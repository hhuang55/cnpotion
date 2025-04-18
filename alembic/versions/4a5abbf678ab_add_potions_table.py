"""Add potions table

Revision ID: 4a5abbf678ab
Revises: 4e55a2d79f4d
Create Date: 2025-04-18 10:19:04.199870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a5abbf678ab'
down_revision: Union[str, None] = '4e55a2d79f4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    print(">>> Running upgrade: creating potions table")
    op.create_table(
        "potions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("red_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("green_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blue_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dark_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.CheckConstraint("red_ml >= 0", name="ck_potions_red_ml_non_negative"),
        sa.CheckConstraint("green_ml >= 0", name="ck_potions_green_ml_non_negative"),
        sa.CheckConstraint("blue_ml >= 0", name="ck_potions_blue_ml_non_negative"),
        sa.CheckConstraint("dark_ml >= 0", name="ck_potions_dark_ml_non_negative"),
        sa.CheckConstraint("price >= 0", name="ck_potions_price_non_negative"),
    )


def downgrade():
    op.drop_table("potions")


