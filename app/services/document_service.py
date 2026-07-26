"""
Document Orchestrator Service Module
====================================

Core domain service managing document uploads, CRUD, versioning, download presigning,
and RBAC ownership authorization checks.

**Architectural Rationale:**
- Implements complete enterprise upload pipeline.
- Coordinates StorageService, ValidationService, ChecksumService, MetadataService, VersionService, and UploadService.
- Emits domain events (`DocumentUploaded`, `DocumentDeleted`, `DocumentVersionCreated`, `DocumentDownloadRequested`).
"""

from __future__ import annotations

import os
from typing import Any, Sequence
import uuid

from app.core.events import (
    DocumentDeleted,
    DocumentDownloadRequested,
    DocumentUploaded,
    DocumentVersionCreated,
    EventBus,
    UploadFailed,
)
from app.core.exceptions.base import BaseAppException
from app.models.document import DocumentModel, DocumentStatus, DocumentVersionModel, Visibility
from app.models.user import UserModel
from app.repositories.document_repository import DocumentRepository
from app.services.checksum_service import ChecksumService
from app.services.metadata_service import MetadataService
from app.services.storage_service import StorageService
from app.services.upload_service import UploadService
from app.services.validation_service import ValidationService
from app.services.version_service import VersionService


class DocumentNotFoundError(BaseAppException):
    """Raised when requested document does not exist."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            status_code=404,
            message=f"Document with ID '{document_id}' not found",
            error_code="DOCUMENT_NOT_FOUND",
        )


class DocumentAccessDeniedError(BaseAppException):
    """Raised when user lacks permission to access document."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            status_code=403,
            message=f"Access denied to document '{document_id}'",
            error_code="DOCUMENT_ACCESS_DENIED",
        )


