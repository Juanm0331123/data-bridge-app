from app.api.v1.router import router as api_v1_router
from app.lifespan import lifespan
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.config import settings
from fastapi import FastAPI
from app.logging import log

import uvicorn


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.add_middleware(ErrorHandlerMiddleware)

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
        log.error(f"No fue posible iniciar el servidor: {error}")
        raise
