"""
004 - Add benchmark results table with run_id and detailed per-scenario results.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-19

Changes:
- Adds `benchmark_results` table (per-scenario results per run)
- Adds `run_id` string to `benchmark_runs` for shareable URL
- Adds `control_score` column for side-by-side comparison
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend benchmark_runs with extra columns
    op.add_column('benchmark_runs', sa.Column('run_key', sa.String(32), nullable=True, unique=True))
    op.add_column('benchmark_runs', sa.Column('control_score', sa.Float(), nullable=True))
    op.add_column('benchmark_runs', sa.Column('seed', sa.String(32), nullable=True))
    op.add_column('benchmark_runs', sa.Column('status', sa.String(32), nullable=False, server_default='pending'))
    op.add_column('benchmark_runs', sa.Column(
        'completed_at', sa.DateTime(timezone=True), nullable=True
    ))

    # Create benchmark_results table (one row per scenario per run)
    op.create_table(
        'benchmark_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('scenario', sa.String(64), nullable=False),
        sa.Column('with_nsn_score', sa.Float(), nullable=False),
        sa.Column('without_nsn_score', sa.Float(), nullable=True),
        sa.Column('delta_pct', sa.Float(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['run_id'], ['benchmark_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_benchmark_results_run_id', 'benchmark_results', ['run_id'])


def downgrade() -> None:
    op.drop_index('ix_benchmark_results_run_id', 'benchmark_results')
    op.drop_table('benchmark_results')
    op.drop_column('benchmark_runs', 'completed_at')
    op.drop_column('benchmark_runs', 'status')
    op.drop_column('benchmark_runs', 'seed')
    op.drop_column('benchmark_runs', 'control_score')
    op.drop_column('benchmark_runs', 'run_key')
