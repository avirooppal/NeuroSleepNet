"""add key_prefix index and token_savings

Revision ID: 008_hardening_fixes
Revises: 007_add_feedback_score
Create Date: 2026-04-30 06:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_hardening_fixes'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add index to api_keys.key_prefix (Fix 2)
    # We first ensure the column length is fixed to 16 for the index
    op.alter_column('api_keys', 'key_prefix',
               existing_type=sa.String(),
               type_=sa.String(length=16),
               existing_nullable=False)
    op.create_index(op.f('ix_api_keys_key_prefix'), 'api_keys', ['key_prefix'], unique=False)

    # 2. Add token_savings to projects (Fix 4)
    op.add_column('projects', sa.Column('token_savings', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('projects', 'token_savings')
    op.drop_index(op.f('ix_api_keys_key_prefix'), table_name='api_keys')
    op.alter_column('api_keys', 'key_prefix',
               existing_type=sa.String(length=16),
               type_=sa.String(),
               existing_nullable=False)
