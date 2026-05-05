"""add feedback_score
Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-29 06:27:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add feedback_score column
    op.add_column('memories', sa.Column('feedback_score', sa.Float(), nullable=False, server_default='0.0'))
    # No need to add importance if it was already in 006 as importance_weight
    # But I should probably make sure it matches my model
    pass

def downgrade() -> None:
    op.drop_column('memories', 'feedback_score')