class DocumentService:
    """Master domain service orchestrating enterprise document storage."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        storage_service: StorageService,
        validation_service: ValidationService,
        checksum_service: ChecksumService,
        metadata_service: MetadataService,
        version_service: VersionService,
        upload_service: UploadService,
    ) -> None:
        self.doc_repo = document_repo
        self.storage_service = storage_service
        self.validation_service = validation_service
        self.checksum_service = checksum_service
        self.metadata_service = metadata_service
        self.version_service = version_service
        self.upload_service = upload_service

    async def upload_document(
        self,
        current_user: UserModel,
        filename: str,
        content: bytes,
        declared_mime: str | None = None,
        visibility: str = Visibility.PRIVATE.value,
        custom_metadata: dict[str, Any] | None = None,
    ) -> DocumentModel:
        """
        Execute full document upload pipeline:
        Validate -> Upload Session -> SHA256 -> MinIO Store -> Persist DB -> Metadata -> Version -> Event
        """
        upload_sess = await self.upload_service.create_session(user_id=current_user.id)
        upload_id = upload_sess.upload_id

        try:
            # 1. Validation
            clean_filename, mime_type, file_size = self.validation_service.validate_file(
                filename=filename,
                content=content,
                declared_mime_type=declared_mime,
            )
            await self.upload_service.update_progress(upload_id, 25)

            # 2. Checksum calculation
            sha256_hash = self.checksum_service.calculate_sha256_bytes(content)
            await self.upload_service.update_progress(upload_id, 40)

            # 3. Server-side UUID stored filename & storage path
            file_uuid = uuid.uuid4()
            ext = os.path.splitext(clean_filename)[1].lower()
            stored_filename = f"{file_uuid.hex}{ext}"
            storage_path = f"documents/{current_user.id}/{stored_filename}"

            # 4. Store binary in MinIO
            await self.storage_service.store_file(
                file_bytes=content,
                object_key=storage_path,
                content_type=mime_type,
            )
            await self.upload_service.update_progress(upload_id, 75)

            # 5. Persist Document entity
            doc_data = {
                "id": file_uuid,
                "owner_id": current_user.id,
                "original_filename": clean_filename,
                "stored_filename": stored_filename,
                "storage_path": storage_path,
                "mime_type": mime_type,
                "extension": ext,
                "file_size": file_size,
                "sha256_hash": sha256_hash,
                "version": 1,
                "status": DocumentStatus.UPLOADED.value,
                "visibility": visibility,
            }
            doc = await self.doc_repo.create(**doc_data)

            # 6. Create Metadata & Initial Version
            await self.metadata_service.create_metadata(
                document_id=doc.id,
                file_size=file_size,
                file_type=ext.lstrip("."),
                custom_metadata=custom_metadata,
            )

            await self.version_service.create_version(
                document_id=doc.id,
                version_number=1,
                storage_path=storage_path,
                checksum=sha256_hash,
                uploaded_by=current_user.id,
                change_notes="Initial document upload",
            )

            await self.upload_service.complete_session(upload_id)

            # 7. Publish Domain Event
            EventBus.publish(
                DocumentUploaded(
                    document_id=str(doc.id),
                    owner_id=str(current_user.id),
                    original_filename=clean_filename,
                    file_size=file_size,
                    sha256_hash=sha256_hash,
                )
            )

            return (await self.doc_repo.get_by_id_with_relations(doc.id)) or doc

        except Exception as exc:
            await self.upload_service.fail_session(upload_id)
            EventBus.publish(
                UploadFailed(
                    upload_id=upload_id,
                    user_id=str(current_user.id),
                    reason=str(exc),
                )
            )
            raise

    async def get_document(
        self,
        document_id: uuid.UUID | str,
        current_user: UserModel,
    ) -> DocumentModel:
        """Fetch document with RBAC ownership access authorization check."""
        doc = await self.doc_repo.get_by_id_with_relations(document_id)
        if not doc:
            raise DocumentNotFoundError(str(document_id))

        self.check_document_access(doc, current_user)
        return doc

    async def list_documents(
        self,
        current_user: UserModel,
        filename: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        mime_type: str | None = None,
        date_from: Any = None,
        date_to: Any = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[DocumentModel], int]:
        """List documents. Non-admins can only list their own documents."""
        is_admin = self._is_user_admin(current_user)
        owner_filter = None if is_admin else current_user.id

        return await self.doc_repo.list_documents(
            owner_id=owner_filter,
            filename=filename,
            status=status,
            visibility=visibility,
            mime_type=mime_type,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )

    async def create_new_version(
        self,
        document_id: uuid.UUID | str,
        current_user: UserModel,
        filename: str,
        content: bytes,
        change_notes: str | None = None,
    ) -> DocumentVersionModel:
        """Upload a new version for an existing document."""
        doc = await self.get_document(document_id, current_user)

        clean_filename, mime_type, file_size = self.validation_service.validate_file(
            filename=filename,
            content=content,
        )
        checksum = self.checksum_service.calculate_sha256_bytes(content)

        new_version_num = doc.version + 1
        ext = os.path.splitext(clean_filename)[1].lower()
        new_stored = f"{uuid.uuid4().hex}{ext}"
        new_storage_path = f"documents/{current_user.id}/v{new_version_num}_{new_stored}"

        await self.storage_service.store_file(content, new_storage_path, mime_type)

        version = await self.version_service.create_version(
            document_id=doc.id,
            version_number=new_version_num,
            storage_path=new_storage_path,
            checksum=checksum,
            uploaded_by=current_user.id,
            change_notes=change_notes or f"Updated to version {new_version_num}",
        )

        # Update parent document metadata & version
        await self.doc_repo.update(
            doc,
            version=new_version_num,
            file_size=file_size,
            sha256_hash=checksum,
            storage_path=new_storage_path,
        )

        EventBus.publish(
            DocumentVersionCreated(
                document_id=str(doc.id),
                version_number=new_version_num,
                uploaded_by=str(current_user.id),
                checksum=checksum,
            )
        )

        return version

    async def get_download_url(
        self,
        document_id: uuid.UUID | str,
        current_user: UserModel,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned download URL for document."""
        doc = await self.get_document(document_id, current_user)

        EventBus.publish(
            DocumentDownloadRequested(
                document_id=str(doc.id),
                requested_by=str(current_user.id),
            )
        )

        return await self.storage_service.get_presigned_download_url(doc.storage_path, expires_in)

    async def delete_document(
        self,
        document_id: uuid.UUID | str,
        current_user: UserModel,
    ) -> bool:
        """Soft delete document record and mark status as DELETED."""
        doc = await self.get_document(document_id, current_user)

        await self.doc_repo.update(doc, status=DocumentStatus.DELETED.value)
        await self.doc_repo.delete(doc, soft=True)

        EventBus.publish(
            DocumentDeleted(
                document_id=str(doc.id),
                deleted_by=str(current_user.id),
            )
        )
        return True

    def check_document_access(self, doc: DocumentModel, current_user: UserModel) -> None:
        """Enforce document ownership / admin access rule."""
        if self._is_user_admin(current_user):
            return

        if doc.owner_id == current_user.id:
            return

        if doc.visibility == Visibility.PUBLIC.value:
            return

        raise DocumentAccessDeniedError(str(doc.id))

    def _is_user_admin(self, user: UserModel) -> bool:
        """Check if user has Admin or Manager role."""
        if not hasattr(user, "roles") or not user.roles:
            return False
        role_names = {r.name.upper() for r in user.roles}
        return bool(role_names.intersection({"ADMIN", "MANAGER", "SUPER_ADMIN"}))
