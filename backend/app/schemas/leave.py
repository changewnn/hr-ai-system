from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LeaveTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=30)
    days_per_year: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=2)


class LeaveTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    days_per_year: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=2)
    enabled: bool | None = None


class LeaveBalanceUpdate(BaseModel):
    employee_id: int
    leave_type_id: int
    year: int = Field(ge=2000, le=2200)
    quota: Decimal = Field(ge=0, max_digits=5, decimal_places=2)


class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    start_period: str = Field(pattern="^(AM|PM|FULL_DAY)$")
    end_period: str = Field(pattern="^(AM|PM|FULL_DAY)$")
    reason: str = Field(min_length=1, max_length=1000)


class LeaveApprovalRequest(BaseModel):
    action: str = Field(pattern="^(APPROVE|REJECT)$")
    comment: str | None = Field(default=None, max_length=1000)
