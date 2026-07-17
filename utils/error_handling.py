from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

import discord
from discord import app_commands


ERROR_TEXT_LIMIT = 1000


@dataclass(
    frozen=True,
    slots=True,
)
class CommandErrorPresentation:
    """
    Safe public and staff-facing information for one
    unexpected application-command failure.

    Raw exception text is deliberately excluded. Complete
    exception details remain available only in the
    application console traceback.
    """

    incident_id: str
    category: str
    error_type: str
    title: str
    public_reason: str
    log_description: str


def _shorten_text(
    value: object,
    limit: int = ERROR_TEXT_LIMIT,
) -> str:
    """
    Converts a value into bounded display text.
    """
    text = str(value).strip()

    if not text:
        return "Not available"

    if len(text) <= limit:
        return text

    return (
        text[: limit - 3]
        + "..."
    )


def create_incident_id() -> str:
    """
    Creates a short reference that users and staff can
    use to correlate a public failure with its staff log.
    """
    date_text = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d"
    )

    random_text = secrets.token_hex(
        3
    ).upper()

    return (
        f"ENVI-{date_text}-{random_text}"
    )


def _classify_error(
    error: app_commands.AppCommandError,
) -> tuple[str, str, str]:
    """
    Returns:
        category,
        public title,
        public guidance

    No raw exception message is returned.
    """
    original_error = getattr(
        error,
        "original",
        error,
    )

    if isinstance(
        error,
        app_commands.errors.CommandOnCooldown,
    ):
        retry_after = max(
            1,
            round(error.retry_after),
        )

        return (
            "COOLDOWN",
            "ENVI COMMAND COOLING DOWN",
            (
                "This command is temporarily cooling down. "
                f"Try again in approximately {retry_after} "
                "second(s)."
            ),
        )

    if isinstance(
        error,
        (
            app_commands.errors.MissingPermissions,
            app_commands.errors.BotMissingPermissions,
            app_commands.errors.CheckFailure,
        ),
    ):
        return (
            "PERMISSION",
            "ENVI ACCESS DENIED",
            (
                "The required Discord or ENVI permission "
                "was not detected. Confirm your role and "
                "the bot's channel permissions before "
                "trying again."
            ),
        )

    if isinstance(
        error,
        (
            app_commands.errors.TransformerError,
            app_commands.errors.CommandSignatureMismatch,
        ),
    ):
        return (
            "INPUT",
            "ENVI COMMAND INPUT DENIED",
            (
                "Discord could not process one or more "
                "command options. Review the selected "
                "members, organizations, items, amounts, "
                "and confirmation values, then try again."
            ),
        )

    if isinstance(
        original_error,
        sqlite3.Error,
    ):
        return (
            "DATABASE",
            "ENVI LEDGER OPERATION FAILED",
            (
                "The ledger database could not complete "
                "this request safely. No partial result "
                "should be assumed. Try once more; if the "
                "failure repeats, give staff the incident "
                "reference below."
            ),
        )

    if isinstance(
        original_error,
        discord.Forbidden,
    ):
        return (
            "DISCORD_PERMISSION",
            "ENVI DISCORD ACCESS FAILED",
            (
                "Discord prevented ENVI from completing "
                "the response. Staff should verify the "
                "bot's channel and message permissions."
            ),
        )

    if isinstance(
        original_error,
        discord.HTTPException,
    ):
        return (
            "DISCORD_RESPONSE",
            "ENVI RESPONSE FAILED",
            (
                "Discord rejected or interrupted the "
                "response. Retry the command once. If it "
                "fails again, give staff the incident "
                "reference below."
            ),
        )

    if isinstance(
        original_error,
        ValueError,
    ):
        return (
            "VALIDATION",
            "ENVI REQUEST DENIED",
            (
                "The request contained a value that could "
                "not be accepted. Review the command "
                "options and try again."
            ),
        )

    if isinstance(
        original_error,
        RuntimeError,
    ):
        return (
            "SAFE_ROLLBACK",
            "ENVI OPERATION INCOMPLETE",
            (
                "ENVI could not complete the operation "
                "safely. No partial financial result "
                "should be assumed. Give staff the "
                "incident reference below if the problem "
                "continues."
            ),
        )

    return (
        "UNEXPECTED",
        "ENVI COMMAND FAILURE",
        (
            "An unexpected system fault interrupted the "
            "command. Try once more. If it fails again, "
            "give staff the incident reference below."
        ),
    )


def build_command_error_presentation(
    *,
    error: app_commands.AppCommandError,
    command_name: str,
    user_text: str,
) -> CommandErrorPresentation:
    """
    Builds safe public guidance and a safe Discord staff
    log without exposing raw database or exception text.
    """
    original_error = getattr(
        error,
        "original",
        error,
    )

    incident_id = create_incident_id()

    (
        category,
        title,
        guidance,
    ) = _classify_error(
        error
    )

    error_type = type(
        original_error
    ).__name__

    safe_command_name = _shorten_text(
        command_name,
        200,
    )

    safe_user_text = _shorten_text(
        user_text,
        300,
    )

    public_reason = (
        f"{guidance}\n\n"
        "Incident Reference: "
        f"`{incident_id}`"
    )

    log_description = (
        f"Incident: `{incident_id}`\n"
        f"Command: `{safe_command_name}`\n"
        f"User: `{safe_user_text}`\n"
        f"Category: `{category}`\n"
        f"Error Type: `{error_type}`\n\n"
        "**Public Guidance Sent**\n"
        f"{guidance}\n\n"
        "_Raw exception text and traceback were retained "
        "only in the application console._"
    )

    return CommandErrorPresentation(
        incident_id=incident_id,
        category=category,
        error_type=error_type,
        title=title,
        public_reason=public_reason,
        log_description=log_description,
    )