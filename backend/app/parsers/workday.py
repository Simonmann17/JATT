import html
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:
    from ..models import ApplicationCreate
except ModuleNotFoundError:
    @dataclass
    class ApplicationCreate:
        vendor: str
        subject: str
        job_title: Optional[str] = None
        company: Optional[str] = None
        location: Optional[str] = None
        status: Optional[str] = None
        requisition_id: Optional[str] = None
        applied_at: Optional[datetime] = None
        raw_email: str = ""


STATUS_ALIASES: dict[str, str] = {
    "application received": "applied",
    "application submitted": "applied",
    "received": "applied",
    "under review": "under_review",
    "in review": "under_review",
    "review": "under_review",
    "interview": "interview",
    "not selected": "rejected",
    "no longer under consideration": "rejected",
    "rejected": "rejected",
    "offer": "offer",
    "withdrawn": "withdrawn",
}

DATE_FORMATS: tuple[str, ...] = (
    "%B %d, %Y",    # February 19, 2026
    "%b %d, %Y",    # Feb 19, 2026
    "%m/%d/%Y",     # 02/19/2026
    "%Y-%m-%d",     # 2026-02-19
)


def _extract_sender_email(raw_email: str) -> Optional[str]:
    from_line_match = re.search(
        r"^From:\s*(.+)$",
        raw_email,
        re.IGNORECASE | re.MULTILINE,
    )
    if not from_line_match:
        return None

    from_header = from_line_match.group(1).strip()
    email_match = re.search(
        r"([A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})",
        from_header,
    )

    return email_match.group(1).lower() if email_match else None


def _is_myworkday_sender(sender_email: str) -> bool:
    sender_email = sender_email.lower()
    return sender_email.endswith(".myworkday.com") or sender_email.endswith("@myworkday.com")


def _clean_email_text(raw_email: str) -> str:
    """Convert HTML-ish email bodies into readable text for regex extraction."""
    text = raw_email
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h\d)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _search_any(patterns: tuple[str, ...], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip(" .:-")
    return None


def _extract_applied_at(text: str) -> Optional[datetime]:
    date_text = _search_any(
        (
            r"(?:Applied|Submitted|Application Date)\s*(?:on|:)\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
            r"(?:Applied|Submitted|Application Date)\s*(?:on|:)\s*(\d{1,2}/\d{1,2}/\d{4})",
            r"(?:Applied|Submitted|Application Date)\s*(?:on|:)\s*(\d{4}-\d{2}-\d{2})",
        ),
        text,
    )
    if not date_text:
        return None

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(date_text, date_format)
        except ValueError:
            continue
    return None


def _normalize_status(raw_status: Optional[str], text: str) -> Optional[str]:
    source = (raw_status or "").lower().strip()
    if source:
        for key, normalized in STATUS_ALIASES.items():
            if key in source:
                return normalized
    lower_text = text.lower()
    for key, normalized in STATUS_ALIASES.items():
        if key in lower_text:
            return normalized
    return raw_status


def parse_workday_email(raw_email: str, sender_email: Optional[str] = None, subject: Optional[str] = None) -> ApplicationCreate:
    """
    Very first-pass parser for Workday job application emails.

    This assumes the email body contains lines like:
      - Job Title: Senior Software Engineer
      - Company: Acme Corp
      - Location: Remote, US
      - Requisition ID: R-12345
      - Status: Application Received
    """
    sender = (sender_email or _extract_sender_email(raw_email) or "").strip().lower()
    if not sender:
        raise ValueError("Missing sender email for Workday validation")
    if not _is_myworkday_sender(sender):
        raise ValueError(f"Invalid sender domain for Workday parser: {sender}")

    clean_body = _clean_email_text(raw_email)
    text = clean_body
    if subject:
        text = f"Subject: {subject}\n{clean_body}"

    job_title = _search_any(
        (
            r"Job Title:\s*(.+)",
            r"Position(?: Applied For)?:\s*(.+)",
            r"Requisition Title:\s*(.+)",
            r"for the\s+(.+?)\s+position",
        ),
        text,
    )
    company = _search_any(
        (
            r"Company:\s*(.+)",
            r"Thank you for applying to\s+(.+)",
            r"at\s+([A-Z][A-Za-z0-9&.,' -]+)",
        ),
        text,
    )
    location = _search_any(
        (
            r"Location:\s*(.+)",
            r"Work Location:\s*(.+)",
        ),
        text,
    )
    requisition_id = _search_any(
        (
            r"(?:Requisition ID|Job Req(?:uisition)?|Req ID):\s*([A-Za-z0-9-]+)",
            r"Req(?:uisition)?\s*#\s*([A-Za-z0-9-]+)",
        ),
        text,
    )
    raw_status = _search_any(
        (
            r"Status:\s*(.+)",
            r"(?:Your application status is|Current Status):\s*(.+)",
            r"Application Status:\s*(.+)",
        ),
        text,
    )
    status = _normalize_status(raw_status, text)
    applied_at = _extract_applied_at(text) or datetime.utcnow()

    # De-noise occasional trailing boilerplate.
    if company:
        company = re.split(r"\s+(?:through|via|using)\s+Workday", company, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    if job_title:
        job_title = re.split(r"\s{2,}", job_title, maxsplit=1)[0].strip()

    return ApplicationCreate(
        vendor="workday",
        subject=subject or "",
        job_title=job_title,
        company=company,
        location=location,
        status=status,
        requisition_id=requisition_id,
        applied_at=applied_at,
        raw_email=raw_email,
    )
