from db.database import get_connection


def add_item_to_inventory(user_id: int, item_id: int, quantity: int) -> None:
    """
    Adds an item quantity to a user's inventory.
    """
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO inventory (
                user_id,
                item_id,
                quantity
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id)
            DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (user_id, item_id, quantity),
        )

        connection.commit()


def get_user_inventory(user_id: int) -> list[dict]:
    """
    Gets a user's inventory with item names and descriptions.
    """
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                shop_items.name,
                shop_items.description,
                inventory.quantity
            FROM inventory
            JOIN shop_items ON inventory.item_id = shop_items.item_id
            WHERE inventory.user_id = ? AND inventory.quantity > 0
            ORDER BY shop_items.name ASC
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]