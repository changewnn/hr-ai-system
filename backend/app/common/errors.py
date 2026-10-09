from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class BusinessError(Exception):
    code: int
    error_key: str
    message: str
    http_status: int = 400
    data: object | None = None


async def business_error_handler(_: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "error_key": exc.error_key, "message": exc.message, "data": exc.data},
    )
