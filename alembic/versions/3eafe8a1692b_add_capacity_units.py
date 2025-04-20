"""add capacity units

Revision ID: 3eafe8a1692b
Revises: c7d8c6368cc9
Create Date: 2025-04-20 01:35:57.744075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eafe8a1692b'
down_revision: Union[str, None] = 'c7d8c6368cc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('global_inventory', sa.Column('potion_capacity', sa.Integer(), server_default='1', nullable=False))
    op.add_column('global_inventory', sa.Column('ml_capacity', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    op.drop_column('global_inventory', 'ml_capacity')
    op.drop_column('global_inventory', 'potion_capacity')