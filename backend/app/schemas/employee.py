from datetime import date

from pydantic import BaseModel, EmailStr, Field


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    gender: str | None = None
    phone: str = Field(min_length=5, max_length=32)
    email: EmailStr | None = None
    id_card: str | None = None
    department_id: int
    position_id: int
    hire_date: date
    emergency_contact: str | None = None
    emergency_phone: str | None = None


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: str | None = None
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: EmailStr | None = None
    id_card: str | None = None
    department_id: int | None = None
    position_id: int | None = None
    hire_date: date | None = None
    emergency_contact: str | None = None
    emergency_phone: str | None = None
