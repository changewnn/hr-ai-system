import asyncio
from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.entities import AttendanceRule, LeaveType
from app.models.tax import TaxBracket


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        rule = await session.scalar(select(AttendanceRule).limit(1))
        if rule is None:
            session.add(AttendanceRule())
        defaults = [
            ("年假", "ANNUAL", Decimal("0.00")),
            ("事假", "PERSONAL", None),
            ("病假", "SICK", None),
            ("调休", "TIME_OFF", None),
        ]
        existing = {row.code for row in (await session.scalars(select(LeaveType))).all()}
        for name, code, days in defaults:
            if code not in existing:
                session.add(LeaveType(name=name, code=code, days_per_year=days))
        if await session.scalar(select(TaxBracket).limit(1)) is None:
            tax_brackets = [
                (Decimal("0.00"), Decimal("3000.00"), Decimal("0.03"), Decimal("0.00")),
                (Decimal("3000.01"), Decimal("12000.00"), Decimal("0.10"), Decimal("210.00")),
                (Decimal("12000.01"), Decimal("25000.00"), Decimal("0.20"), Decimal("1410.00")),
                (Decimal("25000.01"), Decimal("35000.00"), Decimal("0.25"), Decimal("2660.00")),
                (Decimal("35000.01"), Decimal("55000.00"), Decimal("0.30"), Decimal("4410.00")),
                (Decimal("55000.01"), Decimal("80000.00"), Decimal("0.35"), Decimal("7160.00")),
                (Decimal("80000.01"), None, Decimal("0.45"), Decimal("15160.00")),
            ]
            for index, (lower, upper, rate, deduction) in enumerate(tax_brackets, start=1):
                session.add(TaxBracket(lower_bound=lower, upper_bound=upper, tax_rate=rate, quick_deduction=deduction, sort_order=index))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
