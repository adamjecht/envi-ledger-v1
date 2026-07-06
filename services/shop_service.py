from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    DEFAULT_ITEM_RARITY,
    DEFAULT_SHOP_CATEGORY,
    ITEM_RARITIES,
    SHOP_CATEGORIES,
)


DEFAULT_SHOP_ITEMS = [
    (
        "Eclipse Drink Voucher",
        250,
        "A voucher redeemable for one standard drink at Eclipse.",
        "Eclipse Items",
        "Common",
    ),
    (
        "Obsession Perfume Sample",
        500,
        "A luxury fragrance sample from Maximillion's Obsession line.",
        "Obsession Items",
        "Uncommon",
    ),
    (
        "Foxy Delights Dessert Box",
        300,
        "A curated dessert box from Foxy Delights.",
        "Foxy Delights Items",
        "Common",
    ),
    (
        "Black Cab Transit Pass",
        400,
        "A short-distance private transit pass through Sin City.",
        "Transit",
        "Common",
    ),
    (
        "Velvet Obelisk Visitor Pass",
        1500,
        "A limited visitor pass for approved Velvet Obelisk access.",
        "Access Passes",
        "Rare",
    ),
    (
        "Luxury Gift Box",
        2000,
        "A premium social gift package for RP scenes.",
        "Luxury",
        "Luxury",
    ),
]


def validate_shop_category(category: str | None) -> str:
    """
    Validates and normalizes an item category.
    """

    if category is None:
        return DEFAULT_SHOP_CATEGORY

    clean_category = category.strip()

    if not clean_category:
        return DEFAULT_SHOP_CATEGORY

    if clean_category not in SHOP_CATEGORIES:
        valid_categories = ", ".join(SHOP_CATEGORIES)
        raise ValueError(f"Invalid category. Valid categories: {valid_categories}")

    return clean_category


def validate_item_rarity(rarity: str | None) -> str:
    """
    Validates and normalizes an item rarity.
    """

    if rarity is None:
        return DEFAULT_ITEM_RARITY

    clean_rarity = rarity.strip()

    if not clean_rarity:
        return DEFAULT_ITEM_RARITY

    if clean_rarity not in ITEM_RARITIES:
        valid_rarities = ", ".join(ITEM_RARITIES)
        raise ValueError(f"Invalid rarity. Valid rarities: {valid_rarities}")

    return clean_rarity


def seed_default_shop_items() -> None:
    """
    Adds the default V1 shop items if they do not already exist.

    For existing default items, this also upgrades category and rarity
    only when the item still has the old default metadata.
    """

    now = utc_now()

    with get_connection() as connection:
        for name, price, description, category, rarity in DEFAULT_SHOP_ITEMS:
            connection.execute(
                """
                INSERT OR IGNORE INTO shop_items (
                    name,
                    price,
                    description,
                    category,
                    rarity,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (name, price, description, category, rarity, now, now),
            )

            connection.execute(
                """
                UPDATE shop_items
                SET
                    category = ?,
                    rarity = ?,
                    updated_at = ?
                WHERE
                    name = ?
                    AND category = ?
                    AND rarity = ?
                """,
                (
                    category,
                    rarity,
                    now,
                    name,
                    DEFAULT_SHOP_CATEGORY,
                    DEFAULT_ITEM_RARITY,
                ),
            )

        connection.commit()


def get_active_shop_items(category: str | None = None) -> list[dict]:
    """
    Returns all active shop items.

    If a category is provided, only active items in that category are returned.
    """

    with get_connection() as connection:
        if category is None:
            rows = connection.execute(
                """
                SELECT
                    item_id,
                    name,
                    price,
                    description,
                    category,
                    rarity
                FROM shop_items
                WHERE active = 1
                ORDER BY price ASC, name ASC
                """
            ).fetchall()
        else:
            clean_category = validate_shop_category(category)

            rows = connection.execute(
                """
                SELECT
                    item_id,
                    name,
                    price,
                    description,
                    category,
                    rarity
                FROM shop_items
                WHERE active = 1 AND category = ?
                ORDER BY price ASC, name ASC
                """,
                (clean_category,),
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
                description,
                category,
                rarity
            FROM shop_items
            WHERE LOWER(name) = LOWER(?) AND active = 1
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
                category,
                rarity,
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
                category,
                rarity,
                active
            FROM shop_items
            WHERE LOWER(name) = LOWER(?)
            """,
            (item_name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def create_shop_item(
    name: str,
    price: int,
    description: str,
    category: str | None = None,
    rarity: str | None = None,
) -> dict:
    """
    Creates a new active shop item.
    """

    clean_name = name.strip()
    clean_description = description.strip()
    clean_category = validate_shop_category(category)
    clean_rarity = validate_item_rarity(rarity)

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
                category,
                rarity,
                active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                clean_name,
                price,
                clean_description,
                clean_category,
                clean_rarity,
                now,
                now,
            ),
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
    category: str | None = None,
    rarity: str | None = None,
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

    if category is not None:
        clean_category = validate_shop_category(category)

        updates.append("category = ?")
        values.append(clean_category)

    if rarity is not None:
        clean_rarity = validate_item_rarity(rarity)

        updates.append("rarity = ?")
        values.append(clean_rarity)

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