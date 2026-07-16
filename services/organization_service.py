from __future__ import annotations

import sqlite3

from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    ORGANIZATION_DESCRIPTION_MAX_LENGTH,
    ORGANIZATION_NAME_MAX_LENGTH,
    ORGANIZATION_REFERENCE_ID_MAX_LENGTH,
    ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH,
    ORGANIZATION_TRANSACTION_TYPE_MAX_LENGTH,
    ORGANIZATION_TYPES,
)


def _clean_required_text(
    value: object,
    field_name: str,
    max_length: int,
) -> str:
    """
    Validates and normalizes required text.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be text."
        )

    clean_value = value.strip()

    if not clean_value:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    if len(clean_value) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed "
            f"{max_length} characters."
        )

    return clean_value


def _clean_optional_text(
    value: object | None,
    field_name: str,
    max_length: int,
) -> str | None:
    """
    Validates optional text.

    Blank optional text is stored as None.
    """

    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be text."
        )

    clean_value = value.strip()

    if not clean_value:
        return None

    if len(clean_value) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed "
            f"{max_length} characters."
        )

    return clean_value


def _clean_description(
    description: object | None,
) -> str:
    """
    Validates an organization description.

    Blank descriptions are permitted.
    """

    if description is None:
        return ""

    if not isinstance(description, str):
        raise ValueError(
            "Organization description must be text."
        )

    clean_description = description.strip()

    if (
        len(clean_description)
        > ORGANIZATION_DESCRIPTION_MAX_LENGTH
    ):
        raise ValueError(
            "Organization description cannot exceed "
            f"{ORGANIZATION_DESCRIPTION_MAX_LENGTH} "
            "characters."
        )

    return clean_description


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


def _validate_optional_id(
    value: object | None,
    field_name: str,
) -> int | None:
    """
    Validates an optional positive integer identifier.
    """

    if value is None:
        return None

    return _validate_positive_id(
        value=value,
        field_name=field_name,
    )


def _normalize_organization_type(
    organization_type: object,
) -> str:
    """
    Normalizes and validates an organization type.
    """

    clean_type = _clean_required_text(
        value=organization_type,
        field_name="Organization type",
        max_length=32,
    ).upper()

    if clean_type not in ORGANIZATION_TYPES:
        allowed_types = ", ".join(
            ORGANIZATION_TYPES
        )

        raise ValueError(
            "Invalid organization type. "
            f"Allowed types: {allowed_types}."
        )

    return clean_type


def _get_organization_row_by_id(
    connection: sqlite3.Connection,
    organization_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one organization row by ID.
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


def _get_transaction_row(
    connection: sqlite3.Connection,
    transaction_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one complete organization transaction.
    """

    return connection.execute(
        """
        SELECT
            org_transaction.organization_transaction_id,
            org_transaction.organization_id,
            organization.name AS organization_name,
            org_transaction.actor_user_id,
            actor.display_name AS actor_display_name,
            org_transaction.target_user_id,
            target_user.display_name AS target_display_name,
            org_transaction.target_organization_id,
            target_organization.name
                AS target_organization_name,
            org_transaction.transaction_type,
            org_transaction.amount,
            org_transaction.balance_after,
            org_transaction.reason,
            org_transaction.related_item_id,
            item.name AS related_item_name,
            org_transaction.reference_id,
            org_transaction.created_at
        FROM organization_transactions AS org_transaction
        INNER JOIN organizations AS organization
            ON organization.organization_id
                = org_transaction.organization_id
        LEFT JOIN users AS actor
            ON actor.user_id
                = org_transaction.actor_user_id
        LEFT JOIN users AS target_user
            ON target_user.user_id
                = org_transaction.target_user_id
        LEFT JOIN organizations AS target_organization
            ON target_organization.organization_id
                = org_transaction.target_organization_id
        LEFT JOIN shop_items AS item
            ON item.item_id
                = org_transaction.related_item_id
        WHERE
            org_transaction.organization_transaction_id = ?
        """,
        (transaction_id,),
    ).fetchone()


