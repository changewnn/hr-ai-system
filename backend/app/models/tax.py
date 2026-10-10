from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaxBracket(Base):
    __tablename__ = "tax_bracket"
    id: Mapped[int] = mapped_column(primary_key=True)
    lower_bound: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    upper_bound: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    quick_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sort_order: Mapped[int] = mapped_column(Integer, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
