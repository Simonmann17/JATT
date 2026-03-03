from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, TypedDict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_PATH = Path(os.getenv("GMAIL_TOKEN_PATH", str(BASE_DIR / "token.json")))
CREDENTIALS_PATH = Path(
    os.getenv("GMAIL_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json"))
)


class GmailMessage(TypedDict):
    raw_email: str
    sender: str
    subject: str


def _get_credentials() -> Credentials:
    creds: Credentials | None = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail credentials file not found at: {CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds


def _build_service():
    creds = _get_credentials()
    return build("gmail", "v1", credentials=creds)


def fetch_workday_emails(
    limit: int = 5, lookback_days: int = 90, sender_filter: Optional[str] = None
) -> List[GmailMessage]:
    service = _build_service()
    sender_filter_value = (sender_filter or "").lower().strip()
    query_parts = [f"newer_than:{lookback_days}d"]
    if sender_filter_value:
        query_parts.insert(0, f"from:{sender_filter_value}")
    query = " ".join(query_parts)

    parsed_messages: List[GmailMessage] = []
    page_token: Optional[str] = None
    checked = 0
    max_checked = 300 if sender_filter_value else 1000
    page_size = 100

    while len(parsed_messages) < limit and checked < max_checked:
        list_call = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=page_size,
            pageToken=page_token,
        )
        results = list_call.execute()
        messages = results.get("messages", [])
        if not messages:
            break

        for msg in messages:
            if len(parsed_messages) >= limit or checked >= max_checked:
                break
            checked += 1

            msg_detail = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )

            payload = msg_detail.get("payload", {})
            headers = payload.get("headers", [])
            sender = _extract_sender_from_headers(headers)
            if not sender:
                continue
            if sender_filter_value and sender_filter_value not in sender:
                continue
            subject = _extract_subject_from_headers(headers)

            body = _extract_body_text(payload) or msg_detail.get("snippet", "")
            parsed_messages.append(
                {
                    "raw_email": body,
                    "sender": sender,
                    "subject": subject,
                }
            )

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return parsed_messages

# Helper functions for parsing Gmail message details
def _is_workday_sender(sender: str) -> bool:
    sender = sender.lower()
    return sender.endswith(".myworkday.com") or sender.endswith("@myworkday.com")

def _extract_sender_from_headers(headers: list[dict]) -> str:
    from_header = ""
    for header in headers:
        if header.get("name", "").lower() == "from":
            from_header = header.get("value", "").strip()
            break

    if not from_header:
        return ""

    email_match = re.search(r"([A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})", from_header,)
    if not email_match:
        return ""

    return email_match.group(1).lower()

def _extract_subject_from_headers(headers: list[dict]) -> str:
    for header in headers:
        if header.get("name", "").lower() == "subject":
            return header.get("value", "").strip()
    return ""

def _extract_body_text(payload: dict) -> str:
    """Extract plain text from a Gmail message payload."""
    import base64

    def decode(data: str) -> str:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")

    if payload.get("body", {}).get("data"):
        return decode(payload["body"]["data"])

    def walk(parts: list[dict]) -> str:
        html_fallback = ""
        for part in parts:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {}).get("data")

            if mime_type == "text/plain" and body:
                return decode(body)
            if mime_type == "text/html" and body and not html_fallback:
                html_fallback = decode(body)

            # Nested parts
            if "parts" in part:
                result = walk(part["parts"])
                if result:
                    return result

        return html_fallback

    return walk(payload.get("parts", []))
