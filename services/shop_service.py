from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    DEFAULT_ITEM_CONSUMABLE,
    DEFAULT_ITEM_RARITY,
    DEFAULT_ITEM_USABLE,
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
        True,
        True,
        "Voucher redeemed. Eclipse recognizes your indulgence. Please make poor choices responsibly.",
        None,
    ),
    (
        "Obsession Perfume Sample",
        500,
        "A luxury fragrance sample from Maximillion's Obsession line.",
        "Obsession Items",
        "Uncommon",
        True,
        True,
        "Perfume sample applied. Obsession has made note of the version of you trying to surface.",
        None,
    ),
    (
        "Foxy Delights Dessert Box",
        300,
        "A curated dessert box from Foxy Delights.",
        "Foxy Delights Items",
        "Common",
        True,
        True,
        "Dessert box opened. Foxy Delights hopes the sugar helps. It usually does not, but hope is adorable.",
        None,
    ),
    (
        "Black Cab Transit Pass",
        400,
        "A short-distance private transit pass through Sin City.",
        "Transit",
        "Common",
        True,
        True,
        "Transit pass redeemed. Your route has been logged by ENVI. Comforting? No. Efficient? Yes.",
        None,
    ),
    (
        "Velvet Obelisk Visitor Pass",
        1500,
        "A limited visitor pass for approved Velvet Obelisk access.",
        "Access Passes",
        "Rare",
        True,
        False,
        "Visitor pass presented. Velvet Obelisk access credentials recognized. Behave like you were expensive to invite.",
        None,
    ),
    (
        "Luxury Gift Box",
        2000,
        "A premium social gift package for RP scenes.",
        "Luxury",
        "Luxury",
        True,
        True,
        "Luxury gift box opened. Someone either likes you, needs something from you, or both. Usually both.",
        None,
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


def normalize_bool(value: bool | None, default: bool) -> bool:
    """
    Normalizes optional boolean values.
    """

    if value is None:
        return default

    return bool(value)


def normalize_use_message(use_message: str | None) -> str | None:
    """
    Normalizes item use messages.

    Blank messages become None.
    """

    if use_message is None:
        return None

    clean_message = use_message.strip()

    if not clean_message:
        return None

    return clean_message


def normalize_stock(stock: int | None) -> int | None:
    """
    Normalizes stock values.

    None means unlimited stock.
    Any provided stock value must be 0 or greater.
    """

    if stock is None:
        return None

    if stock < 0:
        raise ValueError("Stock cannot be negative.")

    return stock


def validate_use_settings(
    usable: bool,
    consumable: bool,
    use_message: str | None,
) -> None:
    """
    Validates item use behavior.
    """

    if consumable and not usable:
        raise ValueError("Consumable items must also be usable.")

    if use_message is not None and not usable:
        raise ValueError("Items with a use message must also be usable.")


def format_stock(stock: int | None) -> str:
    """
    Formats stock for display.
    """

    if stock is None:
        return "Unlimited"

    if int(stock) == 0:
        return "Sold Out"

    return str(stock)

def decrease_item_stock(item_id: int, quantity: int) -> int | None:
    """
    Decreases stock for a limited-stock item.

    Returns None if the item has unlimited stock.
    Returns the remaining stock amount if the item has limited stock.
    """

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT stock
            FROM shop_items
            WHERE item_id = ? AND active = 1
            """,
            (item_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Requested item is not registered in the active exchange.")

        current_stock = row["stock"]

        if current_stock is None:
            return None

        current_stock = int(current_stock)

        if current_stock <= 0:
            raise ValueError("Requested item is sold out.")

        if current_stock < quantity:
            raise ValueError(
                f"Requested quantity exceeds available stock. "
                f"Available stock: {current_stock}."
            )

        remaining_stock = current_stock - quantity

        connection.execute(
            """
            UPDATE shop_items
            SET stock = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (remaining_stock, utc_now(), item_id),
        )

        connection.commit()

    return remaining_stock


