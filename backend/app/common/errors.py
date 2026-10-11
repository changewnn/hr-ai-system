from dataclasses import dataclass
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class BusinessError(Exception):
    code: int
    error_key: str
    message: str
    http_status: int = 400
    data: object | None = None


async def business_error_handler(_: Request, exc: BusinessError) -> JSONResponse:
    is_server_failure = exc.http_status >= 500
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "error_key": exc.error_key,
            "message": "服务暂时不可用，请稍后重试" if is_server_failure else exc.message,
            "data": None if is_server_failure else exc.data,
        },
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Keep implementation details in server logs, never in API responses."""
    logger.exception("Unhandled API exception: %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": 90001,
            "error_key": "INTERNAL_SERVER_ERROR",
            "message": "服务暂时不可用，请稍后重试",
            "data": None,
        },
    )
