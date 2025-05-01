"""add source to request table

Revision ID: bcf80a1c9ee6
Revises: 0f7f89d743ec
Create Date: 2025-04-30 18:43:47.951272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcf80a1c9ee6'
down_revision: Union[str, None] = '0f7f89d743ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("requests", sa.Column("source", sa.String(), nullable=False, server_default="default"))

    op.drop_constraint("requests_pkey", "requests", type_="primary")

    op.create_unique_constraint("unique_order_source", "requests", ["order_id", "source"])


def downgrade():
    op.drop_constraint("unique_order_source", "requests", type_="unique")
    op.drop_column("requests", "source")
    op.create_primary_key("requests_pkey", "requests", ["order_id"])
