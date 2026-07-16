from __future__ import annotations

import sqlite3
import uuid

from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    ORGANIZATION_REFERENCE_ID_MAX_LENGTH,
    ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH,
    ORGANIZATION_TRANSACTION_SHOP_SALE,
    SHOP_PURCHASE_REFERENCE_PREFIX,
    TRANSACTION_COMMERCIAL_SHOP_PURCHASE,
    TRANSACTION_SHOP_PURCHASE,
)


SQLITE_MAX_INTEGER = 9_223_372_036_854_775_807


def _validate_positive_id(
    value: object,
    field_name: str,
) -> int:
    """
    Validates a positive integer database identifier.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    return value


def _validate_quantity(
    quantity: object,
) -> int:
    """
    Validates a positive whole-item purchase quantity.
    """
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise ValueError(
            "Quantity must be greater than zero."
        )

    return quantity


def _clean_item_name(
    item_name: object,
) -> str:
    """
    Validates the requested shop item name.
    """
    if not isinstance(item_name, str):
        raise ValueError(
            "Item name must be text."
        )

    clean_item_name = item_name.strip()

    if not clean_item_name:
        raise ValueError(
            "Item name cannot be empty."
        )

    return clean_item_name


def _build_purchase_reference_id() -> str:
    """
    Creates a unique purchase reference.

    Commercial purchases share this reference between the
    personal and organization ledger records. System
    purchases retain it in the personal transaction and
    staff log.
    """
    reference_id = (
        f"{SHOP_PURCHASE_REFERENCE_PREFIX}-"
        f"{uuid.uuid4().hex.upper()}"
    )

    if (
        len(reference_id)
        > ORGANIZATION_REFERENCE_ID_MAX_LENGTH
    ):
        raise RuntimeError(
            "Generated purchase reference exceeds the "
            "supported reference length."
        )

    return reference_id


def _get_user_row(
    connection: sqlite3.Connection,
    user_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one personal ENVI account.
    """
    return connection.execute(
        """
        SELECT
            user_id,
            display_name,
            balance,
            created_at,
            updated_at
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()


def _get_shop_item_row(
    connection: sqlite3.Connection,
    item_name: str,
) -> sqlite3.Row | None:
    """
    Retrieves one active or inactive shop item and its
    optional seller metadata.
    """
    return connection.execute(
        """
        SELECT
            item.item_id,
            item.name,
            item.price,
            item.description,
            item.category,
            item.rarity,
            item.usable,
            item.consumable,
            item.use_message,
            item.stock,
            item.seller_org_id,
            item.active,
            item.created_at,
            item.updated_at,
            seller.name AS seller_org_name,
            seller.organization_type AS seller_org_type,
            seller.balance AS seller_org_balance,
            seller.active AS seller_org_active
        FROM shop_items AS item
        LEFT JOIN organizations AS seller
            ON seller.organization_id =
                item.seller_org_id
        WHERE LOWER(item.name) = LOWER(?)
        """,
        (item_name,),
    ).fetchone()


def _get_organization_row(
    connection: sqlite3.Connection,
    organization_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one active or inactive organization.
    """
    return connection.execute(
        """
        SELECT
            organization_id,
            name,
            organization_type,
            description,
            balance,
            active,
            created_at,
            updated_at
        FROM organizations
        WHERE organization_id = ?
        """,
        (organization_id,),
    ).fetchone()


def _get_personal_transaction_row(
    connection: sqlite3.Connection,
    transaction_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one personal purchase transaction.
    """
    return connection.execute(
        """
        SELECT
            transaction_id,
            user_id,
            target_user_id,
            type,
            amount,
            reason,
            created_at
        FROM transactions
        WHERE transaction_id = ?
        """,
        (transaction_id,),
    ).fetchone()


def _get_organization_transaction_row(
    connection: sqlite3.Connection,
    transaction_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one organization sale transaction.
    """
    return connection.execute(
        """
        SELECT
            organization_transaction_id,
            organization_id,
            actor_user_id,
            target_user_id,
            target_organization_id,
            transaction_type,
            amount,
            balance_after,
            reason,
            related_item_id,
            reference_id,
            created_at
        FROM organization_transactions
        WHERE organization_transaction_id = ?
        """,
        (transaction_id,),
    ).fetchone()


def _get_inventory_quantity(
    connection: sqlite3.Connection,
    user_id: int,
    item_id: int,
) -> int:
    """
    Returns the user's current quantity of one item.
    """
    row = connection.execute(
        """
        SELECT quantity
        FROM inventory
        WHERE user_id = ?
        AND item_id = ?
        """,
        (
            user_id,
            item_id,
        ),
    ).fetchone()

    if row is None:
        return 0

    return int(row["quantity"])


def _build_organization_sale_reason(
    *,
    quantity: int,
    item_name: str,
    buyer_user_id: int,
) -> str:
    """
    Builds a concise organization-ledger sale reason.
    """
    reason = (
        f"Sold {quantity}x {item_name} "
        f"to citizen {buyer_user_id}."
    )

    if (
        len(reason)
        <= ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH
    ):
        return reason

    fallback_reason = (
        f"Commercial shop sale to citizen "
        f"{buyer_user_id}."
    )

    if (
        len(fallback_reason)
        > ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH
    ):
        raise RuntimeError(
            "Organization sale reason exceeds the "
            "supported length."
        )

    return fallback_reason


def purchase_shop_item(
    *,
    user_id: int,
    item_name: str,
    quantity: int = 1,
) -> dict:
    """
    Atomically purchases an active shop item.

    Every required operation succeeds or fails together:

    - Buyer balance decreases
    - Limited stock decreases
    - Buyer inventory increases
    - Personal transaction is created
    - Active organization seller receives revenue
    - Organization sale transaction is created

    System-owned purchases create no organization record
    and remove their value from circulation.

    Returns:

    - reference_id
    - purchase_mode
    - user
    - item
    - quantity
    - total_price
    - user_balance_before
    - remaining_stock
    - inventory_quantity
    - personal_transaction
    - seller_organization
    - seller_balance_before
    - organization_transaction
    """
    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )
    clean_item_name = _clean_item_name(
        item_name
    )
    clean_quantity = _validate_quantity(
        quantity
    )
    reference_id = (
        _build_purchase_reference_id()
    )

    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            user_row = _get_user_row(
                connection=connection,
                user_id=clean_user_id,
            )
            if user_row is None:
                raise ValueError(
                    "Purchasing user is not registered."
                )

            item_row = _get_shop_item_row(
                connection=connection,
                item_name=clean_item_name,
            )
            if item_row is None:
                raise ValueError(
                    "Requested item is not registered."
                )

            if int(item_row["active"]) != 1:
                raise ValueError(
                    "Requested item is not registered in "
                    "the active exchange."
                )

            item_id = int(
                item_row["item_id"]
            )
            item_price = int(
                item_row["price"]
            )

            total_price = (
                item_price
                * clean_quantity
            )

            if (
                total_price <= 0
                or total_price > SQLITE_MAX_INTEGER
            ):
                raise ValueError(
                    "Purchase total exceeds the supported "
                    "Nexus Credit range."
                )

            current_user_balance = int(
                user_row["balance"]
            )

            if current_user_balance < total_price:
                raise ValueError(
                    "Insufficient Nexus Credits."
                )

            current_stock = item_row["stock"]

            if current_stock is None:
                remaining_stock = None
            else:
                current_stock = int(
                    current_stock
                )

                if current_stock <= 0:
                    raise ValueError(
                        "Requested item is sold out."
                    )

                if current_stock < clean_quantity:
                    raise ValueError(
                        "Requested quantity exceeds "
                        "available stock. "
                        f"Available stock: {current_stock}."
                    )

                remaining_stock = (
                    current_stock
                    - clean_quantity
                )

            inventory_quantity_before = (
                _get_inventory_quantity(
                    connection=connection,
                    user_id=clean_user_id,
                    item_id=item_id,
                )
            )

            if (
                inventory_quantity_before
                > SQLITE_MAX_INTEGER
                - clean_quantity
            ):
                raise ValueError(
                    "Inventory quantity would exceed the "
                    "supported range."
                )

            inventory_quantity_after = (
                inventory_quantity_before
                + clean_quantity
            )

            seller_org_id = item_row[
                "seller_org_id"
            ]
            seller_organization_row = None
            seller_balance_before = None
            seller_balance_after = None

            if seller_org_id is not None:
                seller_org_id = int(
                    seller_org_id
                )

                seller_organization_row = (
                    _get_organization_row(
                        connection=connection,
                        organization_id=(
                            seller_org_id
                        ),
                    )
                )

                if seller_organization_row is None:
                    raise ValueError(
                        "Item seller organization is no "
                        "longer registered."
                    )

                if (
                    int(
                        seller_organization_row[
                            "active"
                        ]
                    )
                    != 1
                ):
                    raise ValueError(
                        "Seller organization is inactive. "
                        "This item cannot be purchased until "
                        "the seller is reactivated or the "
                        "item is reassigned."
                    )

                seller_balance_before = int(
                    seller_organization_row[
                        "balance"
                    ]
                )

                if (
                    seller_balance_before
                    > SQLITE_MAX_INTEGER
                    - total_price
                ):
                    raise ValueError(
                        "Seller organization balance cannot "
                        "accept this purchase total."
                    )

                seller_balance_after = (
                    seller_balance_before
                    + total_price
                )

            updated_user_balance = (
                current_user_balance
                - total_price
            )
            now = utc_now()

            connection.execute(
                """
                UPDATE users
                SET
                    balance = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (
                    updated_user_balance,
                    now,
                    clean_user_id,
                ),
            )

            if remaining_stock is not None:
                connection.execute(
                    """
                    UPDATE shop_items
                    SET
                        stock = ?,
                        updated_at = ?
                    WHERE item_id = ?
                    """,
                    (
                        remaining_stock,
                        now,
                        item_id,
                    ),
                )

            connection.execute(
                """
                INSERT INTO inventory (
                    user_id,
                    item_id,
                    quantity
                )
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id)
                DO UPDATE SET
                    quantity = quantity
                        + excluded.quantity
                """,
                (
                    clean_user_id,
                    item_id,
                    clean_quantity,
                ),
            )

            if seller_org_id is None:
                purchase_mode = "SYSTEM"
                personal_transaction_type = (
                    TRANSACTION_SHOP_PURCHASE
                )
                seller_name = (
                    "ENVI Commercial Exchange"
                )
            else:
                purchase_mode = "ORGANIZATION"
                personal_transaction_type = (
                    TRANSACTION_COMMERCIAL_SHOP_PURCHASE
                )
                seller_name = str(
                    seller_organization_row[
                        "name"
                    ]
                )

                connection.execute(
                    """
                    UPDATE organizations
                    SET
                        balance = ?,
                        updated_at = ?
                    WHERE organization_id = ?
                    """,
                    (
                        seller_balance_after,
                        now,
                        seller_org_id,
                    ),
                )

            personal_transaction_reason = (
                f"Purchased {clean_quantity}x "
                f"{item_row['name']}. "
                f"Seller: {seller_name}. "
                f"Reference: {reference_id}."
            )

            personal_transaction_cursor = (
                connection.execute(
                    """
                    INSERT INTO transactions (
                        user_id,
                        target_user_id,
                        type,
                        amount,
                        reason,
                        created_at
                    )
                    VALUES (
                        ?,
                        NULL,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    (
                        clean_user_id,
                        personal_transaction_type,
                        -total_price,
                        personal_transaction_reason,
                        now,
                    ),
                )
            )

            personal_transaction_id = int(
                personal_transaction_cursor.lastrowid
            )

            organization_transaction_id = None

            if seller_org_id is not None:
                sale_reason = (
                    _build_organization_sale_reason(
                        quantity=clean_quantity,
                        item_name=str(
                            item_row["name"]
                        ),
                        buyer_user_id=clean_user_id,
                    )
                )

                organization_transaction_cursor = (
                    connection.execute(
                        """
                        INSERT INTO
                        organization_transactions (
                            organization_id,
                            actor_user_id,
                            target_user_id,
                            target_organization_id,
                            transaction_type,
                            amount,
                            balance_after,
                            reason,
                            related_item_id,
                            reference_id,
                            created_at
                        )
                        VALUES (
                            ?,
                            ?,
                            ?,
                            NULL,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        )
                        """,
                        (
                            seller_org_id,
                            clean_user_id,
                            clean_user_id,
                            (
                                ORGANIZATION_TRANSACTION_SHOP_SALE
                            ),
                            total_price,
                            seller_balance_after,
                            sale_reason,
                            item_id,
                            reference_id,
                            now,
                        ),
                    )
                )

                organization_transaction_id = int(
                    organization_transaction_cursor.lastrowid
                )

            updated_user_row = _get_user_row(
                connection=connection,
                user_id=clean_user_id,
            )
            updated_item_row = _get_shop_item_row(
                connection=connection,
                item_name=str(
                    item_row["name"]
                ),
            )
            personal_transaction_row = (
                _get_personal_transaction_row(
                    connection=connection,
                    transaction_id=(
                        personal_transaction_id
                    ),
                )
            )

            updated_seller_organization_row = None
            organization_transaction_row = None

            if seller_org_id is not None:
                updated_seller_organization_row = (
                    _get_organization_row(
                        connection=connection,
                        organization_id=(
                            seller_org_id
                        ),
                    )
                )
                organization_transaction_row = (
                    _get_organization_transaction_row(
                        connection=connection,
                        transaction_id=(
                            organization_transaction_id
                        ),
                    )
                )

            recorded_inventory_quantity = (
                _get_inventory_quantity(
                    connection=connection,
                    user_id=clean_user_id,
                    item_id=item_id,
                )
            )

            if updated_user_row is None:
                raise RuntimeError(
                    "Purchase changed the buyer balance "
                    "but the updated account could not be "
                    "retrieved."
                )

            if updated_item_row is None:
                raise RuntimeError(
                    "Purchase changed item data but the "
                    "updated item could not be retrieved."
                )

            if personal_transaction_row is None:
                raise RuntimeError(
                    "Purchase changed account data but its "
                    "personal transaction could not be "
                    "retrieved."
                )

            if (
                recorded_inventory_quantity
                != inventory_quantity_after
            ):
                raise RuntimeError(
                    "Purchase inventory quantity could not "
                    "be verified."
                )

            if (
                seller_org_id is not None
                and updated_seller_organization_row is None
            ):
                raise RuntimeError(
                    "Purchase changed seller revenue but "
                    "the updated organization could not be "
                    "retrieved."
                )

            if (
                seller_org_id is not None
                and organization_transaction_row is None
            ):
                raise RuntimeError(
                    "Purchase changed seller revenue but "
                    "the organization sale record could "
                    "not be retrieved."
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Shop purchase could not be completed. "
            "No balance, stock, inventory, or ledger "
            "changes were retained."
        ) from error

    return {
        "reference_id": reference_id,
        "purchase_mode": purchase_mode,
        "user": dict(
            updated_user_row
        ),
        "item": dict(
            updated_item_row
        ),
        "quantity": clean_quantity,
        "total_price": total_price,
        "user_balance_before": (
            current_user_balance
        ),
        "remaining_stock": remaining_stock,
        "inventory_quantity": (
            recorded_inventory_quantity
        ),
        "personal_transaction": dict(
            personal_transaction_row
        ),
        "seller_organization": (
            dict(
                updated_seller_organization_row
            )
            if updated_seller_organization_row
            is not None
            else None
        ),
        "seller_balance_before": (
            seller_balance_before
        ),
        "organization_transaction": (
            dict(
                organization_transaction_row
            )
            if organization_transaction_row
            is not None
            else None
        ),
    }