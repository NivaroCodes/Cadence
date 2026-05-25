import base64
import hashlib
import hmac
import uuid
from cryptography.fernet import Fernet

from app.config import settings


def _derive_key(user_id: uuid.UUID) -> bytes:
    message = str(user_id).encode("utf-8")
    key_bytes = settings.ENCRYPTION_KEY.encode("utf-8")
    derived_hash = hmac.new(key_bytes, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(derived_hash)


def encrypt_token(token: str, user_id: uuid.UUID) -> str:
    key = _derive_key(user_id)
    f = Fernet(key)
    return f.encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str, user_id: uuid.UUID) -> str:
    key = _derive_key(user_id)
    f = Fernet(key)
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
