from datetime import datetime
from typing import Optional, TypedDict


class EmailMessage(TypedDict):
    provider_id: str
    sender: str
    subject: str
    raw_email: str
    received_at: Optional[datetime]
