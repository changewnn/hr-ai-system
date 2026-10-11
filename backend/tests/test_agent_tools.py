from datetime import date

from fastapi.encoders import jsonable_encoder

from app.services.agent_tools import detect_tool, parse_leave_request
from app.services.audit import _sanitize


def test_agent_tool_detection_and_leave_parsing():
    assert detect_tool("查询我的工资条") == "my_salary_slips"
    assert detect_tool("我的年假余额") == "my_leave_balance"
    assert parse_leave_request("申请 2026-10-20 至 2026-10-21 年假，原因：个人事务") == {
        "start_date": "2026-10-20", "end_date": "2026-10-21", "reason": "个人事务", "leave_type_code": "ANNUAL"
    }


def test_sensitive_audit_fields_are_redacted_and_dates_are_json_safe():
    assert _sanitize({"api_key": "secret", "password": "secret"}) == {"api_key": "[REDACTED]", "password": "[REDACTED]"}
    assert jsonable_encoder({"date": date(2026, 10, 20)}) == {"date": "2026-10-20"}
