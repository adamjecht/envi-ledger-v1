from __future__ import annotations

import re
import sqlite3

from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    CITATION_ADMIN_NOTES_MAX_LENGTH,
    CITATION_HISTORY_LIMIT,
    CITATION_IDENTIFIER_PREFIX,
    CITATION_PAYMENT_TRANSACTION_TYPES,
    CITATION_REASON_MAX_LENGTH,
    CITATION_STATUS_OPEN,
    CITATION_STATUS_PAID,
    CITATION_STATUS_VOID,
    CITATION_STATUSES,
    TRANSACTION_FINE_COLLECTION,
    TRANSACTION_FINE_PAYMENT,
)


SQLITE_MAX_INTEGER = 9_223_372_036_854_775_807


CITATION_IDENTIFIER_PATTERN = re.compile(
    rf"^{re.escape(CITATION_IDENTIFIER_PREFIX)}-"
    r"(\d{6,})$",
    re.IGNORECASE,
)


CITATION_SELECT = """
    SELECT
        citation.citation_id,
        citation.user_id,
        citizen.display_name
            AS user_display_name,
        citation.issuer_user_id,
        issuer.display_name
            AS issuer_display_name,
        citation.amount,
        citation.reason,
        citation.status,
        citation.issued_at,
        citation.updated_at,
        citation.paid_at,
        citation.voided_at,
        citation.paid_by_user_id,
        paid_by.display_name
            AS paid_by_display_name,
        citation.voided_by_user_id,
        voided_by.display_name
            AS voided_by_display_name,
        citation.payment_transaction_id,
        payment.type
            AS payment_transaction_type,
        payment.amount
            AS payment_transaction_amount,
        payment.reason
            AS payment_transaction_reason,
        payment.created_at
            AS payment_transaction_created_at,
        citation.administrative_notes
    FROM citations AS citation
    INNER JOIN users AS citizen
        ON citizen.user_id = citation.user_id
    INNER JOIN users AS issuer
        ON issuer.user_id = citation.issuer_user_id
    LEFT JOIN users AS paid_by
        ON paid_by.user_id
            = citation.paid_by_user_id
    LEFT JOIN users AS voided_by
        ON voided_by.user_id
            = citation.voided_by_user_id
    LEFT JOIN transactions AS payment
        ON payment.transaction_id
            = citation.payment_transaction_id
"""


def _validate_positive_id(
    value: object,
    field_name: str,
) -> int:
    """
    Validates a positive integer identifier.
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


def _validate_amount(
    amount: object,
) -> int:
    """
    Validates a positive whole-credit citation amount.
    """
    if (
        isinstance(amount, bool)
        or not isinstance(amount, int)
        or amount <= 0
    ):
        raise ValueError(
            "Citation amount must be greater than zero."
        )

    if amount > SQLITE_MAX_INTEGER:
        raise ValueError(
            "Citation amount exceeds the supported "
            "Nexus Credit range."
        )

    return amount


def _clean_required_text(
    value: object,
    field_name: str,
    max_length: int,
) -> str:
    """
    Validates required citation text.
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


def _clean_optional_notes(
    value: object | None,
) -> str:
    """
    Validates optional administrative notes.
    """
    if value is None:
        return ""

    if not isinstance(value, str):
        raise ValueError(
            "Administrative notes must be text."
        )

    clean_value = value.strip()

    if len(clean_value) > (
        CITATION_ADMIN_NOTES_MAX_LENGTH
    ):
        raise ValueError(
            "Administrative notes cannot exceed "
            f"{CITATION_ADMIN_NOTES_MAX_LENGTH} "
            "characters."
        )

    return clean_value


def _merge_administrative_notes(
    existing_notes: object,
    new_notes: object | None,
) -> str:
    """
    Preserves existing notes while appending new notes.
    """
    existing_clean = (
        str(existing_notes).strip()
        if existing_notes is not None
        else ""
    )

    new_clean = _clean_optional_notes(
        new_notes
    )

    if not new_clean:
        return existing_clean

    if existing_clean:
        combined_notes = (
            f"{existing_clean}\n{new_clean}"
        )
    else:
        combined_notes = new_clean

    if len(combined_notes) > (
        CITATION_ADMIN_NOTES_MAX_LENGTH
    ):
        raise ValueError(
            "Combined administrative notes cannot "
            f"exceed {CITATION_ADMIN_NOTES_MAX_LENGTH} "
            "characters."
        )

    return combined_notes


