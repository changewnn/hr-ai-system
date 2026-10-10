from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SalaryConfigCreate(BaseModel):
    employee_id: int
    base_salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    allowance: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    social_security: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    housing_fund: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    tax_threshold: Decimal = Field(default=Decimal("5000.00"), ge=0, max_digits=12, decimal_places=2)
    effective_date: date


class SalaryMonthRequest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class SalaryAdjustmentCreate(BaseModel):
    salary_record_id: int
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    reason: str = Field(min_length=1, max_length=1000)
