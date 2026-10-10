from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.common.errors import BusinessError, business_error_handler


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"code": 90002, "error_key": "VALIDATION_ERROR", "message": "请求参数校验失败", "data": exc.errors()})

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.departments import router as departments_router
from app.api.routes.positions import router as positions_router
from app.api.routes.employees import router as employees_router
from app.api.routes.attendance import router as attendance_router
from app.api.routes.leaves import router as leaves_router
from app.api.routes.salary import router as salary_router
from app.api.routes.messages import router as messages_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )
    application.include_router(health_router, prefix="/api")
    application.include_router(auth_router, prefix="/api")
    application.include_router(departments_router, prefix="/api")
    application.include_router(positions_router, prefix="/api")
    application.include_router(employees_router, prefix="/api")
    application.include_router(attendance_router, prefix="/api")
    application.include_router(leaves_router, prefix="/api")
    application.include_router(salary_router, prefix="/api")
    application.include_router(messages_router, prefix="/api")
    application.add_exception_handler(BusinessError, business_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    return application


app = create_app()