def _normalize_status(
    status: object,
) -> str:
    """
    Normalizes and validates one citation status.
    """
    clean_status = _clean_required_text(
        value=status,
        field_name="Citation status",
        max_length=16,
    ).upper()

    if clean_status not in CITATION_STATUSES:
        allowed_statuses = ", ".join(
            CITATION_STATUSES
        )

        raise ValueError(
            "Invalid citation status. "
            f"Allowed statuses: {allowed_statuses}."
        )

    return clean_status


def _validate_history_limit(
    limit: object,
) -> int:
    """
    Validates a citation-history result limit.
    """
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
        or limit > CITATION_HISTORY_LIMIT
    ):
        raise ValueError(
            "Citation history limit must be between "
            f"1 and {CITATION_HISTORY_LIMIT}."
        )

    return limit


def format_citation_identifier(
    citation_id: int,
) -> str:
    """
    Formats an internal citation ID as BB-000001.
    """
    clean_citation_id = _validate_positive_id(
        value=citation_id,
        field_name="Citation ID",
    )

    return (
        f"{CITATION_IDENTIFIER_PREFIX}-"
        f"{clean_citation_id:06d}"
    )


def parse_citation_identifier(
    citation_identifier: object,
) -> int:
    """
    Accepts an internal integer ID, numeric text,
    or a formatted BB identifier.
    """
    if (
        isinstance(citation_identifier, int)
        and not isinstance(
            citation_identifier,
            bool,
        )
    ):
        return _validate_positive_id(
            value=citation_identifier,
            field_name="Citation ID",
        )

    if not isinstance(
        citation_identifier,
        str,
    ):
        raise ValueError(
            "Citation identifier must be an integer "
            "or text."
        )

    clean_identifier = (
        citation_identifier.strip()
    )

    if not clean_identifier:
        raise ValueError(
            "Citation identifier cannot be empty."
        )

    if clean_identifier.isdigit():
        return _validate_positive_id(
            value=int(clean_identifier),
            field_name="Citation ID",
        )

    match = CITATION_IDENTIFIER_PATTERN.fullmatch(
        clean_identifier
    )

    if match is None:
        raise ValueError(
            "Citation identifier must use the "
            f"{CITATION_IDENTIFIER_PREFIX}-000001 "
            "format."
        )

    return _validate_positive_id(
        value=int(match.group(1)),
        field_name="Citation ID",
    )


def _ensure_user_exists(
    connection: sqlite3.Connection,
    user_id: int,
    error_message: str,
) -> None:
    """
    Ensures one ENVI account exists.
    """
    row = connection.execute(
        """
        SELECT 1
        FROM users
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if row is None:
        raise ValueError(
            error_message
        )


def _get_citation_row(
    connection: sqlite3.Connection,
    citation_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves one complete citation record.
    """
    return connection.execute(
        CITATION_SELECT
        + """
        WHERE citation.citation_id = ?
        """,
        (citation_id,),
    ).fetchone()


def _citation_to_dict(
    row: sqlite3.Row,
) -> dict:
    """
    Adds the formatted public identifier to a record.
    """
    citation = dict(row)

    citation["citation_identifier"] = (
        format_citation_identifier(
            int(
                citation["citation_id"]
            )
        )
    )

    return citation


def create_citation(
    *,
    user_id: int,
    issuer_user_id: int,
    amount: int,
    reason: str,
    administrative_notes: str | None = None,
) -> dict:
    """
    Creates one OPEN Black Badge citation.

    Creating a citation does not move credits and does
    not create a financial transaction.
    """
    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="Citizen user ID",
    )

    clean_issuer_user_id = _validate_positive_id(
        value=issuer_user_id,
        field_name="Issuer user ID",
    )

    clean_amount = _validate_amount(
        amount
    )

    clean_reason = _clean_required_text(
        value=reason,
        field_name="Citation reason",
        max_length=CITATION_REASON_MAX_LENGTH,
    )

    clean_notes = _clean_optional_notes(
        administrative_notes
    )

    now = utc_now()

    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            _ensure_user_exists(
                connection=connection,
                user_id=clean_user_id,
                error_message=(
                    "Cited user is not registered."
                ),
            )

            _ensure_user_exists(
                connection=connection,
                user_id=clean_issuer_user_id,
                error_message=(
                    "Citation issuer is not registered."
                ),
            )

            cursor = connection.execute(
                """
                INSERT INTO citations (
                    user_id,
                    issuer_user_id,
                    amount,
                    reason,
                    status,
                    issued_at,
                    updated_at,
                    paid_at,
                    voided_at,
                    paid_by_user_id,
                    voided_by_user_id,
                    payment_transaction_id,
                    administrative_notes
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    ?
                )
                """,
                (
                    clean_user_id,
                    clean_issuer_user_id,
                    clean_amount,
                    clean_reason,
                    CITATION_STATUS_OPEN,
                    now,
                    now,
                    clean_notes,
                ),
            )

            citation_id = int(
                cursor.lastrowid
            )

            citation_row = _get_citation_row(
                connection=connection,
                citation_id=citation_id,
            )

            if citation_row is None:
                raise RuntimeError(
                    "Citation was created but could "
                    "not be retrieved."
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Citation could not be created. "
            "No partial citation record was retained."
        ) from error

    return _citation_to_dict(
        citation_row
    )


