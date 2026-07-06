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


def decrease_item_quantity(user_id: int, item_id: int, quantity: int = 1) -> int:
    """
    Decreases a user's item quantity.

    Returns the remaining quantity after the decrease.
    Deletes the inventory row when the remaining quantity reaches 0.
    """

    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM inventory
            WHERE user_id = ? AND item_id = ?
            """,
            (user_id, item_id),
        ).fetchone()

        if row is None:
            raise ValueError("That item is not in the user's inventory.")

        current_quantity = int(row["quantity"])

        if current_quantity < quantity:
            raise ValueError("The user does not have enough of that item.")

        remaining_quantity = current_quantity - quantity

        if remaining_quantity > 0:
            connection.execute(
                """
                UPDATE inventory
                SET quantity = ?
                WHERE user_id = ? AND item_id = ?
                """,
                (remaining_quantity, user_id, item_id),
            )
        else:
            connection.execute(
                """
                DELETE FROM inventory
                WHERE user_id = ? AND item_id = ?
                """,
                (user_id, item_id),
            )

        connection.commit()

    return remaining_quantity


def get_user_inventory(user_id: int) -> list[dict]:
    """
    Gets a user's inventory with item metadata.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                shop_items.item_id,
                shop_items.name,
                shop_items.description,
                shop_items.category,
                shop_items.rarity,
                shop_items.usable,
                shop_items.consumable,
                shop_items.use_message,
                inventory.quantity
            FROM inventory
            JOIN shop_items
                ON inventory.item_id = shop_items.item_id
            WHERE
                inventory.user_id = ?
                AND inventory.quantity > 0
            ORDER BY
                shop_items.rarity ASC,
                shop_items.name ASC
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_user_inventory_item_by_name(user_id: int, item_name: str) -> dict | None:
    """
    Finds one owned inventory item by name.

    This includes inactive shop items because users may still own
    items that are no longer available for purchase.
    """

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                shop_items.item_id,
                shop_items.name,
                shop_items.description,
                shop_items.category,
                shop_items.rarity,
                shop_items.usable,
                shop_items.consumable,
                shop_items.use_message,
                shop_items.active,
                inventory.quantity
            FROM inventory
            JOIN shop_items
                ON inventory.item_id = shop_items.item_id
            WHERE
                inventory.user_id = ?
                AND inventory.quantity > 0
                AND LOWER(shop_items.name) = LOWER(?)
            """,
            (user_id, item_name.strip()),
        ).fetchone()

    if row is None:
        return None

    return dict(row)