from decimal import Decimal
from types import SimpleNamespace

from app.services.salary import calculate_salary, calculate_tax


def brackets():
    return [
        SimpleNamespace(lower_bound=Decimal("0"), upper_bound=Decimal("3000"), tax_rate=Decimal("0.03"), quick_deduction=Decimal("0"), sort_order=1, enabled=True),
        SimpleNamespace(lower_bound=Decimal("3000.01"), upper_bound=Decimal("12000"), tax_rate=Decimal("0.10"), quick_deduction=Decimal("210"), sort_order=2, enabled=True),
    ]


def test_tax_and_decimal_precision() -> None:
    assert calculate_tax(Decimal("3000"), brackets()) == Decimal("90.00")
    assert calculate_tax(Decimal("5000"), brackets()) == Decimal("290.00")
    assert calculate_tax(Decimal("-1"), brackets()) == Decimal("0.00")


def test_salary_formula() -> None:
    config = SimpleNamespace(base_salary=Decimal("10000"), allowance=Decimal("1000"), social_security=Decimal("500"), housing_fund=Decimal("500"), tax_threshold=Decimal("5000"))
    result = calculate_salary(config, Decimal("1"), 2, Decimal("20"), brackets())
    assert result["gross_salary"] == Decimal("11000.00")
    assert result["attendance_deduct"] == Decimal("499.77")
    assert result["tax"] == Decimal("290.00")
    assert result["net_salary"] == Decimal("9210.23")