def get_citation(
    citation_identifier: object,
) -> dict | None:
    """
    Retrieves a citation using its internal or public ID.
    """
    citation_id = parse_citation_identifier(
        citation_identifier
    )

    with get_connection() as connection:
        row = _get_citation_row(
            connection=connection,
            citation_id=citation_id,
        )

    if row is None:
        return None

    return _citation_to_dict(
        row
    )


def get_user_citations(
    *,
    user_id: int,
    status: str | None = None,
    limit: int = CITATION_HISTORY_LIMIT,
) -> list[dict]:
    """
    Returns a citizen's newest citations first.
    """
    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="Citizen user ID",
    )

    clean_limit = _validate_history_limit(
        limit
    )

    conditions = [
        "citation.user_id = ?",
    ]

    parameters: list[object] = [
        clean_user_id,
    ]

    if status is not None:
        clean_status = _normalize_status(
            status
        )

        conditions.append(
            "citation.status = ?"
        )

        parameters.append(
            clean_status
        )

    where_clause = " AND ".join(
        conditions
    )

    parameters.append(
        clean_limit
    )

    with get_connection() as connection:
        rows = connection.execute(
            CITATION_SELECT
            + f"""
            WHERE {where_clause}
            ORDER BY
                citation.issued_at DESC,
                citation.citation_id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()

    return [
        _citation_to_dict(row)
        for row in rows
    ]


def get_citation_report(
    *,
    user_id: int | None = None,
) -> dict:
    """
    Returns count and value totals by citation status.

    When user_id is provided, only that citizen's
    citations are included.
    """
    conditions: list[str] = []
    parameters: list[object] = []

    clean_user_id = None

    if user_id is not None:
        clean_user_id = _validate_positive_id(
            value=user_id,
            field_name="Citizen user ID",
        )

        conditions.append(
            "citation.user_id = ?"
        )

        parameters.append(
            clean_user_id
        )

    where_clause = ""

    if conditions:
        where_clause = (
            "WHERE "
            + " AND ".join(
                conditions
            )
        )

    with get_connection() as connection:
        summary_row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total_count,
                COALESCE(
                    SUM(citation.amount),
                    0
                ) AS total_value,

                COALESCE(
                    SUM(
                        CASE
                            WHEN citation.status = ?
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS open_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN citation.status = ?
                            THEN citation.amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS open_value,

                COALESCE(
                    SUM(
                        CASE
                            WHEN citation.status = ?
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS paid_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN citation.status = ?
                            THEN citation.amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS paid_value,

                COALESCE(
                    SUM(
                        CASE
                            WHEN citation.status = ?
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS void_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN citation.status = ?
                            THEN citation.amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS void_value
            FROM citations AS citation
            {where_clause}
            """,
            (
                CITATION_STATUS_OPEN,
                CITATION_STATUS_OPEN,
                CITATION_STATUS_PAID,
                CITATION_STATUS_PAID,
                CITATION_STATUS_VOID,
                CITATION_STATUS_VOID,
                *parameters,
            ),
        ).fetchone()

        payment_conditions = [
            "citation.status = ?",
            "citation.payment_transaction_id "
            "IS NOT NULL",
        ]

        payment_parameters: list[object] = [
            CITATION_STATUS_PAID,
        ]

        if clean_user_id is not None:
            payment_conditions.append(
                "citation.user_id = ?"
            )

            payment_parameters.append(
                clean_user_id
            )

        payment_where_clause = (
            "WHERE "
            + " AND ".join(
                payment_conditions
            )
        )

        payment_rows = connection.execute(
            f"""
            SELECT
                payment.type
                    AS transaction_type,
                COUNT(*) AS transaction_count,
                COALESCE(
                    SUM(
                        -payment.amount
                    ),
                    0
                ) AS credits_removed
            FROM citations AS citation
            INNER JOIN transactions AS payment
                ON payment.transaction_id
                    = citation.payment_transaction_id
            {payment_where_clause}
            GROUP BY payment.type
            ORDER BY payment.type ASC
            """,
            payment_parameters,
        ).fetchall()

    payment_types = {
        str(row["transaction_type"]): {
            "transaction_count": int(
                row["transaction_count"]
            ),
            "credits_removed": int(
                row["credits_removed"]
            ),
        }
        for row in payment_rows
    }

    return {
        "user_id": clean_user_id,
        "total_count": int(
            summary_row["total_count"]
        ),
        "total_value": int(
            summary_row["total_value"]
        ),
        "open_count": int(
            summary_row["open_count"]
        ),
        "open_value": int(
            summary_row["open_value"]
        ),
        "paid_count": int(
            summary_row["paid_count"]
        ),
        "paid_value": int(
            summary_row["paid_value"]
        ),
        "void_count": int(
            summary_row["void_count"]
        ),
        "void_value": int(
            summary_row["void_value"]
        ),
        "payment_types": payment_types,
    }


