# Alembic generic migration template
# Revision ID: 7b143975c0cc
# Revises: 1190850c4097
# Create Date: 2026-02-07 11:50:47.317219

"""add_source_column"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '7b143975c0cc'
down_revision: Union[str, None] = '1190850c4097'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source column
    op.add_column('positions', sa.Column('source', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove source column
    op.drop_column('positions', 'source')
