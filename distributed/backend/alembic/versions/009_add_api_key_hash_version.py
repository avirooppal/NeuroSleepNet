"""add hash_version to api_keys and mark legacy keys

Revision ID: 009_add_api_key_hash_version
Revises: 008_hardening_fixes
Create Date: 2026-05-09 10:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_add_api_key_hash_version'
down_revision = '008_hardening_fixes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix 1.4: Add hash_version column to api_keys
    op.add_column('api_keys', sa.Column('hash_version', sa.String(length=8), nullable=False, server_default='v1'))

    # Update the server_default so new keys default to v2 (passlib)
    op.alter_column('api_keys', 'hash_version',
               existing_type=sa.String(length=8),
               server_default='v2',
               existing_nullable=False)


def downgrade() -> None:
    op.drop_column('api_keys', 'hash_version')