def mark_citation_paid_on_connection(
    *,
    connection: sqlite3.Connection,
    citation_identifier: object,
    paid_by_user_id: int,
    payment_transaction_id: int,
    administrative_notes: str | None = None,
) -> dict:
    """
    Marks one OPEN citation PAID using an existing
    matching personal transaction.

    This function does not commit. Future payment and
    collection services can call it inside the same
    transaction that debits the citizen and creates the
    payment transaction.
    """
    citation_id = parse_citation_identifier(
        citation_identifier
    )

    clean_paid_by_user_id = (
        _validate_positive_id(
            value=paid_by_user_id,
            field_name="Payment actor user ID",
        )
    )

    clean_payment_transaction_id = (
        _validate_positive_id(
            value=payment_transaction_id,
            field_name=(
                "Payment transaction ID"
            ),
        )
    )

    citation_row = _get_citation_row(
        connection=connection,
        citation_id=citation_id,
    )

    if citation_row is None:
        raise ValueError(
            "Requested citation was not found."
        )

    if (
        str(citation_row["status"])
        != CITATION_STATUS_OPEN
    ):
        raise ValueError(
            "Only OPEN citations can be marked PAID."
        )

    _ensure_user_exists(
        connection=connection,
        user_id=clean_paid_by_user_id,
        error_message=(
            "Payment actor is not registered."
        ),
    )

    transaction_row = connection.execute(
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
        (
            clean_payment_transaction_id,
        ),
    ).fetchone()

    if transaction_row is None:
        raise ValueError(
            "Payment transaction was not found."
        )

    transaction_type = str(
        transaction_row["type"]
    )

    if transaction_type not in (
        CITATION_PAYMENT_TRANSACTION_TYPES
    ):
        raise ValueError(
            "Transaction is not a recognized fine "
            "payment or collection record."
        )

    if int(
        transaction_row["user_id"]
    ) != int(
        citation_row["user_id"]
    ):
        raise ValueError(
            "Payment transaction belongs to a "
            "different citizen."
        )

    if int(
        transaction_row["amount"]
    ) != -int(
        citation_row["amount"]
    ):
        raise ValueError(
            "Payment transaction amount does not "
            "match the full citation amount."
        )

    linked_citation = connection.execute(
        """
        SELECT citation_id
        FROM citations
        WHERE
            payment_transaction_id = ?
            AND citation_id != ?
        """,
        (
            clean_payment_transaction_id,
            citation_id,
        ),
    ).fetchone()

    if linked_citation is not None:
        raise ValueError(
            "Payment transaction is already linked "
            "to another citation."
        )

    updated_notes = (
        _merge_administrative_notes(
            existing_notes=(
                citation_row[
                    "administrative_notes"
                ]
            ),
            new_notes=administrative_notes,
        )
    )

    now = utc_now()

    cursor = connection.execute(
        """
        UPDATE citations
        SET
            status = ?,
            updated_at = ?,
            paid_at = ?,
            paid_by_user_id = ?,
            payment_transaction_id = ?,
            administrative_notes = ?
        WHERE
            citation_id = ?
            AND status = ?
        """,
        (
            CITATION_STATUS_PAID,
            now,
            now,
            clean_paid_by_user_id,
            clean_payment_transaction_id,
            updated_notes,
            citation_id,
            CITATION_STATUS_OPEN,
        ),
    )

    if cursor.rowcount != 1:
        raise RuntimeError(
            "Citation status changed before payment "
            "could be recorded."
        )

    updated_row = _get_citation_row(
        connection=connection,
        citation_id=citation_id,
    )

    if updated_row is None:
        raise RuntimeError(
            "Citation was paid but could not be "
            "retrieved."
        )

    return _citation_to_dict(
        updated_row
    )


