from app.api.v1.router import router as api_v1_router
from app.middleware.error_handler import (
    validation_exception_handler,
    ErrorHandlerMiddleware,
    http_exception_handler,
)
from app.lifespan import lifespan
from app.config import settings
from app.logging import log

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI
import uvicorn


def create_app() -> FastAPI:
    is_production = settings.APP_ENV.lower() == "production"
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    app.add_middleware(ErrorHandlerMiddleware)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()

if __name__ == "__main__":
    try:
        log.bloque_inicio(settings.APP_NAME)

        log.info(f"Entorno: {settings.APP_ENV}")
        log.info(f"Host: {settings.APP_HOST}")
        log.info(f"Puerto: {settings.APP_PORT}")
        log.step("Levantando servidor FastAPI...")

        uvicorn.run(
            "main:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=settings.APP_ENV == "development",
        )

    except Exception as error:
        log.error(
            "No fue posible iniciar el servidor " f"| error_type={type(error).__name__}"
        )
        raise
