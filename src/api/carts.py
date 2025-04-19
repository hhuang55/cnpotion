from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from enum import Enum
from typing import List, Optional
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class SearchSortOptions(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"


class SearchSortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class LineItem(BaseModel):
    line_item_id: int
    item_sku: str
    customer_name: str
    line_item_total: int
    timestamp: str


class SearchResponse(BaseModel):
    previous: Optional[str] = None
    next: Optional[str] = None
    results: List[LineItem]


@router.get("/search/", response_model=SearchResponse, tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: SearchSortOptions = SearchSortOptions.timestamp,
    sort_order: SearchSortOrder = SearchSortOrder.desc,
):
    query = f"""
        SELECT 
            ci.cart_item_id AS line_item_id,
            ci.potion_sku AS item_sku,
            c.customer_id AS customer_name,
            ci.quantity * p.price AS line_item_total,
            c.created_at AS timestamp
        FROM cart_items ci
        JOIN carts c ON ci.cart_id = c.cart_id
        JOIN potions p ON ci.potion_sku = p.sku
        WHERE (:customer_name = '' OR c.customer_id ILIKE :customer_name)
        AND (:potion_sku = '' OR ci.potion_sku = :potion_sku)
        ORDER BY {sort_col.value} {sort_order.value.upper()}
        LIMIT 50
    """

    with db.engine.begin() as connection:
        rows = connection.execute(
            sqlalchemy.text(query),
            {"customer_name": f"%{customer_name}%", "potion_sku": potion_sku}
        ).fetchall()

    return SearchResponse(
        previous=None,
        next=None,
        results=[
            LineItem(
                line_item_id=row.line_item_id,
                item_sku=row.item_sku,
                customer_name=row.customer_name,
                line_item_total=row.line_item_total,
                timestamp=row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else row.timestamp
            )
            for row in rows
        ],
    )





class Customer(BaseModel):
    customer_id: str
    customer_name: str
    character_class: str
    level: int = Field(ge=1, le=20)


@router.post("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_visits(visit_id: int, customers: List[Customer]):
    """
    Shares the customers that visited the store on that tick.
    """
    print(customers)
    pass


class CartCreateResponse(BaseModel):
    cart_id: int


@router.post("/", response_model=CartCreateResponse)
def create_cart(new_cart: Customer):
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO carts (customer_id, customer_name)
                VALUES (:customer_id, :customer_name)
                RETURNING cart_id
                """
            ),
            {
                "customer_id": new_cart.customer_id,
                "customer_name": new_cart.customer_name
            }
        )
        cart_id = result.scalar_one()

    return CartCreateResponse(cart_id=cart_id)



class CartItem(BaseModel):
    quantity: int = Field(ge=1, description="Quantity must be at least 1")



@router.post("/{cart_id}/items/{item_sku}", status_code=status.HTTP_204_NO_CONTENT)
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    with db.engine.begin() as connection:
        # Check if cart exists
        result = connection.execute(
            sqlalchemy.text("SELECT 1 FROM carts WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        ).first()

        if result is None:
            raise HTTPException(status_code=404, detail="Cart not found")

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO cart_items (cart_id, potion_sku, quantity)
                VALUES (:cart_id, :sku, :qty)
                ON CONFLICT (cart_id, potion_sku) DO UPDATE
                SET quantity = :qty
            """),
            {"cart_id": cart_id, "sku": item_sku, "qty": cart_item.quantity}
        )


class CheckoutResponse(BaseModel):
    total_potions_bought: int
    total_gold_paid: int


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        cart_items = connection.execute(
            sqlalchemy.text("""
                SELECT ci.potion_sku, ci.quantity, p.amount, p.price
                FROM cart_items ci
                JOIN potions p ON ci.potion_sku = p.sku
                WHERE ci.cart_id = :cart_id
            """),
            {"cart_id": cart_id}
        ).fetchall()

        if not cart_items:
            raise HTTPException(status_code=404, detail="Cart not found or empty")

        total_gold_paid = 0
        total_potions_bought = 0

        for item in cart_items:
            if item.amount < item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough {item.potion_sku} in stock")
            total_potions_bought += item.quantity
            total_gold_paid += item.price * item.quantity

        connection.execute(
            sqlalchemy.text("UPDATE global_inventory SET gold = gold + :gold"),
            {"gold": total_gold_paid}
        )

        for item in cart_items:
            connection.execute(
                sqlalchemy.text("""
                    UPDATE potions SET amount = amount - :qty WHERE sku = :sku
                """),
                {"qty": item.quantity, "sku": item.potion_sku}
            )

        # clear cart
        connection.execute(
            sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        )

        #true if checkedout from cart
        connection.execute(
        sqlalchemy.text("UPDATE carts SET checked_out = true WHERE cart_id = :cart_id"),
        {"cart_id": cart_id}
)


    return CheckoutResponse(
        total_potions_bought=total_potions_bought,
        total_gold_paid=total_gold_paid,
    )
