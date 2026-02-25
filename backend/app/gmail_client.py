from __future__ import annotations

import os
from pathlib import Path
from typing import List

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


def fetch_workday_emails(limit: int = 5, lookback_days: int = 90) -> List[str]:
    """
    Fetch raw text bodies of recent Workday-related messages from Gmail.

    This uses a simple Gmail search query; you can refine it later.
    """
    service = _build_service()
    query = (
        'from:(workday.com) OR subject:(Workday) OR "Thank you for applying" '
        f"newer_than:{lookback_days}d"
    )
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=limit)
        .execute()
    )

    messages = results.get("messages", [])
    bodies: List[str] = []

    for msg in messages:
        msg_detail = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="full")
            .execute()
        )
        payload = msg_detail.get("payload", {})
        body = _extract_body_text(payload)
        if body:
            bodies.append(body)

    return bodies


def _extract_body_text(payload: dict) -> str:
    """Extract plain text from a Gmail message payload."""
    import base64

    def decode(data: str) -> str:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")

    if "body" in payload and payload["body"].get("data"):
        return decode(payload["body"]["data"])

    parts = payload.get("parts", [])
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain" and part.get("body", {}).get("data"):
            return decode(part["body"]["data"])

    # Fallback: first part with data
    for part in parts:
        if part.get("body", {}).get("data"):
            return decode(part["body"]["data"])

    return ""
