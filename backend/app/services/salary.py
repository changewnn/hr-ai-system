from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")
WORK_DAYS_PER_MONTH = Decimal("21.75")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def calculate_tax(taxable_income: Decimal, brackets: list) -> Decimal:
    taxable = max(Decimal("0"), taxable_income)
    if taxable == 0:
        return Decimal("0.00")
    for bracket in sorted(brackets, key=lambda item: item.sort_order):
        if not bracket.enabled:
            continue
        if taxable >= bracket.lower_bound and (bracket.upper_bound is None or taxable <= bracket.upper_bound):
            return money(max(Decimal("0"), taxable * bracket.tax_rate - bracket.quick_deduction))
    return Decimal("0.00")


def calculate_salary(config, absent_days: Decimal, late_early_count: int, single_deduct: Decimal, brackets: list) -> dict[str, Decimal]:
    daily_salary = money(config.base_salary / WORK_DAYS_PER_MONTH)
    attendance_deduct = money(absent_days * daily_salary + Decimal(late_early_count) * single_deduct)
    gross_salary = money(config.base_salary + config.allowance)
    taxable_income = max(Decimal("0"), gross_salary - config.social_security - config.housing_fund - config.tax_threshold)
    tax = calculate_tax(taxable_income, brackets)
    net_salary = money(gross_salary - attendance_deduct - config.social_security - config.housing_fund - tax)
    return {"base_salary": money(config.base_salary), "allowance": money(config.allowance), "attendance_deduct": attendance_deduct, "social_security": money(config.social_security), "housing_fund": money(config.housing_fund), "tax": tax, "gross_salary": gross_salary, "net_salary": net_salary}
