from __future__ import annotations

import sqlite3
import uuid

from db.database import get_connection
from services.economy_service import utc_now
from services.organization_membership_service import (
    role_has_permission,
)
from utils.constants import (
    ORGANIZATION_DEPOSIT_REFERENCE_PREFIX,
    ORGANIZATION_PERMISSION_DEPOSIT,
    ORGANIZATION_REFERENCE_ID_MAX_LENGTH,
    ORGANIZATION_TRANSACTION_MEMBER_DEPOSIT,
    ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH,
    TRANSACTION_ORGANIZATION_DEPOSIT,
)


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


def _validate_positive_amount(
    amount: object,
) -> int:
    """
    Validates a positive whole-credit amount.
    """

    if (
        isinstance(amount, bool)
        or not isinstance(amount, int)
        or amount <= 0
    ):
        raise ValueError(
            "Deposit amount must be greater than zero."
        )

    return amount


def _clean_reason(
    reason: object,
) -> str:
    """
    Validates a required financial-action reason.
    """

    if not isinstance(reason, str):
        raise ValueError(
            "Deposit reason must be text."
        )

    clean_reason = reason.strip()

    if not clean_reason:
        raise ValueError(
            "Deposit reason cannot be empty."
        )

    if (
        len(clean_reason)
        > ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH
    ):
        raise ValueError(
            "Deposit reason cannot exceed "
            f"{ORGANIZATION_TRANSACTION_REASON_MAX_LENGTH} "
            "characters."
        )

    return clean_reason


