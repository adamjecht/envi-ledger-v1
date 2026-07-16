from __future__ import annotations

import sqlite3

from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    ORGANIZATION_PERMISSION_DEPOSIT,
    ORGANIZATION_PERMISSION_MANAGE_MEMBERS,
    ORGANIZATION_PERMISSION_MANAGE_ROLES,
    ORGANIZATION_PERMISSION_PAY_ORGANIZATION,
    ORGANIZATION_PERMISSION_PAY_USER,
    ORGANIZATION_PERMISSION_REMOVE_MEMBERS,
    ORGANIZATION_PERMISSION_VIEW_BALANCE,
    ORGANIZATION_PERMISSION_VIEW_LEDGER,
    ORGANIZATION_PERMISSION_VIEW_MEMBERS,
    ORGANIZATION_PERMISSIONS,
    ORGANIZATION_ROLE_OWNER,
    ORGANIZATION_ROLE_PERMISSIONS,
    ORGANIZATION_ROLES,
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


def _validate_boolean(
    value: object,
    field_name: str,
) -> bool:
    """
    Validates a strict Boolean setting.
    """

    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be True or False."
        )

    return value


def _normalize_role(
    role: object,
) -> str:
    """
    Normalizes and validates an organization role.
    """

    if not isinstance(role, str):
        raise ValueError(
            "Organization role must be text."
        )

    clean_role = role.strip().upper()

    if clean_role not in ORGANIZATION_ROLES:
        allowed_roles = ", ".join(
            ORGANIZATION_ROLES
        )

        raise ValueError(
            "Invalid organization role. "
            f"Allowed roles: {allowed_roles}."
        )

    return clean_role


def _normalize_permission(
    permission: object,
) -> str:
    """
    Normalizes and validates an organization permission.
    """

    if not isinstance(permission, str):
        raise ValueError(
            "Organization permission must be text."
        )

    clean_permission = permission.strip().upper()

    if clean_permission not in ORGANIZATION_PERMISSIONS:
        allowed_permissions = ", ".join(
            ORGANIZATION_PERMISSIONS
        )

        raise ValueError(
            "Invalid organization permission. "
            f"Allowed permissions: {allowed_permissions}."
        )

    return clean_permission


