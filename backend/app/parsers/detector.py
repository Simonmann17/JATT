from typing import Optional

from ..email import EmailMessage
from ..vendors import is_workday_sender


def detect_vendor(email: EmailMessage) -> Optional[str]:
    if is_workday_sender(email["sender"]):
        return "workday"
    return None
