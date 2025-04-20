from dataclasses import dataclass
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List

import sqlalchemy
from src.api import auth
from src import database as db
import random

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int = Field(gt=0, description="Must be greater than 0")
    potion_type: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d] that sum to 1.0",
    )
    price: int = Field(ge=0, description="Price must be non-negative")
    quantity: int = Field(ge=0, description="Quantity must be non-negative")

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[float]) -> List[float]:
        if len(potion_type) != 4:
            raise ValueError("potion_type must have exactly 4 elements: [r, g, b, d]")
        if not abs(sum(potion_type) - 1.0) < 1e-6:
            raise ValueError("Sum of potion_type values must be exactly 1.0")
        return potion_type


class BarrelOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


@dataclass
class BarrelSummary:
    gold_paid: int


def calculate_barrel_summary(barrels: List[Barrel]) -> BarrelSummary:
    return BarrelSummary(gold_paid=sum(b.price * b.quantity for b in barrels))


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    """
    Processes barrels delivered based on the provided order_id. order_id is a unique value representing
    a single delivery; the call is idempotent based on the order_id.
    """
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    delivery = calculate_barrel_summary(barrels_delivered)

    red_ml = green_ml = blue_ml = dark_ml = 0

    
    for barrel in barrels_delivered:
        ml_added = barrel.ml_per_barrel * barrel.quantity
        red_ml += barrel.potion_type[0] * ml_added
        green_ml += barrel.potion_type[1] * ml_added
        blue_ml += barrel.potion_type[2] * ml_added
        dark_ml += barrel.potion_type[3] * ml_added



    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory SET 

                gold = gold - :gold_paid,
                red_ml = red_ml + :red_ml,
                green_ml = green_ml + :green_ml,
                blue_ml = blue_ml + :blue_ml,
                dark_ml = dark_ml + :dark_ml
                """
            ),
            {"gold_paid": delivery.gold_paid,
              "red_ml": red_ml,
              "green_ml": green_ml,
              "blue_ml": blue_ml,
                "dark_ml": dark_ml
              }

        )
        

    pass


def create_barrel_plan(
    gold: int,
    max_barrel_capacity: int,
    current_red_ml: int,
    current_green_ml: int,
    current_blue_ml: int,
    current_dark_ml: int,
    wholesale_catalog: List[Barrel],
) -> List[BarrelOrder]:
    import math

    plan: List[BarrelOrder] = []
    remaining_gold = gold

    target_per_color = max_barrel_capacity // 4
    current_ml = [current_red_ml, current_green_ml, current_blue_ml, current_dark_ml]
    needed_ml = [max(0, target_per_color - amt) for amt in current_ml]

    def needed_from_barrel(barrel: Barrel) -> float:
        return sum(
            barrel.potion_type[i] * barrel.ml_per_barrel
            if needed_ml[i] > 0 else 0
            for i in range(4)
        )

    #sort out the useful barrels
    useful_barrels = [b for b in wholesale_catalog if needed_from_barrel(b) > 0]
    useful_barrels.sort(key=lambda b: (b.price / needed_from_barrel(b)) if needed_from_barrel(b) > 0 else float("inf"))


    for barrel in useful_barrels:
        if barrel.price > remaining_gold or barrel.quantity == 0: #check for cost
            continue

        #how much each color barrel gives
        ml_per_color = [barrel.potion_type[i] * barrel.ml_per_barrel for i in range(4)]  


        # barrels we cacn buy before hitting threshold
        max_quantity_based_on_need = math.inf
        for i in range(4):
            if ml_per_color[i] > 0 and needed_ml[i] > 0:
                can_take = needed_ml[i] / ml_per_color[i]
                max_quantity_based_on_need = min(max_quantity_based_on_need, int(math.ceil(can_take)))

        #how much we can buy
        max_quantity_affordable = remaining_gold // barrel.price
        final_quantity = min(barrel.quantity, max_quantity_affordable, max_quantity_based_on_need)

        if final_quantity > 0:
            plan.append(BarrelOrder(sku=barrel.sku, quantity=final_quantity))
            remaining_gold -= final_quantity * barrel.price
            for i in range(4):
                needed_ml[i] = max(0, needed_ml[i] - (ml_per_color[i] * final_quantity))

        if all(ml == 0 for ml in needed_ml):
            break

    return plan


@router.post("/plan", response_model=List[BarrelOrder])
def get_wholesale_purchase_plan(wholesale_catalog: List[Barrel]):
    """
    Gets the plan for purchasing wholesale barrels. The call passes in a catalog of available barrels
    and the shop returns back which barrels they'd like to purchase and how many.
    """
    print(f"barrel catalog: {wholesale_catalog}")

    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT gold, red_ml, green_ml, blue_ml, dark_ml
                FROM global_inventory
                """
            )
        ).one()

        gold = row.gold
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml
        dark_ml = row.dark_ml

    # TODO: fill in values correctly based on what is in your database
    return create_barrel_plan(
        gold=gold,
        max_barrel_capacity=10000,
        current_red_ml= red_ml,
        current_green_ml= green_ml,
        current_blue_ml= blue_ml,
        current_dark_ml= dark_ml,
        wholesale_catalog=wholesale_catalog,
    )