def mark_citation_paid(
    *,
    citation_identifier: object,
    paid_by_user_id: int,
    payment_transaction_id: int,
    administrative_notes: str | None = None,
) -> dict:
    """
    Standalone wrapper for a pre-existing payment
    transaction.
    """
    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            citation = (
                mark_citation_paid_on_connection(
                    connection=connection,
                    citation_identifier=(
                        citation_identifier
                    ),
                    paid_by_user_id=(
                        paid_by_user_id
                    ),
                    payment_transaction_id=(
                        payment_transaction_id
                    ),
                    administrative_notes=(
                        administrative_notes
                    ),
                )
            )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Citation payment status could not be "
            "recorded. No partial citation change "
            "was retained."
        ) from error

    return citation

def pay_citation(
    *,
    user_id: int,
    citation_identifier: object,
) -> dict:
    """
    Pays one OPEN citation belonging to the citizen.

    Every required operation succeeds or fails together:

    - The citation is confirmed to belong to the user
    - The user's full balance is verified
    - The user's balance decreases exactly once
    - One FINE_PAYMENT transaction is created
    - The citation becomes PAID
    - The payment transaction is linked to the citation

    Fine payments are credit sinks. No user or
    organization receives the removed credits.
    """
    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="Paying user ID",
    )

    citation_id = parse_citation_identifier(
        citation_identifier
    )

    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            user_row = connection.execute(
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
                (clean_user_id,),
            ).fetchone()

            if user_row is None:
                raise ValueError(
                    "Paying user is not registered."
                )

            citation_row = _get_citation_row(
                connection=connection,
                citation_id=citation_id,
            )

            if citation_row is None:
                raise ValueError(
                    "Requested citation was not found."
                )

            if int(
                citation_row["user_id"]
            ) != clean_user_id:
                raise ValueError(
                    "You can only pay citations issued "
                    "to your own ENVI account."
                )

            if (
                str(citation_row["status"])
                != CITATION_STATUS_OPEN
            ):
                raise ValueError(
                    "Only OPEN citations can be paid."
                )

            citation_amount = int(
                citation_row["amount"]
            )

            balance_before = int(
                user_row["balance"]
            )

            if balance_before < citation_amount:
                raise ValueError(
                    "Insufficient Nexus Credits. "
                    f"This citation requires "
                    f"{citation_amount:,} credits, but "
                    f"the account contains only "
                    f"{balance_before:,}."
                )

            citation_public_id = (
                format_citation_identifier(
                    citation_id
                )
            )

            now = utc_now()

            balance_cursor = connection.execute(
                """
                UPDATE users
                SET
                    balance = balance - ?,
                    updated_at = ?
                WHERE
                    user_id = ?
                    AND balance >= ?
                """,
                (
                    citation_amount,
                    now,
                    clean_user_id,
                    citation_amount,
                ),
            )

            if balance_cursor.rowcount != 1:
                raise RuntimeError(
                    "Citizen balance changed before the "
                    "citation payment could complete."
                )

            transaction_reason = (
                "Paid Black Badge citation "
                f"{citation_public_id}. "
                "Credits removed from circulation."
            )

            transaction_cursor = connection.execute(
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
                    TRANSACTION_FINE_PAYMENT,
                    -citation_amount,
                    transaction_reason,
                    now,
                ),
            )

            payment_transaction_id = int(
                transaction_cursor.lastrowid
            )

            paid_citation = (
                mark_citation_paid_on_connection(
                    connection=connection,
                    citation_identifier=citation_id,
                    paid_by_user_id=clean_user_id,
                    payment_transaction_id=(
                        payment_transaction_id
                    ),
                )
            )

            updated_user_row = connection.execute(
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
                (clean_user_id,),
            ).fetchone()

            payment_transaction_row = (
                connection.execute(
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
                    (
                        payment_transaction_id,
                    ),
                ).fetchone()
            )

            if updated_user_row is None:
                raise RuntimeError(
                    "Citation payment completed, but the "
                    "updated citizen account could not "
                    "be retrieved."
                )

            if payment_transaction_row is None:
                raise RuntimeError(
                    "Citation payment completed, but the "
                    "payment transaction could not be "
                    "retrieved."
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Citation payment could not be processed. "
            "No balance, transaction, or citation "
            "change was retained."
        ) from error

    return {
        "citation": paid_citation,
        "user": dict(
            updated_user_row
        ),
        "amount": citation_amount,
        "balance_before": balance_before,
        "transaction": dict(
            payment_transaction_row
        ),
    }

