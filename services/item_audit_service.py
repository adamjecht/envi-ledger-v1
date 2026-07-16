from db.database import get_connection
from utils.constants import TRANSACTION_SHOP_PURCHASE


PURCHASE_REASON_PREFIX = "Purchased "
PURCHASE_ITEM_SEPARATOR = "x "


def _parse_purchase_quantity(
    reason: str,
    item_name: str,
) -> int | None:
    """
    Reads the quantity from the current shop-purchase reason format.

    Expected format:
    Purchased 2x Item Name.

    Returns the purchased quantity when the reason belongs to the
    requested item. Returns None when it does not match.
    """

    if not reason.startswith(PURCHASE_REASON_PREFIX):
        return None

    purchase_details = reason[len(PURCHASE_REASON_PREFIX):]

    quantity_text, separator, purchased_item = purchase_details.partition(
        PURCHASE_ITEM_SEPARATOR
    )

    if not separator:
        return None

    if purchased_item != f"{item_name}.":
        return None

    quantity_text = quantity_text.strip()

    if not quantity_text.isdigit():
        return None

    quantity = int(quantity_text)

    if quantity <= 0:
        return None

    return quantity


def get_item_audit(item_name: str) -> dict | None:
    """
    Returns a complete audit of one registered shop item.

    Active and inactive items are supported.

    Purchase statistics are based on SHOP_PURCHASE records using the
    item's current registered name because existing transaction records
    do not yet store a direct item ID.
    """

    clean_item_name = item_name.strip()

    if not clean_item_name:
        return None

    with get_connection() as connection:
        item_row = connection.execute(
            """
            SELECT
                shop.item_id,
                shop.name,
                shop.price,
                shop.description,
                shop.category,
                shop.rarity,
                shop.usable,
                shop.consumable,
                shop.use_message,
                shop.stock,
                shop.seller_org_id,
                shop.active,
                shop.created_at,
                shop.updated_at,
                seller.name AS seller_org_name,
                seller.organization_type
                    AS seller_org_type,
                seller.active AS seller_org_active
            FROM shop_items AS shop
            LEFT JOIN organizations AS seller
                ON seller.organization_id =
                    shop.seller_org_id
            WHERE LOWER(shop.name) = LOWER(?)
            """,
            (clean_item_name,),
        ).fetchone()

        if item_row is None:
            return None

        item = dict(item_row)

        ownership_row = connection.execute(
            """
            SELECT
                COUNT(*) AS holder_count,
                COALESCE(SUM(quantity), 0) AS total_owned
            FROM inventory
            WHERE
                item_id = ?
                AND quantity > 0
            """,
            (item["item_id"],),
        ).fetchone()

        purchase_rows = connection.execute(
            """
            SELECT reason
            FROM transactions
            WHERE type = ?
            ORDER BY transaction_id ASC
            """,
            (TRANSACTION_SHOP_PURCHASE,),
        ).fetchall()

    purchase_count = 0
    units_purchased = 0

    for purchase_row in purchase_rows:
        quantity = _parse_purchase_quantity(
            reason=str(purchase_row["reason"]),
            item_name=str(item["name"]),
        )

        if quantity is None:
            continue

        purchase_count += 1
        units_purchased += quantity

    item["holder_count"] = int(ownership_row["holder_count"])
    item["total_owned"] = int(ownership_row["total_owned"])
    item["purchase_count"] = purchase_count
    item["units_purchased"] = units_purchased

    return item