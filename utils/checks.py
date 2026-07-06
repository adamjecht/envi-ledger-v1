import os

import discord
from dotenv import load_dotenv


load_dotenv()


def get_admin_role_id() -> int:
    """
    Gets the admin role ID from the .env file.
    """
    admin_role_id = os.getenv("ADMIN_ROLE_ID")

    if not admin_role_id:
        raise RuntimeError("ADMIN_ROLE_ID is missing from your .env file.")

    try:
        return int(admin_role_id)
    except ValueError as error:
        raise RuntimeError("ADMIN_ROLE_ID must be a number with no quotes or spaces.") from error


def user_has_admin_role(member: discord.Member) -> bool:
    """
    Checks whether a Discord member has the ENVI Ledger Admin role.
    """
    admin_role_id = get_admin_role_id()

    return any(role.id == admin_role_id for role in member.roles)