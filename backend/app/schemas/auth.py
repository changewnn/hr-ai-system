from pydantic import BaseModel, Field

from app.models.entities import Role


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=64, description="工号或手机号")
    password: str = Field(min_length=1, max_length=128)


class UserSummary(BaseModel):
    id: int
    username: str
    role: Role
    employee_id: int | None = None
    status: str | None = None
    must_change_password: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AccountCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: Role
    employee_id: int | None = None


class AccountStatusRequest(BaseModel):
    enabled: bool
