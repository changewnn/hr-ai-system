import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    key = hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_sensitive(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_sensitive(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("sensitive value cannot be decrypted") from exc


def mask_id_card(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}{'*' * (len(value) - 7)}{value[-4:]}"
