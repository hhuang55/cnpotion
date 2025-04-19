from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
from src.api import auth


import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)


class PotionMixes(BaseModel):
    potion_type: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d]",
    )
    quantity: int = Field(
        ..., ge=1, le=10000, description="Quantity must be between 1 and 10,000"
    )

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[int]) -> List[int]:
        if sum(potion_type) != 100:
            raise ValueError("Sum of potion_type values must be exactly 100")
        return potion_type


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    used_red = used_green = used_blue = used_dark = 0

    for pot in potions_delivered:
        r, g, b, d = pot.potion_type
        used_red += r * pot.quantity
        used_green += g * pot.quantity
        used_blue += b * pot.quantity
        used_dark += d * pot.quantity

    with db.engine.begin() as connection:
        # Subtract used ml
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory SET 
                red_ml = red_ml - :usedred,
                green_ml = green_ml - :usedgreen,
                blue_ml = blue_ml - :usedblue,
                dark_ml = dark_ml - :useddark
                """
            ),
            {
                "usedred": used_red,
                "usedgreen": used_green,
                "usedblue": used_blue,
                "useddark": used_dark,
            },
        )

        # Update potion amounts
        for pot in potions_delivered:
            r, g, b, d = pot.potion_type
            connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE potions
                    SET amount = amount + :qty
                    WHERE red_ml = :r AND green_ml = :g AND blue_ml = :b AND dark_ml = :d
                    """
                ),
                {
                    "qty": pot.quantity,
                    "r": r,
                    "g": g,
                    "b": b,
                    "d": d,
                },
            )




def create_bottle_plan(
    red_ml: int,
    green_ml: int,
    blue_ml: int,
    dark_ml: int,
    maximum_potion_capacity: int,
    current_potion_inventory: List[PotionMixes],
) -> List[PotionMixes]:
    plan = []

    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("""
            SELECT red_ml, green_ml, blue_ml, dark_ml FROM potions
        """)).fetchall()

    for potion in potions:
        r, g, b, d = potion.red_ml, potion.green_ml, potion.blue_ml, potion.dark_ml
        total = r + g + b + d
        if total == 0:
            continue

        max_possible = min(
            red_ml // r if r else float("inf"),
            green_ml // g if g else float("inf"),
            blue_ml // b if b else float("inf"),
            dark_ml // d if d else float("inf"),
        )

        quantity = min(max_possible, maximum_potion_capacity)
        if quantity == 0:
            continue

        percentages = [
            int(r / total * 100),
            int(g / total * 100),
            int(b / total * 100),
            int(d / total * 100),
        ]

        diff = 100 - sum(percentages)
        percentages[0] += diff

        plan.append(PotionMixes(potion_type=percentages, quantity=quantity))

    return plan

@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    """
    Gets the plan for bottling potions.
    Each bottle has a quantity of what proportion of red, green, blue, and dark potions to add.
    Colors are expressed in integers from 0 to 100 that must sum up to exactly 100.
    """
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT red_ml, green_ml, blue_ml, dark_ml FROM global_inventory")).first()

        red_ml = result.red_ml
        green_ml = result.green_ml
        blue_ml = result.blue_ml
        dark_ml = result.dark_ml

    # TODO: Fill in values below based on what is in your database
    return create_bottle_plan(
        red_ml=red_ml,
        green_ml=green_ml,
        blue_ml=blue_ml,
        dark_ml=dark_ml,
        maximum_potion_capacity=50,
        current_potion_inventory=[],
    )


if __name__ == "__main__":
    print(get_bottle_plan())