def _get_organization_row(
    connection: sqlite3.Connection,
    organization_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves a basic organization record.
    """

    return connection.execute(
        """
        SELECT
            organization_id,
            name,
            organization_type,
            balance,
            active,
            created_at,
            updated_at
        FROM organizations
        WHERE organization_id = ?
        """,
        (organization_id,),
    ).fetchone()


def _get_user_row(
    connection: sqlite3.Connection,
    user_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves a registered ENVI user.
    """

    return connection.execute(
        """
        SELECT
            user_id,
            display_name
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()


def _get_membership_row(
    connection: sqlite3.Connection,
    organization_id: int,
    user_id: int,
) -> sqlite3.Row | None:
    """
    Retrieves an active or inactive membership record.
    """

    return connection.execute(
        """
        SELECT
            membership.organization_id,
            organization.name AS organization_name,
            organization.organization_type,
            organization.active AS organization_active,
            membership.user_id,
            user.display_name,
            membership.role,
            membership.active AS membership_active,
            membership.joined_at,
            membership.updated_at,
            membership.removed_at
        FROM organization_members AS membership
        INNER JOIN organizations AS organization
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


def _count_active_owners(
    connection: sqlite3.Connection,
    organization_id: int,
) -> int:
    """
    Counts active owners inside one organization.
    """

    row = connection.execute(
        """
        SELECT COUNT(*) AS owner_count
        FROM organization_members
        WHERE
            organization_id = ?
            AND role = ?
            AND active = 1
        """,
        (
            organization_id,
            ORGANIZATION_ROLE_OWNER,
        ),
    ).fetchone()

    return int(row["owner_count"])


def _ensure_organization_exists(
    connection: sqlite3.Connection,
    organization_id: int,
) -> sqlite3.Row:
    """
    Retrieves an organization or raises a clear error.
    """

    organization = _get_organization_row(
        connection=connection,
        organization_id=organization_id,
    )

    if organization is None:
        raise ValueError(
            "Requested organization is not registered."
        )

    return organization


def _ensure_user_exists(
    connection: sqlite3.Connection,
    user_id: int,
) -> sqlite3.Row:
    """
    Retrieves an ENVI user or raises a clear error.
    """

    user = _get_user_row(
        connection=connection,
        user_id=user_id,
    )

    if user is None:
        raise ValueError(
            "Requested user is not registered."
        )

    return user


def get_role_permissions(
    role: str,
) -> frozenset[str]:
    """
    Returns the fixed permission set assigned to a role.
    """

    clean_role = _normalize_role(role)

    return ORGANIZATION_ROLE_PERMISSIONS[
        clean_role
    ]


def role_has_permission(
    role: str,
    permission: str,
) -> bool:
    """
    Checks whether a role contains one permission.
    """

    clean_role = _normalize_role(role)
    clean_permission = _normalize_permission(
        permission
    )

    return (
        clean_permission
        in ORGANIZATION_ROLE_PERMISSIONS[
            clean_role
        ]
    )


def add_organization_member(
    *,
    organization_id: int,
    user_id: int,
    role: str,
) -> dict:
    """
    Adds a new organization member.

    If an inactive historical membership already exists, the same
    row is reactivated instead of creating a duplicate record.

    Returns:
    - membership
    - reactivated
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    clean_role = _normalize_role(role)
    now = utc_now()

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        _ensure_organization_exists(
            connection=connection,
            organization_id=clean_organization_id,
        )

        _ensure_user_exists(
            connection=connection,
            user_id=clean_user_id,
        )

        existing_membership = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

        reactivated = False

        if existing_membership is not None:
            if (
                int(
                    existing_membership[
                        "membership_active"
                    ]
                )
                == 1
            ):
                raise ValueError(
                    "User is already an active member "
                    "of this organization."
                )

            connection.execute(
                """
                UPDATE organization_members
                SET
                    role = ?,
                    active = 1,
                    updated_at = ?,
                    removed_at = NULL
                WHERE
                    organization_id = ?
                    AND user_id = ?
                """,
                (
                    clean_role,
                    now,
                    clean_organization_id,
                    clean_user_id,
                ),
            )

            reactivated = True

        else:
            connection.execute(
                """
                INSERT INTO organization_members (
                    organization_id,
                    user_id,
                    role,
                    active,
                    joined_at,
                    updated_at,
                    removed_at
                )
                VALUES (?, ?, ?, 1, ?, ?, NULL)
                """,
                (
                    clean_organization_id,
                    clean_user_id,
                    clean_role,
                    now,
                    now,
                ),
            )

        membership_row = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

        connection.commit()

    if membership_row is None:
        raise RuntimeError(
            "Organization membership was saved but "
            "could not be retrieved."
        )

    return {
        "membership": dict(membership_row),
        "reactivated": reactivated,
    }


def get_organization_membership(
    *,
    organization_id: int,
    user_id: int,
    active_only: bool = True,
) -> dict | None:
    """
    Retrieves one organization membership.

    Active-only retrieval is the safe default for permissions.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    clean_active_only = _validate_boolean(
        value=active_only,
        field_name="active_only",
    )

    with get_connection() as connection:
        organization = _get_organization_row(
            connection=connection,
            organization_id=clean_organization_id,
        )

        if organization is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        membership = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

    if membership is None:
        return None

    if (
        clean_active_only
        and int(
            membership["membership_active"]
        )
        != 1
    ):
        return None

    return dict(membership)


def get_organization_members(
    organization_id: int,
    *,
    active_only: bool = True,
) -> list[dict]:
    """
    Returns organization members with owners listed first.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_active_only = _validate_boolean(
        value=active_only,
        field_name="active_only",
    )

    active_condition = ""

    if clean_active_only:
        active_condition = (
            "AND membership.active = 1"
        )

    with get_connection() as connection:
        _ensure_organization_exists(
            connection=connection,
            organization_id=clean_organization_id,
        )

        rows = connection.execute(
            f"""
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
                {active_condition}
            ORDER BY
                CASE membership.role
                    WHEN 'OWNER' THEN 1
                    WHEN 'MANAGER' THEN 2
                    WHEN 'MEMBER' THEN 3
                    ELSE 4
                END,
                membership.active DESC,
                user.display_name
                    COLLATE NOCASE ASC
            """,
            (clean_organization_id,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_user_organization_memberships(
    user_id: int,
    *,
    active_only: bool = True,
    organization_active_only: bool = True,
) -> list[dict]:
    """
    Returns the organizations associated with one user.
    """

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    clean_active_only = _validate_boolean(
        value=active_only,
        field_name="active_only",
    )

    clean_organization_active_only = (
        _validate_boolean(
            value=organization_active_only,
            field_name=(
                "organization_active_only"
            ),
        )
    )

    conditions = [
        "membership.user_id = ?",
    ]

    if clean_active_only:
        conditions.append(
            "membership.active = 1"
        )

    if clean_organization_active_only:
        conditions.append(
            "organization.active = 1"
        )

    where_clause = " AND ".join(conditions)

    with get_connection() as connection:
        user = _get_user_row(
            connection=connection,
            user_id=clean_user_id,
        )

        if user is None:
            raise ValueError(
                "Requested user is not registered."
            )

        rows = connection.execute(
            f"""
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
            WHERE {where_clause}
            ORDER BY
                organization.name
                    COLLATE NOCASE ASC
            """,
            (clean_user_id,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def count_active_organization_owners(
    organization_id: int,
) -> int:
    """
    Returns the number of active organization owners.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    with get_connection() as connection:
        _ensure_organization_exists(
            connection=connection,
            organization_id=clean_organization_id,
        )

        return _count_active_owners(
            connection=connection,
            organization_id=clean_organization_id,
        )


def set_organization_member_role(
    *,
    organization_id: int,
    user_id: int,
    role: str,
) -> dict:
    """
    Changes the role of an active organization member.

    The final active owner cannot be demoted.

    Returns:
    - before
    - after
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    clean_role = _normalize_role(role)

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        _ensure_organization_exists(
            connection=connection,
            organization_id=clean_organization_id,
        )

        current_row = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

        if current_row is None:
            raise ValueError(
                "User is not a member of this organization."
            )

        if (
            int(current_row["membership_active"])
            != 1
        ):
            raise ValueError(
                "Inactive organization memberships "
                "cannot change roles."
            )

        before = dict(current_row)

        if before["role"] == clean_role:
            raise ValueError(
                "Member already has the requested role."
            )

        if (
            before["role"]
            == ORGANIZATION_ROLE_OWNER
            and clean_role
            != ORGANIZATION_ROLE_OWNER
            and _count_active_owners(
                connection=connection,
                organization_id=(
                    clean_organization_id
                ),
            )
            <= 1
        ):
            raise ValueError(
                "The final active owner cannot be "
                "removed or demoted."
            )

        connection.execute(
            """
            UPDATE organization_members
            SET
                role = ?,
                updated_at = ?
            WHERE
                organization_id = ?
                AND user_id = ?
            """,
            (
                clean_role,
                utc_now(),
                clean_organization_id,
                clean_user_id,
            ),
        )

        updated_row = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

        connection.commit()

    if updated_row is None:
        raise RuntimeError(
            "Organization role was updated but "
            "could not be retrieved."
        )

    return {
        "before": before,
        "after": dict(updated_row),
    }


def remove_organization_member(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Soft-removes an active organization member.

    The membership row remains available for historical inspection.
    The final active owner cannot be removed.

    Returns:
    - before
    - after
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        _ensure_organization_exists(
            connection=connection,
            organization_id=clean_organization_id,
        )

        current_row = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

        if current_row is None:
            raise ValueError(
                "User is not a member of this organization."
            )

        if (
            int(current_row["membership_active"])
            != 1
        ):
            raise ValueError(
                "Organization membership is already inactive."
            )

        before = dict(current_row)

        if (
            before["role"]
            == ORGANIZATION_ROLE_OWNER
            and _count_active_owners(
                connection=connection,
                organization_id=(
                    clean_organization_id
                ),
            )
            <= 1
        ):
            raise ValueError(
                "The final active owner cannot be "
                "removed or demoted."
            )

        removal_time = utc_now()

        connection.execute(
            """
            UPDATE organization_members
            SET
                active = 0,
                updated_at = ?,
                removed_at = ?
            WHERE
                organization_id = ?
                AND user_id = ?
            """,
            (
                removal_time,
                removal_time,
                clean_organization_id,
                clean_user_id,
            ),
        )

        updated_row = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

        connection.commit()

    if updated_row is None:
        raise RuntimeError(
            "Organization member was removed but "
            "the historical record could not be retrieved."
        )

    return {
        "before": before,
        "after": dict(updated_row),
    }


def get_user_organization_permissions(
    *,
    organization_id: int,
    user_id: int,
    require_active_organization: bool = True,
) -> frozenset[str]:
    """
    Returns the user's effective organization permissions.

    Users outside the organization, inactive memberships, and users
    in inactive organizations receive no operational permissions.
    """

    clean_require_active = _validate_boolean(
        value=require_active_organization,
        field_name="require_active_organization",
    )

    membership = get_organization_membership(
        organization_id=organization_id,
        user_id=user_id,
        active_only=True,
    )

    if membership is None:
        return frozenset()

    if (
        clean_require_active
        and int(
            membership["organization_active"]
        )
        != 1
    ):
        return frozenset()

    return get_role_permissions(
        membership["role"]
    )


def user_has_organization_permission(
    *,
    organization_id: int,
    user_id: int,
    permission: str,
    require_active_organization: bool = True,
) -> bool:
    """
    Checks one effective organization permission.
    """

    clean_permission = _normalize_permission(
        permission
    )

    permissions = (
        get_user_organization_permissions(
            organization_id=organization_id,
            user_id=user_id,
            require_active_organization=(
                require_active_organization
            ),
        )
    )

    return clean_permission in permissions


def require_organization_permission(
    *,
    organization_id: int,
    user_id: int,
    permission: str,
    require_active_organization: bool = True,
) -> dict:
    """
    Requires active membership and one role permission.

    Returns the membership when access is approved.
    """

    clean_organization_id = _validate_positive_id(
        value=organization_id,
        field_name="Organization ID",
    )

    clean_user_id = _validate_positive_id(
        value=user_id,
        field_name="User ID",
    )

    clean_permission = _normalize_permission(
        permission
    )

    clean_require_active = _validate_boolean(
        value=require_active_organization,
        field_name="require_active_organization",
    )

    with get_connection() as connection:
        organization = _get_organization_row(
            connection=connection,
            organization_id=clean_organization_id,
        )

        if organization is None:
            raise ValueError(
                "Requested organization is not registered."
            )

        if (
            clean_require_active
            and int(organization["active"]) != 1
        ):
            raise ValueError(
                "Inactive organizations cannot perform "
                "this action."
            )

        membership = _get_membership_row(
            connection=connection,
            organization_id=clean_organization_id,
            user_id=clean_user_id,
        )

    if (
        membership is None
        or int(
            membership["membership_active"]
        )
        != 1
    ):
        raise ValueError(
            "You are not an active member of "
            "this organization."
        )

    if not role_has_permission(
        role=membership["role"],
        permission=clean_permission,
    ):
        raise ValueError(
            "Your organization role does not "
            "permit this action."
        )

    return dict(membership)

def require_organization_members_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires permission to inspect the active member roster.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=(
            ORGANIZATION_PERMISSION_VIEW_MEMBERS
        ),
    )


def require_organization_balance_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires permission to inspect an organization balance.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=(
            ORGANIZATION_PERMISSION_VIEW_BALANCE
        ),
    )


def require_organization_deposit_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires permission to deposit organization funds.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=ORGANIZATION_PERMISSION_DEPOSIT,
    )


def require_organization_user_payment_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires permission to pay a user from an organization.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=ORGANIZATION_PERMISSION_PAY_USER,
    )


def require_organization_payment_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires permission to pay another organization.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=(
            ORGANIZATION_PERMISSION_PAY_ORGANIZATION
        ),
    )


def require_organization_ledger_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires permission to inspect the private ledger.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=ORGANIZATION_PERMISSION_VIEW_LEDGER,
    )


def require_organization_member_management_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires owner-level member-management permission.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=(
            ORGANIZATION_PERMISSION_MANAGE_MEMBERS
        ),
    )


def require_organization_role_management_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires owner-level role-management permission.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=(
            ORGANIZATION_PERMISSION_MANAGE_ROLES
        ),
    )


def require_organization_member_removal_access(
    *,
    organization_id: int,
    user_id: int,
) -> dict:
    """
    Requires owner-level member-removal permission.
    """

    return require_organization_permission(
        organization_id=organization_id,
        user_id=user_id,
        permission=(
            ORGANIZATION_PERMISSION_REMOVE_MEMBERS
        ),
    )