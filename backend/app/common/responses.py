from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = 0
    error_key: str = "OK"
    message: str = "操作成功"
    data: Any = None
    request_id: str | None = None


class PageData(BaseModel):
    items: list[Any] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0


def success(data: Any = None, request_id: str | None = None, message: str = "操作成功") -> dict[str, Any]:
    return ApiResponse(data=data, request_id=request_id, message=message).model_dump()
