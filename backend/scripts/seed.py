import asyncio
from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.entities import AttendanceRule, LeaveType


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
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
