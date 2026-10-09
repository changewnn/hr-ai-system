from __future__ import annotations

import enum
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class ActiveStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESIGNED = "RESIGNED"


class AttendanceStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    LATE = "LATE"
    EARLY_LEAVE = "EARLY_LEAVE"
    MISSING = "MISSING"
    LEAVE = "LEAVE"


class LeaveStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class SalaryStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class MessageType(str, enum.Enum):
    APPROVAL_TODO = "APPROVAL_TODO"
    APPROVAL_RESULT = "APPROVAL_RESULT"
    SALARY_PUBLISHED = "SALARY_PUBLISHED"


class PolicyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), index=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id", ondelete="SET NULL"), unique=True)
    status: Mapped[ActiveStatus] = mapped_column(Enum(ActiveStatus, name="user_status_enum"), default=ActiveStatus.ACTIVE)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Department(Base):
    __tablename__ = "department"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="RESTRICT"), index=True)
    leader_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id", ondelete="SET NULL"))
    status: Mapped[ActiveStatus] = mapped_column(Enum(ActiveStatus, name="department_status_enum"), default=ActiveStatus.ACTIVE)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Position(Base):
    __tablename__ = "position"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[ActiveStatus] = mapped_column(Enum(ActiveStatus, name="position_status_enum"), default=ActiveStatus.ACTIVE)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Employee(Base):
    __tablename__ = "employee"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    gender: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    id_card_encrypted: Mapped[str | None] = mapped_column(Text)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id", ondelete="RESTRICT"), index=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("position.id", ondelete="RESTRICT"), index=True)
    hire_date: Mapped[date] = mapped_column(Date)
    status: Mapped[EmployeeStatus] = mapped_column(Enum(EmployeeStatus, name="employee_status_enum"), default=EmployeeStatus.ACTIVE, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emergency_contact: Mapped[str | None] = mapped_column(String(100))
    emergency_phone: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceRule(Base):
    __tablename__ = "attendance_rule"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    work_end_time: Mapped[time] = mapped_column(Time, default=time(18, 0))
    late_threshold: Mapped[int] = mapped_column(Integer, default=5)
    early_leave_threshold: Mapped[int] = mapped_column(Integer, default=5)
    work_days: Mapped[list[int]] = mapped_column(JSON, default=lambda: [1, 2, 3, 4, 5])
    single_deduct: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("20.00"))


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"), Index("ix_attendance_month", "work_date", "employee_id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id", ondelete="RESTRICT"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus, name="attendance_status_enum"))
    adjust_note: Mapped[str | None] = mapped_column(Text)
    adjusted_by: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class LeaveType(Base):
    __tablename__ = "leave_type"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    days_per_year: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    status: Mapped[ActiveStatus] = mapped_column(Enum(ActiveStatus, name="leave_type_status_enum"), default=ActiveStatus.ACTIVE)


class LeaveRequest(Base):
    __tablename__ = "leave_request"
    __table_args__ = (Index("ix_leave_employee_dates", "employee_id", "start_date", "end_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    request_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id", ondelete="RESTRICT"), index=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_type.id", ondelete="RESTRICT"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    start_period: Mapped[str] = mapped_column(String(10))
    end_period: Mapped[str] = mapped_column(String(10))
    days: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus, name="leave_status_enum"), default=LeaveStatus.DRAFT, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class LeaveApproval(Base):
    __tablename__ = "leave_approval"
    id: Mapped[int] = mapped_column(primary_key=True)
    leave_request_id: Mapped[int] = mapped_column(ForeignKey("leave_request.id", ondelete="CASCADE"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"))
    action: Mapped[ApprovalAction] = mapped_column(Enum(ApprovalAction, name="approval_action_enum"))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SalaryConfig(Base):
    __tablename__ = "salary_config"
    __table_args__ = (UniqueConstraint("employee_id", name="uq_salary_config_employee"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id", ondelete="RESTRICT"))
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    social_security: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    housing_fund: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("5000.00"))
    effective_date: Mapped[date] = mapped_column(Date)


class SalaryRecord(Base):
    __tablename__ = "salary_record"
    __table_args__ = (UniqueConstraint("employee_id", "month", name="uq_salary_employee_month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id", ondelete="RESTRICT"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    attendance_deduct: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    social_security: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    housing_fund: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[SalaryStatus] = mapped_column(Enum(SalaryStatus, name="salary_status_enum"), default=SalaryStatus.DRAFT, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
