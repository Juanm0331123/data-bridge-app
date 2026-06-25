from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.postgresql import postgres_db
from app.integrations.zoho_analytics import zoho_analytics
from app.config import settings
from app.middleware.error_handler import AppError
from app.logging import log


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        log.bloque_inicio("Iniciando Data Bridge")

        log.step("Inicializando conexion con PostgreSQL...")
        postgres_db.connect()

        await postgres_db.check_connection()

        log.ok("Base de datos PostgreSQL lista.")

        if settings.ZOHO_REQUIRED:
            log.step("Inicializando conexion con Zoho Analytics...")
            await zoho_analytics.connect()
            await zoho_analytics.check_connection()
            log.ok("Zoho Analytics listo.")
        else:
            log.info("ZOHO_REQUIRED=false, se omite la validacion de Zoho Analytics.")

        log.ok("Aplicacion inicializada correctamente.")
        log.bloque_fin("Startup completo")

        yield

    except Exception as error:
        if isinstance(error, AppError) and error.details is not None:
            log.error(
                f"Error durante el ciclo de vida de la aplicacion: {error.details}"
            )
        else:
            log.error(f"Error durante el ciclo de vida de la aplicacion: {error}")

        raise

    finally:
        log.bloque_inicio("Apagando Data Bridge")

        try:
            await zoho_analytics.disconnect()
            await postgres_db.disconnect()
            log.ok("Recursos liberados correctamente.")

        except Exception as error:
            if isinstance(error, AppError) and error.details is not None:
                log.error(f"Error cerrando recursos de la aplicacion: {error.details}")
            else:
                log.error(f"Error cerrando recursos de la aplicacion: {error}")

            raise

        finally:
            log.bloque_fin("Shutdown completo")
