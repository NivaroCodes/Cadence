import asyncio
import base64
import logging
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Deferred imports — these are only resolved when credentials exist
# so the server starts cleanly without Google auth libraries erroring.
_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _load_credentials():
    """Return valid OAuth2 credentials, refreshing if expired."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path = Path(settings.GMAIL_CREDENTIALS_PATH)
    token_path = creds_path.parent / "token.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), _GMAIL_SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), _GMAIL_SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json())
    return creds


def _build_gmail_client():
    from googleapiclient.discovery import build as google_build
    creds = _load_credentials()
    return google_build("gmail", "v1", credentials=creds)


def _encode_message(to: str, subject: str, body: str) -> dict:
    mime = MIMEText(body, "plain", "utf-8")
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    return {"raw": raw}


def _sync_send(to: str, subject: str, body: str) -> bool:
    service = _build_gmail_client()
    message = _encode_message(to, subject, body)
    sent = service.users().messages().send(userId="me", body=message).execute()
    logger.info("Email sent to %s | message_id=%s", to, sent.get("id"))
    return True


def _sync_check_inbox(search_query: str) -> list[dict]:
    service = _build_gmail_client()
    result = service.users().messages().list(userId="me", q=search_query).execute()
    messages = result.get("messages", [])

    parsed: list[dict] = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        parsed.append(
            {
                "message_id": msg["id"],
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "timestamp": headers.get("Date", ""),
            }
        )

    return parsed


class GmailService:
    def __init__(self) -> None:
        self._available = self._check_credentials()

    def _check_credentials(self) -> bool:
        creds_path = Path(settings.GMAIL_CREDENTIALS_PATH)
        if not creds_path.exists():
            logger.warning(
                "Gmail credentials not found at %s — GmailService running in degraded mode",
                settings.GMAIL_CREDENTIALS_PATH,
            )
            return False
        return True

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        if not self._available:
            logger.warning("send_email skipped — Gmail credentials missing")
            if settings.APP_ENV == "dev":
                logger.info("Dev environment: Mocking successful email send to %s", to)
                return True
            return False
        try:
            return await asyncio.to_thread(_sync_send, to, subject, body)
        except Exception:
            logger.exception("Failed to send email to %s", to)
            return False

    async def check_inbox(self, search_query: str) -> list[dict]:
        if not self._available:
            logger.warning("check_inbox skipped — Gmail credentials missing")
            return []
        try:
            return await asyncio.to_thread(_sync_check_inbox, search_query)
        except Exception:
            logger.exception("Failed to check inbox with query: %s", search_query)
            return []
