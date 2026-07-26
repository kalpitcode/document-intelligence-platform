"""
Create Workflow Engine Tables (workflow_templates, workflow_runs, workflow_steps, workflow_events, workflow_schedules)

Revision ID: 008_create_workflow_engine_tables
Revises: 007_create_ai_feature_tables
Create Date: 2026-07-26
"""

from __future__ import annotations

import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = "008_create_workflow_engine_tables"
down_revision = "007_create_ai_feature_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create workflow_templates table
    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_workflow_templates_id", "workflow_templates", ["id"], unique=False)
    op.create_index("ix_workflow_templates_name", "workflow_templates", ["name"], unique=False)
    op.create_index("ix_workflow_templates_is_active", "workflow_templates", ["is_active"], unique=False)
    op.create_index("ix_workflow_templates_owner_id", "workflow_templates", ["owner_id"], unique=False)
    op.create_index("ix_workflow_templates_owner_active", "workflow_templates", ["owner_id", "is_active"], unique=False)

    # 2. Create workflow_runs table
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("trigger_type", sa.String(length=50), nullable=False, server_default="MANUAL"),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_workflow_runs_id", "workflow_runs", ["id"], unique=False)
    op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"], unique=False)
    op.create_index("ix_workflow_runs_initiated_by", "workflow_runs", ["initiated_by"], unique=False)
    op.create_index("ix_workflow_runs_workflow_status", "workflow_runs", ["workflow_id", "status"], unique=False)

    # 3. Create workflow_steps table
    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("step_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("step_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_workflow_steps_id", "workflow_steps", ["id"], unique=False)
    op.create_index("ix_workflow_steps_workflow_run_id", "workflow_steps", ["workflow_run_id"], unique=False)
    op.create_index("ix_workflow_steps_step_type", "workflow_steps", ["step_type"], unique=False)
    op.create_index("ix_workflow_steps_status", "workflow_steps", ["status"], unique=False)
    op.create_index("ix_workflow_steps_run_order", "workflow_steps", ["workflow_run_id", "execution_order"], unique=False)

    # 4. Create workflow_events table
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_workflow_events_id", "workflow_events", ["id"], unique=False)
    op.create_index("ix_workflow_events_workflow_run_id", "workflow_events", ["workflow_run_id"], unique=False)
    op.create_index("ix_workflow_events_event_type", "workflow_events", ["event_type"], unique=False)

    # 5. Create workflow_schedules table
    op.create_table(
        "workflow_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cron_expression", sa.String(length=100), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("next_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_workflow_schedules_id", "workflow_schedules", ["id"], unique=False)
    op.create_index("ix_workflow_schedules_workflow_id", "workflow_schedules", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_schedules_enabled", "workflow_schedules", ["enabled"], unique=False)


def downgrade() -> None:
    op.drop_table("workflow_schedules")
    op.drop_table("workflow_events")
    op.drop_table("workflow_steps")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_templates")