def collect_citation(
    *,
    citation_identifier: object,
    collector_user_id: int,
    administrative_notes: str,
) -> dict:
    """
    Administratively collects one OPEN citation.

    Every required operation succeeds or fails together:

    - The citation must exist and remain OPEN
    - The collector must have a registered ENVI account
    - The citizen must possess the full citation amount
    - The citizen balance decreases exactly once
    - One FINE_COLLECTION transaction is created
    - The citation becomes PAID
    - The collector and payment transaction are linked

    Partial collection is not supported. Collection
    removes credits from circulation and cannot create
    a negative citizen balance.
    """
    citation_id = parse_citation_identifier(
        citation_identifier
    )

    clean_collector_user_id = (
        _validate_positive_id(
            value=collector_user_id,
            field_name="Collector user ID",
        )
    )

    clean_notes = _clean_required_text(
        value=administrative_notes,
        field_name="Collection reason",
        max_length=(
            CITATION_ADMIN_NOTES_MAX_LENGTH
        ),
    )

    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            citation_row = _get_citation_row(
                connection=connection,
                citation_id=citation_id,
            )

            if citation_row is None:
                raise ValueError(
                    "Requested citation was not found."
                )

            if (
                str(citation_row["status"])
                != CITATION_STATUS_OPEN
            ):
                raise ValueError(
                    "Only OPEN citations can be "
                    "collected."
                )

            _ensure_user_exists(
                connection=connection,
                user_id=clean_collector_user_id,
                error_message=(
                    "Citation collector is not "
                    "registered."
                ),
            )

            collector_row = connection.execute(
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
                (
                    clean_collector_user_id,
                ),
            ).fetchone()

            citizen_id = int(
                citation_row["user_id"]
            )

            citizen_row = connection.execute(
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
                (citizen_id,),
            ).fetchone()

            if collector_row is None:
                raise RuntimeError(
                    "The registered collector account "
                    "could not be retrieved."
                )

            if citizen_row is None:
                raise RuntimeError(
                    "The cited citizen account could "
                    "not be retrieved."
                )

            citation_amount = int(
                citation_row["amount"]
            )

            balance_before = int(
                citizen_row["balance"]
            )

            if balance_before < citation_amount:
                raise ValueError(
                    "Administrative collection requires "
                    "the full citation amount. "
                    f"The citation requires "
                    f"{citation_amount:,} credits, but "
                    f"the citizen has only "
                    f"{balance_before:,}."
                )

            citation_public_id = (
                format_citation_identifier(
                    citation_id
                )
            )

            now = utc_now()

            balance_cursor = connection.execute(
                """
                UPDATE users
                SET
                    balance = balance - ?,
                    updated_at = ?
                WHERE
                    user_id = ?
                    AND balance >= ?
                """,
                (
                    citation_amount,
                    now,
                    citizen_id,
                    citation_amount,
                ),
            )

            if balance_cursor.rowcount != 1:
                raise RuntimeError(
                    "Citizen balance changed before "
                    "administrative collection could "
                    "complete."
                )

            transaction_reason = (
                "Administratively collected Black Badge "
                f"citation {citation_public_id}. "
                "Collector user ID: "
                f"{clean_collector_user_id}. "
                "Credits removed from circulation."
            )

            transaction_cursor = connection.execute(
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
                    citizen_id,
                    TRANSACTION_FINE_COLLECTION,
                    -citation_amount,
                    transaction_reason,
                    now,
                ),
            )

            payment_transaction_id = int(
                transaction_cursor.lastrowid
            )

            paid_citation = (
                mark_citation_paid_on_connection(
                    connection=connection,
                    citation_identifier=citation_id,
                    paid_by_user_id=(
                        clean_collector_user_id
                    ),
                    payment_transaction_id=(
                        payment_transaction_id
                    ),
                    administrative_notes=(
                        clean_notes
                    ),
                )
            )

            updated_citizen_row = (
                connection.execute(
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
                    (citizen_id,),
                ).fetchone()
            )

            transaction_row = connection.execute(
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
                (
                    payment_transaction_id,
                ),
            ).fetchone()

            if updated_citizen_row is None:
                raise RuntimeError(
                    "Collection completed, but the "
                    "updated citizen account could not "
                    "be retrieved."
                )

            if transaction_row is None:
                raise RuntimeError(
                    "Collection completed, but the "
                    "collection transaction could not "
                    "be retrieved."
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Citation collection could not be "
            "processed. No balance, transaction, or "
            "citation change was retained."
        ) from error

    return {
        "citation": paid_citation,
        "user": dict(
            updated_citizen_row
        ),
        "collector": dict(
            collector_row
        ),
        "amount": citation_amount,
        "balance_before": balance_before,
        "transaction": dict(
            transaction_row
        ),
        "payment_method": (
            "ADMINISTRATIVE_COLLECTION"
        ),
    }

