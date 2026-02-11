# Alembic generic migration template
# Revision ID: 1190850c4097
# Revises: 001
# Create Date: 2026-02-07 14:28:27.961285

"""add_applied_column"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '1190850c4097'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add applied column with default value
    op.add_column('positions', sa.Column('applied', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove applied column
    op.drop_column('positions', 'applied')
