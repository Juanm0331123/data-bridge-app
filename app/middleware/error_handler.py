from http import HTTPStatus
from traceback import format_exc
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.logging import log


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
            return self._build_response(
                error.status_code, error.error_code, error.message
            )
        except Exception as error:
            self._log_unexpected_error(request, error)
            return self._build_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_server_error",
                "Ocurrio un error interno procesando la solicitud.",
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
        details = error.details or error.message
        log.error(
            f"{request.method} {request.url.path} | {error.error_code} | {details}"
        )

    def _log_unexpected_error(self, request: Request, error: Exception) -> None:
        log.error(
            f"{request.method} {request.url.path} | unexpected_error | {error}\n{format_exc()}"
        )