def _ensure_reference_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    identifier: int | None,
    error_message: str,
) -> None:
    """
    Validates an optional foreign-key reference.
    """

    if identifier is None:
        return

    row = connection.execute(
        f"""
        SELECT 1
        FROM {table_name}
        WHERE {column_name} = ?
        LIMIT 1
        """,
        (identifier,),
    ).fetchone()

    if row is None:
        raise ValueError(error_message)


def create_organization(
    name: str,
    organization_type: str,
    description: str = "",
) -> dict:
    """
    Creates an active organization with a zero balance.

    Starting balances are intentionally zero. Future revenue,
    deposits, and administrative balance changes must pass through
    the organization ledger.
    """

    clean_name = _clean_required_text(
        value=name,
        field_name="Organization name",
        max_length=ORGANIZATION_NAME_MAX_LENGTH,
    )

    clean_type = _normalize_organization_type(
        organization_type
    )

    clean_description = _clean_description(
        description
    )

    now = utc_now()

    with get_connection() as connection:
        existing_row = connection.execute(
            """
            SELECT organization_id
            FROM organizations
            WHERE name = ? COLLATE NOCASE
            """,
            (clean_name,),
        ).fetchone()

        if existing_row is not None:
            raise ValueError(
                "Organization name is already registered."
            )

        try:
            cursor = connection.execute(
                """
                INSERT INTO organizations (
                    name,
                    organization_type,
                    description,
                    balance,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 0, 1, ?, ?)
                """,
                (
                    clean_name,
                    clean_type,
                    clean_description,
                    now,
                    now,
                ),
            )

            organization_id = int(
                cursor.lastrowid
            )

            connection.commit()

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "Organization could not be created "
                "because its record is invalid or duplicated."
            ) from error

        organization_row = (
            _get_organization_row_by_id(
                connection=connection,
                organization_id=organization_id,
            )
        )

    if organization_row is None:
        raise RuntimeError(
            "Organization was created but could not "
            "be retrieved."
        )

    return dict(organization_row)

def update_organization(
    *,
    current_name: str,
    new_name: str | None = None,
    organization_type: str | None = None,
    description: str | None = None,
) -> dict:
    """
    Updates organization metadata without replacing its record.

    The organization ID, balance, memberships, and transaction
    history remain attached to the same organization.

    Returns:
    - before
    - after
    - changed_fields
    """

    clean_current_name = _clean_required_text(
        value=current_name,
        field_name="Current organization name",
        max_length=ORGANIZATION_NAME_MAX_LENGTH,
    )

    if (
        new_name is None
        and organization_type is None
        and description is None
    ):
        raise ValueError(
            "At least one organization field must be provided."
        )

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        current_row = connection.execute(
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
            WHERE name = ? COLLATE NOCASE
            """,
            (clean_current_name,),
        ).fetchone()

        if current_row is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        before = dict(current_row)

        updated_name = str(before["name"])
        updated_type = str(
            before["organization_type"]
        )
        updated_description = str(
            before["description"]
        )

        if new_name is not None:
            updated_name = _clean_required_text(
                value=new_name,
                field_name="New organization name",
                max_length=(
                    ORGANIZATION_NAME_MAX_LENGTH
                ),
            )

            duplicate_row = connection.execute(
                """
                SELECT organization_id
                FROM organizations
                WHERE
                    name = ? COLLATE NOCASE
                    AND organization_id != ?
                """,
                (
                    updated_name,
                    before["organization_id"],
                ),
            ).fetchone()

            if duplicate_row is not None:
                raise ValueError(
                    "Organization name is already registered."
                )

        if organization_type is not None:
            updated_type = (
                _normalize_organization_type(
                    organization_type
                )
            )

        if description is not None:
            updated_description = _clean_description(
                description
            )

        changed_fields: list[str] = []

        if updated_name != before["name"]:
            changed_fields.append("name")

        if updated_type != before["organization_type"]:
            changed_fields.append(
                "organization_type"
            )

        if (
            updated_description
            != before["description"]
        ):
            changed_fields.append("description")

        if not changed_fields:
            raise ValueError(
                "No organization changes were detected."
            )

        try:
            connection.execute(
                """
                UPDATE organizations
                SET
                    name = ?,
                    organization_type = ?,
                    description = ?,
                    updated_at = ?
                WHERE organization_id = ?
                """,
                (
                    updated_name,
                    updated_type,
                    updated_description,
                    utc_now(),
                    before["organization_id"],
                ),
            )

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "Organization could not be updated "
                "because the requested record is invalid "
                "or duplicated."
            ) from error

        updated_row = _get_organization_row_by_id(
            connection=connection,
            organization_id=(
                before["organization_id"]
            ),
        )

        connection.commit()

    if updated_row is None:
        raise RuntimeError(
            "Organization was updated but the new "
            "record could not be retrieved."
        )

    return {
        "before": before,
        "after": dict(updated_row),
        "changed_fields": tuple(
            changed_fields
        ),
    }


def deactivate_organization(
    name: str,
) -> dict:
    """
    Deactivates an organization by name.

    The organization record, balance, memberships, and complete
    financial history remain intact.
    """

    clean_name = _clean_required_text(
        value=name,
        field_name="Organization name",
        max_length=ORGANIZATION_NAME_MAX_LENGTH,
    )

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        current_row = connection.execute(
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
            WHERE name = ? COLLATE NOCASE
            """,
            (clean_name,),
        ).fetchone()

        if current_row is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        if int(current_row["active"]) != 1:
            raise ValueError(
                "Organization is already inactive."
            )

        before = dict(current_row)

        connection.execute(
            """
            UPDATE organizations
            SET
                active = 0,
                updated_at = ?
            WHERE organization_id = ?
            """,
            (
                utc_now(),
                before["organization_id"],
            ),
        )

        updated_row = _get_organization_row_by_id(
            connection=connection,
            organization_id=(
                before["organization_id"]
            ),
        )

        connection.commit()

    if updated_row is None:
        raise RuntimeError(
            "Organization was deactivated but the "
            "updated record could not be retrieved."
        )

    return {
        "before": before,
        "after": dict(updated_row),
    }

