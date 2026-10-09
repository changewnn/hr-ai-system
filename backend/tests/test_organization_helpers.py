from app.api.routes.employees import _next_employee_no
from app.common.crypto import mask_id_card


def test_employee_number_is_incremented_for_current_day() -> None:
    existing = ["E20261009001", "E20261009003", "E20261008099"]
    result = _next_employee_no(existing)
    assert result.startswith("E")
    assert len(result) == 12


def test_id_card_is_masked() -> None:
    assert mask_id_card("110101199001011234") == "110***********1234"
