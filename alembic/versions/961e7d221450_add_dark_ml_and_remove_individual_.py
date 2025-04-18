"""Add dark_ml and remove individual potions

Revision ID: 961e7d221450
Revises: e9d2b97b79e3
Create Date: 2025-04-18 10:52:56.751803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '961e7d221450'
down_revision: Union[str, None] = 'e9d2b97b79e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add dark_ml
    op.add_column("global_inventory", sa.Column("dark_ml", sa.Integer(), nullable=False, server_default="0"))

    # Remove individual potion counts
    op.drop_column("global_inventory", "red_potions")
    op.drop_column("global_inventory", "green_potions")
    op.drop_column("global_inventory", "blue_potions")

    # Add constraint for dark_ml
    op.create_check_constraint("ck_dark_ml_non_negative", "global_inventory", "dark_ml >= 0")


def downgrade():
    # Restore individual potion counts
    op.add_column("global_inventory", sa.Column("red_potions", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("global_inventory", sa.Column("green_potions", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("global_inventory", sa.Column("blue_potions", sa.Integer(), nullable=False, server_default="0"))

    # Remove dark_ml column
    op.drop_constraint("ck_dark_ml_non_negative", "global_inventory", type_="check")
    op.drop_column("global_inventory", "dark_ml")