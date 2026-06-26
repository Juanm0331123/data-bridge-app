from http import HTTPStatus
from typing import Any

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response
from fastapi import Request

from app.config import settings
from app.logging import log

GENERIC_INTERNAL_MESSAGE = "Ocurrio un error interno procesando la solicitud."
GENERIC_REQUEST_MESSAGE = "No fue posible procesar la solicitud."
PRODUCTION_ENV = "production"


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = HTTPStatus.BAD_REQUEST,
        error_code: str = "application_error",
        details: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        try:
            return await call_next(request)
        except AppError as error:
            self._log_app_error(request, error)
            if settings.APP_ENV.lower() == PRODUCTION_ENV:
                return self._build_response(
                    error.status_code,
                    "request_error",
                    GENERIC_REQUEST_MESSAGE,
                )

            return self._build_response(
                error.status_code, error.error_code, error.message
            )
        except Exception as error:
            self._log_unexpected_error(request, error)
            return self._build_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_server_error",
                GENERIC_INTERNAL_MESSAGE,
            )

    def _build_response(
        self,
        status_code: int,
        error_code: str,
        message: str,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                },
            },
        )

    def _log_app_error(self, request: Request, error: AppError) -> None:
        log.error(
            f"{request.method} {request.url.path} | app_error | "
            f"code={error.error_code} | status_code={error.status_code}"
        )

    def _log_unexpected_error(self, request: Request, error: Exception) -> None:
        log.error(
            f"{request.method} {request.url.path} | unexpected_error | "
            f"error_type={type(error).__name__}"
        )


async def http_exception_handler(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    log.warn(
        f"{request.method} {request.url.path} | http_error | "
        f"status_code={error.status_code}"
    )

    if settings.APP_ENV.lower() == PRODUCTION_ENV:
        if error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            return JSONResponse(
                status_code=error.status_code,
                content={
                    "success": False,
                    "error": {
                        "code": "internal_server_error",
                        "message": GENERIC_INTERNAL_MESSAGE,
                    },
                },
            )

        return JSONResponse(
            status_code=error.status_code,
            content={
                "success": False,
                "error": {
                    "code": "request_error",
                    "message": GENERIC_REQUEST_MESSAGE,
                },
            },
        )

    detail = error.detail if isinstance(error.detail, str) else GENERIC_REQUEST_MESSAGE
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "error": {
                "code": "http_error",
                "message": detail,
            },
        },
    )


async def validation_exception_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    log.warn(
        f"{request.method} {request.url.path} | validation_error | "
        f"errors_count={len(error.errors())}"
    )

    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "validation_error",
                "message": "La solicitud no es valida.",
            },
        },
    )