def seed_default_shop_items() -> None:
    """
    Adds the default shop items if they do not already exist.

    For existing default items, this also upgrades V1.5 metadata
    only when the item still has old/default values.
    """

    now = utc_now()

    with get_connection() as connection:
        for (
            name,
            price,
            description,
            category,
            rarity,
            usable,
            consumable,
            use_message,
            stock,
        ) in DEFAULT_SHOP_ITEMS:
            usable_value = 1 if usable else 0
            consumable_value = 1 if consumable else 0

            connection.execute(
                """
                INSERT OR IGNORE INTO shop_items (
                    name,
                    price,
                    description,
                    category,
                    rarity,
                    usable,
                    consumable,
                    use_message,
                    stock,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    name,
                    price,
                    description,
                    category,
                    rarity,
                    usable_value,
                    consumable_value,
                    use_message,
                    stock,
                    now,
                    now,
                ),
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

            connection.execute(
                """
                UPDATE shop_items
                SET
                    usable = ?,
                    consumable = ?,
                    use_message = ?,
                    updated_at = ?
                WHERE
                    name = ?
                    AND usable = 0
                    AND consumable = 0
                    AND use_message IS NULL
                """,
                (
                    usable_value,
                    consumable_value,
                    use_message,
                    now,
                    name,
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
                    rarity,
                    usable,
                    consumable,
                    use_message,
                    stock
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
                    rarity,
                    usable,
                    consumable,
                    use_message,
                    stock
                FROM shop_items
                WHERE active = 1 AND category = ?
                ORDER BY price ASC, name ASC
                """,
                (clean_category,),
            ).fetchall()

    return [dict(row) for row in rows]

def get_all_shop_items() -> list[dict]:
    """
    Returns every registered shop item.

    Active and inactive items are included so administrative commands
    can inspect, edit, or manage the complete item catalog.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description,
                active,
                category,
                rarity,
                usable,
                consumable,
                use_message,
                stock
            FROM shop_items
            ORDER BY
                active DESC,
                name ASC
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
                description,
                category,
                rarity,
                usable,
                consumable,
                use_message,
                stock
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
                usable,
                consumable,
                use_message,
                stock,
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
                usable,
                consumable,
                use_message,
                stock,
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
    usable: bool | None = None,
    consumable: bool | None = None,
    use_message: str | None = None,
    stock: int | None = None,
) -> dict:
    """
    Creates a new active shop item.
    """

    clean_name = name.strip()
    clean_description = description.strip()
    clean_category = validate_shop_category(category)
    clean_rarity = validate_item_rarity(rarity)
    clean_usable = normalize_bool(usable, DEFAULT_ITEM_USABLE)
    clean_consumable = normalize_bool(consumable, DEFAULT_ITEM_CONSUMABLE)
    clean_use_message = normalize_use_message(use_message)
    clean_stock = normalize_stock(stock)

    validate_use_settings(
        usable=clean_usable,
        consumable=clean_consumable,
        use_message=clean_use_message,
    )

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
                usable,
                consumable,
                use_message,
                stock,
                active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                clean_name,
                price,
                clean_description,
                clean_category,
                clean_rarity,
                1 if clean_usable else 0,
                1 if clean_consumable else 0,
                clean_use_message,
                clean_stock,
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
    usable: bool | None = None,
    consumable: bool | None = None,
    use_message: str | None = None,
    stock: int | None = None,
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

    next_usable = bool(item["usable"])
    next_consumable = bool(item["consumable"])
    next_use_message = item["use_message"]

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

    if usable is not None:
        next_usable = bool(usable)

    if consumable is not None:
        next_consumable = bool(consumable)

    if use_message is not None:
        next_use_message = normalize_use_message(use_message)

    validate_use_settings(
        usable=next_usable,
        consumable=next_consumable,
        use_message=next_use_message,
    )

    if usable is not None:
        updates.append("usable = ?")
        values.append(1 if next_usable else 0)

    if consumable is not None:
        updates.append("consumable = ?")
        values.append(1 if next_consumable else 0)

    if use_message is not None:
        updates.append("use_message = ?")
        values.append(next_use_message)

    if stock is not None:
        clean_stock = normalize_stock(stock)

        updates.append("stock = ?")
        values.append(clean_stock)

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