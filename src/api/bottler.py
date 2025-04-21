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
    potion_capacity: int
) -> List[PotionMixes]:
    plan = []

    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("""
            SELECT red_ml, green_ml, blue_ml, dark_ml FROM potions
        """)).fetchall()

        total_existing = connection.execute(sqlalchemy.text("""
            SELECT SUM(amount) FROM potions
        """)).scalar() or 0


        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()

        rows = connection.execute(sqlalchemy.text("""
            SELECT red_ml, green_ml, blue_ml, dark_ml, amount FROM potions
        """)).fetchall()
        
        potion_counts = {}
        for row in rows:
            key = (row.red_ml, row.green_ml, row.blue_ml, row.dark_ml)
            potion_counts[key] = row.amount


    remaining_red = red_ml
    remaining_green = green_ml
    remaining_blue = blue_ml
    remaining_dark = dark_ml

    size_preferred = max(1, (potion_capacity * 50) // 6)


    # def is_basic_potion(r, g, b, d):
    #     return [r, g, b, d] in ([100, 0, 0, 0], [0, 100, 0, 0], [0, 0, 100, 0], [0, 0, 0, 100])
    

    for potion in potions:
        r, g, b, d = potion.red_ml, potion.green_ml, potion.blue_ml, potion.dark_ml
        # if r + g + b + d == 0 or is_basic_potion(r, g, b, d):
            # continue
        existing_qty = potion_counts.get((r, g, b, d), 0)
        if existing_qty >= size_preferred:
            continue

        can_make = min(
            remaining_red // r if r else float("inf"),
            remaining_green // g if g else float("inf"),
            remaining_blue // b if b else float("inf"),
            remaining_dark // d if d else float("inf"),
        )

        max_allowed = size_preferred - existing_qty
        if max_allowed <= 0:
            continue

        quantity = min(max_allowed, can_make, maximum_potion_capacity)
        if quantity <= 0:
            continue

        remaining_red -= r * quantity
        remaining_green -= g * quantity
        remaining_blue -= b * quantity
        remaining_dark -= d * quantity
        maximum_potion_capacity -= quantity


        plan.append(PotionMixes(potion_type=[r, g, b, d], quantity=quantity))


    # for potion in potions:
    #     r, g, b, d = potion.red_ml, potion.green_ml, potion.blue_ml, potion.dark_ml
    #     if r + g + b + d == 0 or is_basic_potion(r, g, b, d):
    #         continue

    #     can_make = min(
    #         remaining_red // r if r else float("inf"),
    #         remaining_green // g if g else float("inf"),
    #         remaining_blue // b if b else float("inf"),
    #         remaining_dark // d if d else float("inf"),
    #     )

    #     quantity = min(can_make, maximum_potion_capacity)
    #     if quantity == 0:
    #         continue

    #     remaining_red -= r * quantity
    #     remaining_green -= g * quantity
    #     remaining_blue -= b * quantity
    #     remaining_dark -= d * quantity
    #     maximum_potion_capacity -= quantity

    #     plan.append(PotionMixes(potion_type=[r, g, b, d], quantity=quantity))
        

    #make normal potion as last resort
    # if not plan and gold < 100 and total_existing == 0 and maximum_potion_capacity > 0:
    #     if red_ml >= 100:
    #         max_quantity = min(red_ml // 100, maximum_potion_capacity)
    #         plan.append(PotionMixes(potion_type=[100, 0, 0, 0], quantity=max_quantity))
    #     elif green_ml >= 100:
    #         max_quantity = min(green_ml // 100, maximum_potion_capacity)
    #         plan.append(PotionMixes(potion_type=[0, 100, 0, 0], quantity=max_quantity))
    #     elif blue_ml >= 100:
    #         max_quantity = min(blue_ml // 100, maximum_potion_capacity)
    #         plan.append(PotionMixes(potion_type=[0, 0, 100, 0], quantity=max_quantity))
    #     elif dark_ml >= 100:
    #         max_quantity = min(dark_ml // 100, maximum_potion_capacity)
    #         plan.append(PotionMixes(potion_type=[0, 0, 0, 100], quantity=max_quantity))


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
            sqlalchemy.text("""
                SELECT red_ml, green_ml, blue_ml, dark_ml, potion_capacity 
                FROM global_inventory
            """)
        ).first()

        # calculate total potions
        total_potions = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM potions")
        ).scalar_one()

        red_ml = result.red_ml
        green_ml = result.green_ml
        blue_ml = result.blue_ml
        dark_ml = result.dark_ml
        potion_capacity = result.potion_capacity

        # remaining potion slots
        remaining_capacity = max(0, 50 * potion_capacity - total_potions)

    return create_bottle_plan(
        red_ml=red_ml,
        green_ml=green_ml,
        blue_ml=blue_ml,
        dark_ml=dark_ml,
        maximum_potion_capacity=remaining_capacity,
        current_potion_inventory=[],
        potion_capacity=potion_capacity,
    )


if __name__ == "__main__":
    print(get_bottle_plan())