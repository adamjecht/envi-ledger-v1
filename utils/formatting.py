from utils.constants import CURRENCY_SYMBOL


def format_credits(amount: int) -> str:
    """
    Formats a credit amount with the Nexus Credits symbol.

    Example:
    2500 -> ₦C 2,500
    """
    return f"{CURRENCY_SYMBOL} {amount:,}"


def format_seconds(seconds: int) -> str:
    """
    Turns seconds into a readable time string.

    Example:
    3660 -> 1h 1m
    """
    if seconds <= 0:
        return "now"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    parts = []

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if remaining_seconds and not hours:
        parts.append(f"{remaining_seconds}s")

    return " ".join(parts)