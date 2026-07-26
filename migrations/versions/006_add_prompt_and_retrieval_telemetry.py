"""
Add prompt version and retrieval telemetry to llm_usage_logs

Revision ID: 006_add_prompt_and_retrieval_telemetry
Revises: 005_create_rag_tables
Create Date: 2026-07-26
"""

from __future__ import annotations

import alembic.op as op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "006_add_prompt_and_retrieval_telemetry"
down_revision = "005_create_rag_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("llm_usage_logs", sa.Column("prompt_template_name", sa.String(length=128), nullable=True))
    op.add_column("llm_usage_logs", sa.Column("prompt_version", sa.String(length=32), nullable=True))
    op.add_column("llm_usage_logs", sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=True))
    op.add_column("llm_usage_logs", sa.Column("retrieval_scores", sa.JSON(), nullable=True))
    op.add_column("llm_usage_logs", sa.Column("retrieval_strategy", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_usage_logs", "retrieval_strategy")
    op.drop_column("llm_usage_logs", "retrieval_scores")
    op.drop_column("llm_usage_logs", "retrieved_chunk_ids")
    op.drop_column("llm_usage_logs", "prompt_version")
    op.drop_column("llm_usage_logs", "prompt_template_name")
