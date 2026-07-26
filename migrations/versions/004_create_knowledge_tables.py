"""create_knowledge_tables

Revision ID: 004_create_knowledge_tables
Revises: 003_create_processing_tables
Create Date: 2026-07-26 18:00:00.000000

"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_create_knowledge_tables"
down_revision: str | None = "003_create_processing_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. embedding_jobs table
    op.create_table(
        "embedding_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="Queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("embedding_model", sa.String(255), nullable=False, server_default="sentence-transformers/all-MiniLM-L6-v2"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_embedding_jobs_document_id", "embedding_jobs", ["document_id"])
    op.create_index("ix_embedding_jobs_status", "embedding_jobs", ["status"])

    # 2. search_histories table
    op.create_table(
        "search_histories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(50), nullable=False, server_default="hybrid"),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_histories_user_id", "search_histories", ["user_id"])
    op.create_index("ix_search_histories_query_type", "search_histories", ["query_type"])
    op.create_index("ix_search_histories_created_at", "search_histories", ["created_at"])

    # 3. embedding_models table
    op.create_table(
        "embedding_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="384"),
        sa.Column("provider", sa.String(100), nullable=False, server_default="sentence-transformers"),
        sa.Column("version", sa.String(50), nullable=False, server_default="v1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_embedding_models_name", "embedding_models", ["name"], unique=True)
    op.create_index("ix_embedding_models_is_active", "embedding_models", ["is_active"])


def downgrade() -> None:
    op.drop_table("embedding_models")
    op.drop_table("search_histories")
    op.drop_table("embedding_jobs")
