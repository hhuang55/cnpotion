"""Merge broken and fixed potion migrations

Revision ID: e9d2b97b79e3
Revises: 2a2f4ea3c605, 4a5abbf678ab
Create Date: 2025-04-18 10:49:55.508619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9d2b97b79e3'
down_revision: Union[str, None] = ('2a2f4ea3c605')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
