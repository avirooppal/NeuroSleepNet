"""
006 - Add TTL index optimisation and importance_weight column to memories.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-19

Changes:
- Adds partial index on `expires_at` for fast TTL expiry queries
- Adds `importance_weight` float column (maps to nsn.remember(importance=) param)
- Adds `schema_version` if not already present (should be from initial migration)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial index for TTL expiry queries — only non-null expires_at rows
    op.create_index(
        'ix_memories_ttl_expires_at',
        'memories',
        ['expires_at'],
        postgresql_where=sa.text('expires_at IS NOT NULL'),
    )

    # Importance weight column (used for attention scoring w4 boost)
    op.add_column(
        'memories',
        sa.Column('importance_weight', sa.Float(), nullable=False, server_default='0.5'),
    )

    # Index on consolidation_score for fast archive candidate queries
    op.create_index('ix_memories_consolidation_score', 'memories', ['consolidation_score'])


def downgrade() -> None:
    op.drop_index('ix_memories_consolidation_score', 'memories')
    op.drop_column('memories', 'importance_weight')
    op.drop_index('ix_memories_ttl_expires_at', 'memories')
