from db.database import get_connection
from services.economy_service import utc_now


DEFAULT_SHOP_ITEMS = [
    (
        "Eclipse Drink Voucher",
        250,
        "A voucher redeemable for one standard drink at Eclipse.",
    ),
    (
        "Obsession Perfume Sample",
        500,
        "A luxury fragrance sample from Maximillion's Obsession line.",
    ),
    (
        "Foxy Delights Dessert Box",
        300,
        "A curated dessert box from Foxy Delights.",
    ),
    (
        "Black Cab Transit Pass",
        400,
        "A short-distance private transit pass through Sin City.",
    ),
    (
        "Velvet Obelisk Visitor Pass",
        1500,
        "A limited visitor pass for approved Velvet Obelisk access.",
    ),
    (
        "Luxury Gift Box",
        2000,
        "A premium social gift package for RP scenes.",
    ),
]


def seed_default_shop_items() -> None:
    """
    Adds the default v1 shop items if they do not already exist.
    """
    now = utc_now()

    with get_connection() as connection:
        for name, price, description in DEFAULT_SHOP_ITEMS:
            connection.execute(
                """
                INSERT OR IGNORE INTO shop_items (
                    name,
                    price,
                    description,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (name, price, description, now, now),
            )

        connection.commit()


def get_active_shop_items() -> list[dict]:
    """
    Returns all active shop items.
    """
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description
            FROM shop_items
            WHERE active = 1
            ORDER BY price ASC, name ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]

def get_shop_item_by_name(item_name: str) -> dict | None:
    """
    Finds an active shop item by name.

    Matching is case-insensitive.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description
            FROM shop_items
            WHERE LOWER(name) = LOWER(?)
              AND active = 1
            """,
            (item_name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)

def get_shop_item_by_id(item_id: int) -> dict | None:
    """
    Finds a shop item by ID, including inactive items.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description,
                active
            FROM shop_items
            WHERE item_id = ?
            """,
            (item_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_shop_item_by_name_any_status(item_name: str) -> dict | None:
    """
    Finds a shop item by name, including inactive items.

    Matching is case-insensitive.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description,
                active
            FROM shop_items
            WHERE LOWER(name) = LOWER(?)
            """,
            (item_name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def create_shop_item(name: str, price: int, description: str) -> dict:
    """
    Creates a new active shop item.
    """
    clean_name = name.strip()
    clean_description = description.strip()

    if not clean_name:
        raise ValueError("Item name cannot be empty.")

    if price <= 0:
        raise ValueError("Price must be greater than zero.")

    if not clean_description:
        raise ValueError("Item description cannot be empty.")

    existing_item = get_shop_item_by_name_any_status(clean_name)

    if existing_item is not None:
        raise ValueError("An item with that name already exists.")

    now = utc_now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO shop_items (
                name,
                price,
                description,
                active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (clean_name, price, clean_description, now, now),
        )

        connection.commit()

        item_id = cursor.lastrowid

    item = get_shop_item_by_id(item_id)

    if item is None:
        raise RuntimeError("Shop item was created, but could not be retrieved.")

    return item


def update_shop_item(
    current_name: str,
    new_name: str | None = None,
    price: int | None = None,
    description: str | None = None,
    active: bool | None = None,
) -> dict:
    """
    Updates an existing shop item.

    Any field left as None will stay unchanged.
    """
    item = get_shop_item_by_name_any_status(current_name.strip())

    if item is None:
        raise ValueError("Requested item is not registered.")

    updates = []
    values = []

    if new_name is not None:
        clean_new_name = new_name.strip()

        if not clean_new_name:
            raise ValueError("New item name cannot be empty.")

        duplicate_item = get_shop_item_by_name_any_status(clean_new_name)

        if duplicate_item is not None and duplicate_item["item_id"] != item["item_id"]:
            raise ValueError("Another item already uses that name.")

        updates.append("name = ?")
        values.append(clean_new_name)

    if price is not None:
        if price <= 0:
            raise ValueError("Price must be greater than zero.")

        updates.append("price = ?")
        values.append(price)

    if description is not None:
        clean_description = description.strip()

        if not clean_description:
            raise ValueError("Description cannot be empty.")

        updates.append("description = ?")
        values.append(clean_description)

    if active is not None:
        updates.append("active = ?")
        values.append(1 if active else 0)

    if not updates:
        raise ValueError("No item changes were provided.")

    updates.append("updated_at = ?")
    values.append(utc_now())

    values.append(item["item_id"])

    with get_connection() as connection:
        connection.execute(
            f"""
            UPDATE shop_items
            SET {", ".join(updates)}
            WHERE item_id = ?
            """,
            tuple(values),
        )

        connection.commit()

    updated_item = get_shop_item_by_id(item["item_id"])

    if updated_item is None:
        raise RuntimeError("Shop item was updated, but could not be retrieved.")

    return updated_item


def deactivate_shop_item(item_name: str) -> dict:
    """
    Deactivates a shop item instead of deleting it.
    """
    item = get_shop_item_by_name_any_status(item_name.strip())

    if item is None:
        raise ValueError("Requested item is not registered.")

    if int(item["active"]) == 0:
        raise ValueError("Requested item is already inactive.")

    updated_item = update_shop_item(
        current_name=item["name"],
        active=False,
    )

    return updated_item