def get_organization_by_id(
    organization_id: int,
) -> dict | None:
    """
    Retrieves an active or inactive organization by ID.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    with get_connection() as connection:
        row = _get_organization_row_by_id(
            connection=connection,
            organization_id=clean_organization_id,
        )

    if row is None:
        return None

    return dict(row)


def get_organization_by_name(
    name: str,
) -> dict | None:
    """
    Retrieves an active or inactive organization by name.

    Matching is case-insensitive.
    """

    if not isinstance(name, str):
        return None

    clean_name = name.strip()

    if not clean_name:
        return None

    with get_connection() as connection:
        row = connection.execute(
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
            WHERE name = ? COLLATE NOCASE
            """,
            (clean_name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_organizations(
    *,
    active_only: bool = False,
    organization_type: str | None = None,
) -> list[dict]:
    """
    Returns organizations with optional activity and type filters.
    """

    if not isinstance(active_only, bool):
        raise ValueError(
            "active_only must be True or False."
        )

    conditions: list[str] = []
    parameters: list[object] = []

    if active_only:
        conditions.append("active = 1")

    if organization_type is not None:
        clean_type = _normalize_organization_type(
            organization_type
        )

        conditions.append(
            "organization_type = ?"
        )
        parameters.append(clean_type)

    where_clause = ""

    if conditions:
        where_clause = (
            "WHERE "
            + " AND ".join(conditions)
        )

    with get_connection() as connection:
        rows = connection.execute(
            f"""
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
            {where_clause}
            ORDER BY
                active DESC,
                name COLLATE NOCASE ASC
            """,
            parameters,
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_organization_balance(
    organization_id: int,
) -> int:
    """
    Returns an organization's current balance.
    """

    organization = get_organization_by_id(
        organization_id
    )

    if organization is None:
        raise ValueError(
            "Requested organization is not registered."
        )

    return int(organization["balance"])


def set_organization_active(
    organization_id: int,
    active: bool,
) -> dict:
    """
    Activates or deactivates an organization.

    Repeating the current status is safe and does not alter the
    existing updated timestamp.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    if not isinstance(active, bool):
        raise ValueError(
            "Organization active status must be "
            "True or False."
        )

    requested_status = 1 if active else 0

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        current_row = _get_organization_row_by_id(
            connection=connection,
            organization_id=clean_organization_id,
        )

        if current_row is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        if int(current_row["active"]) == requested_status:
            connection.rollback()
            return dict(current_row)

        connection.execute(
            """
            UPDATE organizations
            SET
                active = ?,
                updated_at = ?
            WHERE organization_id = ?
            """,
            (
                requested_status,
                utc_now(),
                clean_organization_id,
            ),
        )

        updated_row = _get_organization_row_by_id(
            connection=connection,
            organization_id=clean_organization_id,
        )

        connection.commit()

    if updated_row is None:
        raise RuntimeError(
            "Organization status changed but the "
            "updated record could not be retrieved."
        )

    return dict(updated_row)


def adjust_organization_balance(
    *,
    organization_id: int,
    amount: int,
    transaction_type: str,
    reason: str,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    target_organization_id: int | None = None,
    related_item_id: int | None = None,
    reference_id: str | None = None,
) -> dict:
    """
    Atomically changes an active organization's balance and records
    the resulting ledger transaction.

    Positive amounts add funds.
    Negative amounts remove funds.

    No balance change is committed unless the complete transaction
    record is also created successfully.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    if (
        isinstance(amount, bool)
        or not isinstance(amount, int)
    ):
        raise ValueError(
            "Organization transaction amount "
            "must be an integer."
        )

    if amount == 0:
        raise ValueError(
            "Organization transaction amount "
            "cannot be zero."
        )

    clean_transaction_type = (
        _clean_required_text(
            value=transaction_type,
            field_name="Transaction type",
            max_length=(
                ORGANIZATION_TRANSACTION_TYPE_MAX_LENGTH
            ),
        ).upper()
    )

    clean_reason = _clean_required_text(
        value=reason,
        field_name="Transaction reason",
        max_length=(
            ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH
        ),
    )

    clean_actor_user_id = _validate_optional_id(
        value=actor_user_id,
        field_name="Actor user ID",
    )

    clean_target_user_id = _validate_optional_id(
        value=target_user_id,
        field_name="Target user ID",
    )

    clean_target_organization_id = (
        _validate_optional_id(
            value=target_organization_id,
            field_name="Target organization ID",
        )
    )

    clean_related_item_id = _validate_optional_id(
        value=related_item_id,
        field_name="Related item ID",
    )

    clean_reference_id = _clean_optional_text(
        value=reference_id,
        field_name="Reference ID",
        max_length=(
            ORGANIZATION_REFERENCE_ID_MAX_LENGTH
        ),
    )

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        organization_row = (
            _get_organization_row_by_id(
                connection=connection,
                organization_id=clean_organization_id,
            )
        )

        if organization_row is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        if int(organization_row["active"]) != 1:
            raise ValueError(
                "Inactive organizations cannot perform "
                "new financial activity."
            )

        _ensure_reference_exists(
            connection=connection,
            table_name="users",
            column_name="user_id",
            identifier=clean_actor_user_id,
            error_message=(
                "Actor user is not registered."
            ),
        )

        _ensure_reference_exists(
            connection=connection,
            table_name="users",
            column_name="user_id",
            identifier=clean_target_user_id,
            error_message=(
                "Target user is not registered."
            ),
        )

        _ensure_reference_exists(
            connection=connection,
            table_name="organizations",
            column_name="organization_id",
            identifier=(
                clean_target_organization_id
            ),
            error_message=(
                "Target organization is not registered."
            ),
        )

        _ensure_reference_exists(
            connection=connection,
            table_name="shop_items",
            column_name="item_id",
            identifier=clean_related_item_id,
            error_message=(
                "Related item is not registered."
            ),
        )

        current_balance = int(
            organization_row["balance"]
        )

        new_balance = current_balance + amount

        if new_balance < 0:
            raise ValueError(
                "Organization has insufficient "
                "Nexus Credits."
            )

        now = utc_now()

        connection.execute(
            """
            UPDATE organizations
            SET
                balance = ?,
                updated_at = ?
            WHERE organization_id = ?
            """,
            (
                new_balance,
                now,
                clean_organization_id,
            ),
        )

        transaction_cursor = connection.execute(
            """
            INSERT INTO organization_transactions (
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
                ?,
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
                clean_organization_id,
                clean_actor_user_id,
                clean_target_user_id,
                clean_target_organization_id,
                clean_transaction_type,
                amount,
                new_balance,
                clean_reason,
                clean_related_item_id,
                clean_reference_id,
                now,
            ),
        )

        transaction_id = int(
            transaction_cursor.lastrowid
        )

        updated_organization_row = (
            _get_organization_row_by_id(
                connection=connection,
                organization_id=clean_organization_id,
            )
        )

        transaction_row = _get_transaction_row(
            connection=connection,
            transaction_id=transaction_id,
        )

        connection.commit()

    if updated_organization_row is None:
        raise RuntimeError(
            "Organization balance changed but the "
            "updated organization could not be retrieved."
        )

    if transaction_row is None:
        raise RuntimeError(
            "Organization balance changed but the "
            "transaction record could not be retrieved."
        )

    return {
        "organization": dict(
            updated_organization_row
        ),
        "transaction": dict(transaction_row),
    }


def add_organization_funds(
    *,
    organization_id: int,
    amount: int,
    transaction_type: str,
    reason: str,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    target_organization_id: int | None = None,
    related_item_id: int | None = None,
    reference_id: str | None = None,
) -> dict:
    """
    Adds a positive amount to an organization and logs it.
    """

    if (
        isinstance(amount, bool)
        or not isinstance(amount, int)
        or amount <= 0
    ):
        raise ValueError(
            "Amount added must be greater than zero."
        )

    return adjust_organization_balance(
        organization_id=organization_id,
        amount=amount,
        transaction_type=transaction_type,
        reason=reason,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        target_organization_id=(
            target_organization_id
        ),
        related_item_id=related_item_id,
        reference_id=reference_id,
    )


def remove_organization_funds(
    *,
    organization_id: int,
    amount: int,
    transaction_type: str,
    reason: str,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    target_organization_id: int | None = None,
    related_item_id: int | None = None,
    reference_id: str | None = None,
) -> dict:
    """
    Removes a positive amount from an organization and logs it.
    """

    if (
        isinstance(amount, bool)
        or not isinstance(amount, int)
        or amount <= 0
    ):
        raise ValueError(
            "Amount removed must be greater than zero."
        )

    return adjust_organization_balance(
        organization_id=organization_id,
        amount=-amount,
        transaction_type=transaction_type,
        reason=reason,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        target_organization_id=(
            target_organization_id
        ),
        related_item_id=related_item_id,
        reference_id=reference_id,
    )


def get_organization_transactions(
    organization_id: int,
    limit: int = 25,
) -> list[dict]:
    """
    Returns the newest organization transactions first.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
        or limit > 100
    ):
        raise ValueError(
            "Transaction limit must be between 1 and 100."
        )

    with get_connection() as connection:
        organization_row = (
            _get_organization_row_by_id(
                connection=connection,
                organization_id=clean_organization_id,
            )
        )

        if organization_row is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        rows = connection.execute(
            """
            SELECT
                org_transaction.organization_transaction_id,
                org_transaction.organization_id,
                organization.name AS organization_name,
                org_transaction.actor_user_id,
                actor.display_name AS actor_display_name,
                org_transaction.target_user_id,
                target_user.display_name
                    AS target_display_name,
                org_transaction.target_organization_id,
                target_organization.name
                    AS target_organization_name,
                org_transaction.transaction_type,
                org_transaction.amount,
                org_transaction.balance_after,
                org_transaction.reason,
                org_transaction.related_item_id,
                item.name AS related_item_name,
                org_transaction.reference_id,
                org_transaction.created_at
            FROM organization_transactions
                AS org_transaction
            INNER JOIN organizations AS organization
                ON organization.organization_id
                    = org_transaction.organization_id
            LEFT JOIN users AS actor
                ON actor.user_id
                    = org_transaction.actor_user_id
            LEFT JOIN users AS target_user
                ON target_user.user_id
                    = org_transaction.target_user_id
            LEFT JOIN organizations
                AS target_organization
                ON target_organization.organization_id
                    = org_transaction.target_organization_id
            LEFT JOIN shop_items AS item
                ON item.item_id
                    = org_transaction.related_item_id
            WHERE org_transaction.organization_id = ?
            ORDER BY
                org_transaction.created_at DESC,
                org_transaction.organization_transaction_id
                    DESC
            LIMIT ?
            """,
            (
                clean_organization_id,
                limit,
            ),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]