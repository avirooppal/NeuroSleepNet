"""
003 - Add webhook delivery log, update webhooks table schema.

Revision ID: a1b2c3d4e5f6
Revises: 3e77c51bfd23
Create Date: 2026-04-19

Changes:
- Adds `event_types` JSONB column to webhooks (replaces `events` string)
- Adds `secret` column to webhooks (HMAC signing)
- Adds `is_active` boolean to webhooks
- Creates `webhook_deliveries` audit table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3e77c51bfd23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Update webhooks table ─────────────────────────────────────────────────
    # Add new columns (event_types JSONB replaces events String)
    op.add_column('webhooks', sa.Column(
        'event_types',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default='[]',
    ))
    op.add_column('webhooks', sa.Column('secret', sa.String(256), nullable=True))
    op.add_column('webhooks', sa.Column(
        'is_active', sa.Boolean(), nullable=False, server_default='true'
    ))
    # Extend url column to 2048 chars
    op.alter_column('webhooks', 'url', type_=sa.String(2048))
    # Drop old comma-string column
    op.drop_column('webhooks', 'events')

    # ── Create webhook_deliveries table ───────────────────────────────────────
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('webhook_id', sa.UUID(), nullable=False),
        sa.Column('event', sa.String(64), nullable=False),
        sa.Column('payload_summary', sa.String(512), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('succeeded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column(
            'delivered_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_deliveries_webhook_id', 'webhook_deliveries', ['webhook_id'])
    op.create_index('ix_webhook_deliveries_succeeded', 'webhook_deliveries', ['succeeded'])


def downgrade() -> None:
    op.drop_index('ix_webhook_deliveries_succeeded', 'webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_webhook_id', 'webhook_deliveries')
    op.drop_table('webhook_deliveries')

    op.drop_column('webhooks', 'is_active')
    op.drop_column('webhooks', 'secret')
    op.drop_column('webhooks', 'event_types')
    op.add_column('webhooks', sa.Column('events', sa.String(), nullable=False, server_default=''))
