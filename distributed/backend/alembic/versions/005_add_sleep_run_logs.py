"""
005 - Add sleep_run_logs table for nightly sleep phase audit trail.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sleep_run_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('memories_scanned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memories_consolidated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_score_delta', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('memories_archived', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memories_deleted_ttl', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('run_duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'top_archived',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
        sa.Column('guardrails_triggered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('run_type', sa.String(32), nullable=False, server_default='nightly'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sleep_run_logs_user_id', 'sleep_run_logs', ['user_id'])
    op.create_index('ix_sleep_run_logs_project_id', 'sleep_run_logs', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_sleep_run_logs_project_id', 'sleep_run_logs')
    op.drop_index('ix_sleep_run_logs_user_id', 'sleep_run_logs')
    op.drop_table('sleep_run_logs')