def _build_deposit_reference_id() -> str:
    """
    Creates a unique reference shared by both ledger sides.
    """

    reference_id = (
        f"{ORGANIZATION_DEPOSIT_REFERENCE_PREFIX}-"
        f"{uuid.uuid4().hex.upper()}"
    )

    if (
        len(reference_id)
        > ORGANIZATION_REFERENCE_ID_MAX_LENGTH
    ):
        raise RuntimeError(
            "Generated deposit reference exceeds "
            "the supported reference length."
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


def _get_membership_row(
    connection: sqlite3.Connection,
    organization_id: int,
    user_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves the user's organization membership.
    """

    return connection.execute(
        """
        SELECT
            membership.organization_id,
            organization.name
                AS organization_name,
            organization.organization_type,
            organization.active
                AS organization_active,
            membership.user_id,
            user.display_name,
            membership.role,
            membership.active
                AS membership_active,
            membership.joined_at,
            membership.updated_at,
            membership.removed_at
        FROM organization_members
            AS membership
        INNER JOIN organizations
            AS organization
            ON organization.organization_id
                = membership.organization_id
        INNER JOIN users AS user
            ON user.user_id
                = membership.user_id
        WHERE
            membership.organization_id = ?
            AND membership.user_id = ?
        """,
        (
            organization_id,
            user_id,
        ),
    ).fetchone()


def _get_user_transaction_row(
    connection: sqlite3.Connection,
    transaction_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one personal-side transaction.
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
    Retrieves one organization-side deposit transaction.
    """

    return connection.execute(
        """
        SELECT
            org_transaction.organization_transaction_id,
            org_transaction.organization_id,
            organization.name
                AS organization_name,
            org_transaction.actor_user_id,
            actor.display_name
                AS actor_display_name,
            org_transaction.target_user_id,
            org_transaction.target_organization_id,
            org_transaction.transaction_type,
            org_transaction.amount,
            org_transaction.balance_after,
            org_transaction.reason,
            org_transaction.related_item_id,
            org_transaction.reference_id,
            org_transaction.created_at
        FROM organization_transactions
            AS org_transaction
        INNER JOIN organizations
            AS organization
            ON organization.organization_id
                = org_transaction.organization_id
        LEFT JOIN users AS actor
            ON actor.user_id
                = org_transaction.actor_user_id
        WHERE
            org_transaction.organization_transaction_id
                = ?
        """,
        (transaction_id,),
    ).fetchone()


def deposit_user_funds_to_organization(
    *,
    organization_id: int,
    user_id: int,
    amount: int,
    reason: str,
) -> dict:
    """
    Atomically transfers personal credits into an organization.

    The following operations succeed or fail together:

    - Personal balance decreases
    - Organization balance increases
    - Personal transaction is recorded
    - Organization transaction is recorded

    Returns:
    - reference_id
    - user
    - organization
    - membership
    - user_transaction
    - organization_transaction
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    clean_amount = _validate_positive_amount(
        amount
    )

    clean_reason = _clean_reason(
        reason
    )

    reference_id = (
        _build_deposit_reference_id()
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
                    "Depositing user is not registered."
                )

            organization_row = (
                _get_organization_row(
                    connection=connection,
                    organization_id=(
                        clean_organization_id
                    ),
                )
            )

            if organization_row is None:
                raise ValueError(
                    "Requested organization is not registered."
                )

            if int(organization_row["active"]) != 1:
                raise ValueError(
                    "Inactive organizations cannot "
                    "receive new deposits."
                )

            membership_row = (
                _get_membership_row(
                    connection=connection,
                    organization_id=(
                        clean_organization_id
                    ),
                    user_id=clean_user_id,
                )
            )

            if (
                membership_row is None
                or int(
                    membership_row[
                        "membership_active"
                    ]
                )
                != 1
            ):
                raise ValueError(
                    "You are not an active member "
                    "of this organization."
                )

            if not role_has_permission(
                role=membership_row["role"],
                permission=(
                    ORGANIZATION_PERMISSION_DEPOSIT
                ),
            ):
                raise ValueError(
                    "Your organization role does not "
                    "permit this action."
                )

            current_user_balance = int(
                user_row["balance"]
            )

            if current_user_balance < clean_amount:
                raise ValueError(
                    "Insufficient Nexus Credits."
                )

            current_organization_balance = int(
                organization_row["balance"]
            )

            updated_user_balance = (
                current_user_balance
                - clean_amount
            )

            updated_organization_balance = (
                current_organization_balance
                + clean_amount
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

            connection.execute(
                """
                UPDATE organizations
                SET
                    balance = ?,
                    updated_at = ?
                WHERE organization_id = ?
                """,
                (
                    updated_organization_balance,
                    now,
                    clean_organization_id,
                ),
            )

            user_transaction_reason = (
                "Organization deposit to "
                f"{organization_row['name']}. "
                f"Reason: {clean_reason} "
                f"Reference: {reference_id}."
            )

            user_transaction_cursor = (
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
                    VALUES (?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        clean_user_id,
                        (
                            TRANSACTION_ORGANIZATION_DEPOSIT
                        ),
                        -clean_amount,
                        user_transaction_reason,
                        now,
                    ),
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
                        NULL,
                        NULL,
                        ?,
                        ?,
                        ?,
                        ?,
                        NULL,
                        ?,
                        ?
                    )
                    """,
                    (
                        clean_organization_id,
                        clean_user_id,
                        (
                            ORGANIZATION_TRANSACTION_MEMBER_DEPOSIT
                        ),
                        clean_amount,
                        updated_organization_balance,
                        clean_reason,
                        reference_id,
                        now,
                    ),
                )
            )

            user_transaction_id = int(
                user_transaction_cursor.lastrowid
            )

            organization_transaction_id = int(
                organization_transaction_cursor.lastrowid
            )

            updated_user_row = _get_user_row(
                connection=connection,
                user_id=clean_user_id,
            )

            updated_organization_row = (
                _get_organization_row(
                    connection=connection,
                    organization_id=(
                        clean_organization_id
                    ),
                )
            )

            user_transaction_row = (
                _get_user_transaction_row(
                    connection=connection,
                    transaction_id=(
                        user_transaction_id
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

            if updated_user_row is None:
                raise RuntimeError(
                    "Deposit changed the personal balance "
                    "but the updated account could not "
                    "be retrieved."
                )

            if updated_organization_row is None:
                raise RuntimeError(
                    "Deposit changed the organization balance "
                    "but the updated organization could not "
                    "be retrieved."
                )

            if user_transaction_row is None:
                raise RuntimeError(
                    "Deposit changed balances but the "
                    "personal transaction could not "
                    "be retrieved."
                )

            if organization_transaction_row is None:
                raise RuntimeError(
                    "Deposit changed balances but the "
                    "organization transaction could not "
                    "be retrieved."
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Organization deposit could not be completed. "
            "No funds were moved."
        ) from error

    return {
        "reference_id": reference_id,
        "user": dict(updated_user_row),
        "organization": dict(
            updated_organization_row
        ),
        "membership": dict(membership_row),
        "user_transaction": dict(
            user_transaction_row
        ),
        "organization_transaction": dict(
            organization_transaction_row
        ),
    }