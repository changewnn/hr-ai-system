from app.models.entities import ActiveStatus, EmployeeStatus, Role, User
from app.services.auth import hash_password, validate_password_strength, verify_password


def test_password_hash_is_bcrypt() -> None:
    hashed = hash_password("Secure123")
    assert hashed.startswith("$2")
    assert verify_password("Secure123", hashed)


def test_password_strength_rejects_weak_password() -> None:
    try:
        validate_password_strength("12345678")
    except Exception as exc:
        assert getattr(exc, "error_key", None) == "AUTH_WEAK_PASSWORD"
    else:
        raise AssertionError("weak password was accepted")


def test_roles_are_explicit() -> None:
    user = User(username="u", password_hash="x", role=Role.EMPLOYEE, status=ActiveStatus.ACTIVE)
    assert user.role == Role.EMPLOYEE
