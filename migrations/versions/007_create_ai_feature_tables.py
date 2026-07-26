"""
Create AI Feature Tables (ai_jobs, ai_results, feature_templates)

Revision ID: 007_create_ai_feature_tables
Revises: 006_add_prompt_and_retrieval_telemetry
Create Date: 2026-07-26
"""

from __future__ import annotations

import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = "007_create_ai_feature_tables"
down_revision = "006_add_prompt_and_retrieval_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create ai_jobs table
    op.create_table(
        "ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ai_jobs_id", "ai_jobs", ["id"], unique=False)
    op.create_index("ix_ai_jobs_user_id", "ai_jobs", ["user_id"], unique=False)
    op.create_index("ix_ai_jobs_document_id", "ai_jobs", ["document_id"], unique=False)
    op.create_index("ix_ai_jobs_feature_type", "ai_jobs", ["feature_type"], unique=False)
    op.create_index("ix_ai_jobs_status", "ai_jobs", ["status"], unique=False)
    op.create_index("ix_ai_jobs_created_at", "ai_jobs", ["created_at"], unique=False)
    op.create_index("ix_ai_jobs_user_doc", "ai_jobs", ["user_id", "document_id"], unique=False)
    op.create_index("ix_ai_jobs_doc_feature", "ai_jobs", ["document_id", "feature_type"], unique=False)

    # 2. Create ai_results table
    op.create_table(
        "ai_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_type", sa.String(length=64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ai_results_id", "ai_results", ["id"], unique=False)
    op.create_index("ix_ai_results_job_id", "ai_results", ["job_id"], unique=False)
    op.create_index("ix_ai_results_document_id", "ai_results", ["document_id"], unique=False)
    op.create_index("ix_ai_results_feature_type", "ai_results", ["feature_type"], unique=False)
    op.create_index("ix_ai_results_created_at", "ai_results", ["created_at"], unique=False)
    op.create_index("ix_ai_results_doc_feature", "ai_results", ["document_id", "feature_type"], unique=False)

    # 3. Create feature_templates table
    op.create_table(
        "feature_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_feature_templates_id", "feature_templates", ["id"], unique=False)
    op.create_index("ix_feature_templates_feature_name", "feature_templates", ["feature_name"], unique=True)
    op.create_index("ix_feature_templates_is_active", "feature_templates", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_table("feature_templates")
    op.drop_table("ai_results")
    op.drop_table("ai_jobs")
