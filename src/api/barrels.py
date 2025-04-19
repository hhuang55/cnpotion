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
    plan = []
    
    # Randomly pick a color 
    colors = ['red', 'green', 'blue', 'dark']
    chosen_color = random.choice(colors)

    # Check inventory and price for the chosen color
    if chosen_color == 'red':
        if current_red_ml < 500:
            red_barrel = min(
                (barrel for barrel in wholesale_catalog if barrel.potion_type == [1.0, 0, 0, 0]),
                key=lambda b: b.price,
                default=None
            )

            if red_barrel and red_barrel.price <= gold:
                plan.append(BarrelOrder(sku=red_barrel.sku, quantity=1))

    elif chosen_color == 'green':
        if current_green_ml < 500:  # Fewer than 100 ml
            green_barrel = min(
                (barrel for barrel in wholesale_catalog if barrel.potion_type == [0, 1.0, 0, 0]),
                key=lambda b: b.price,
                default=None
            )

            if green_barrel and green_barrel.price <= gold:
                plan.append(BarrelOrder(sku=green_barrel.sku, quantity=1))

    elif chosen_color == 'blue':
        if current_blue_ml < 500:  # Fewer than 100 ml
            blue_barrel = min(
                (barrel for barrel in wholesale_catalog if barrel.potion_type == [0, 0, 1.0, 0]),
                key=lambda b: b.price,
                default=None
            )

            if blue_barrel and blue_barrel.price <= gold:
                plan.append(BarrelOrder(sku=blue_barrel.sku, quantity=1))
    elif chosen_color == 'dark':
        if current_dark_ml < 500:  # Fewer than 100 ml
            dark_barrel = min(
                (barrel for barrel in wholesale_catalog if barrel.potion_type == [0, 0, 0, 1.0]),
                key=lambda b: b.price,
                default=None
            )   
            
            if dark_barrel and dark_barrel.price <= gold:
                plan.append(BarrelOrder(sku=dark_barrel.sku, quantity=1))


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
