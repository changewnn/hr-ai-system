from datetime import date
from decimal import Decimal

import pytest

from app.common.errors import BusinessError
from app.services.leave import calculate_leave_days, working_dates


def test_half_day_and_workday_calculation() -> None:
    assert calculate_leave_days(date(2026, 10, 9), date(2026, 10, 9), "AM", "AM", [1, 2, 3, 4, 5]) == Decimal("0.5")
    assert calculate_leave_days(date(2026, 10, 9), date(2026, 10, 12), "PM", "AM", [1, 2, 3, 4, 5]) == Decimal("1.0")
    assert working_dates(date(2026, 10, 10), date(2026, 10, 12), [1, 2, 3, 4, 5]) == [date(2026, 10, 12)]


def test_invalid_leave_range() -> None:
    with pytest.raises(BusinessError):
        calculate_leave_days(date(2026, 10, 10), date(2026, 10, 9), "AM", "PM", [1, 2, 3, 4, 5])
