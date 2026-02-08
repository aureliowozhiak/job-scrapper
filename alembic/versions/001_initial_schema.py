"""Initial schema with positions table

Revision ID: 001
Revises: 
Create Date: 2026-02-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create positions table."""
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('link', sa.Text(), nullable=False),
        sa.Column('company', sa.String(length=300), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_company'), 'positions', ['company'], unique=False)
    op.create_index(op.f('ix_positions_link'), 'positions', ['link'], unique=True)
    op.create_index(op.f('ix_positions_title'), 'positions', ['title'], unique=False)


def downgrade() -> None:
    """Drop positions table."""
    op.drop_index(op.f('ix_positions_title'), table_name='positions')
    op.drop_index(op.f('ix_positions_link'), table_name='positions')
    op.drop_index(op.f('ix_positions_company'), table_name='positions')
    op.drop_table('positions')
