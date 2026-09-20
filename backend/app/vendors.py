import re


def is_workday_sender(sender: str) -> bool:
    """Return whether an email address belongs to a Workday notification domain."""
    normalized = sender.strip().lower()
    return bool(
        re.fullmatch(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)*myworkday\.com", normalized)
    )
