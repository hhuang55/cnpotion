from sqlalchemy import text
from src import database as db  # assuming your db.engine is set up

with db.engine.begin() as connection:
    connection.execute(text("""
        INSERT INTO potions (sku, name, red_ml, green_ml, blue_ml, dark_ml, price)
        VALUES 
        ('red_potion', 'Red Potion', 100, 0, 0, 0, 50),
        ('green_potion', 'Green Potion', 0, 100, 0, 0, 50),
        ('blue_potion', 'Blue Potion', 0, 0, 100, 0, 50),
        ('purple_potion', 'Purple Potion', 50, 0, 50, 0, 60),
        ('orange_potion', 'Orange Potion', 60, 40, 0, 0, 60),
        ('dark_potion', 'Dark Potion', 0, 0, 0, 100, 80);
    """))

