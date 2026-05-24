import asyncio
import logging
import os
import pickle
from datetime import datetime

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
]


class GmailService:
    def __init__(self) -> None:
        self.credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", "./credentials.json")
        self.sender_email = os.getenv("SENDER_EMAIL", "me")
        self._available = os.path.exists(self.credentials_path)

    def _load_credentials(self):
        from app.config import settings
        token_path = settings.GMAIL_TOKEN_PATH
        creds = None

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        return creds

    def _create_message(self, sender, to, subject, body):
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        if not self._available:
            logger.warning("send_email skipped — credentials.json missing")
            return False
        try:
            return await asyncio.to_thread(self._sync_send, to, subject, body)
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return False

    def _sync_send(self, to: str, subject: str, body: str) -> bool:
        creds = self._load_credentials()
        service = build('gmail', 'v1', credentials=creds)

        message = self._create_message(self.sender_email, to, subject, body)
        send_message = service.users().messages().send(
            userId='me', body=message).execute()

        logger.info(f"Email sent to {to} (id: {send_message['id']})")
        return True

    async def search_replies(self, lead_email: str, after_datetime: datetime) -> list[str]:
        if not self._available:
            return []
        try:
            return await asyncio.to_thread(self._sync_search_replies, lead_email, after_datetime)
        except Exception as e:
            logger.error("Failed to search replies for %s: %s", lead_email, e)
            return []

    def _sync_search_replies(self, lead_email: str, after_datetime: datetime) -> list[str]:
        epoch = int(after_datetime.timestamp())
        query = f"from:{lead_email} to:me after:{epoch}"
        creds = self._load_credentials()
        service = build('gmail', 'v1', credentials=creds)
        result = service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])
        return [m['id'] for m in messages]
