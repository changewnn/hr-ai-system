from datetime import datetime, timezone

import bcrypt

from app.models.entities import ActiveStatus, Role, User
from app.core.security import decode_access_token
from app.services.auth import create_access_token, hash_password, verify_password


def test_verify_password() -> None:
    password_hash = bcrypt.hashpw(b"Secret123", bcrypt.gensalt()).decode()
    assert verify_password("Secret123", password_hash)
    assert not verify_password("wrong", password_hash)


def test_hash_password_does_not_store_plaintext() -> None:
    password_hash = hash_password("Secret123")
    assert password_hash != "Secret123"
    assert verify_password("Secret123", password_hash)


def test_access_token_contains_user_claims() -> None:
    user = User(id=7, username="E20261008001", password_hash="unused", role=Role.ADMIN, status=ActiveStatus.ACTIVE)
    token, expires_in = create_access_token(user)
    assert token
    assert expires_in == 8 * 60 * 60
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "ADMIN"
    assert payload["jti"]