def void_citation(
    *,
    citation_identifier: object,
    voided_by_user_id: int,
    administrative_notes: str,
) -> dict:
    """
    Moves one OPEN citation to the terminal VOID state.
    """
    citation_id = parse_citation_identifier(
        citation_identifier
    )

    clean_voided_by_user_id = (
        _validate_positive_id(
            value=voided_by_user_id,
            field_name="Voiding user ID",
        )
    )

    clean_void_notes = _clean_required_text(
        value=administrative_notes,
        field_name="Void reason",
        max_length=(
            CITATION_ADMIN_NOTES_MAX_LENGTH
        ),
    )

    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            citation_row = _get_citation_row(
                connection=connection,
                citation_id=citation_id,
            )

            if citation_row is None:
                raise ValueError(
                    "Requested citation was not found."
                )

            if (
                str(citation_row["status"])
                != CITATION_STATUS_OPEN
            ):
                raise ValueError(
                    "Only OPEN citations can be VOID."
                )

            _ensure_user_exists(
                connection=connection,
                user_id=(
                    clean_voided_by_user_id
                ),
                error_message=(
                    "Voiding user is not registered."
                ),
            )

            updated_notes = (
                _merge_administrative_notes(
                    existing_notes=(
                        citation_row[
                            "administrative_notes"
                        ]
                    ),
                    new_notes=clean_void_notes,
                )
            )

            now = utc_now()

            cursor = connection.execute(
                """
                UPDATE citations
                SET
                    status = ?,
                    updated_at = ?,
                    voided_at = ?,
                    voided_by_user_id = ?,
                    administrative_notes = ?
                WHERE
                    citation_id = ?
                    AND status = ?
                """,
                (
                    CITATION_STATUS_VOID,
                    now,
                    now,
                    clean_voided_by_user_id,
                    updated_notes,
                    citation_id,
                    CITATION_STATUS_OPEN,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Citation status changed before "
                    "it could be voided."
                )

            updated_row = _get_citation_row(
                connection=connection,
                citation_id=citation_id,
            )

            if updated_row is None:
                raise RuntimeError(
                    "Citation was voided but could "
                    "not be retrieved."
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "Citation could not be voided. "
            "No partial citation change was retained."
        ) from error

    return _citation_to_dict(
        updated_row
    )