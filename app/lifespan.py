from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.postgresql import postgres_db
from app.logging import log


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        log.bloque_inicio("Iniciando Data Bridge")

        log.step("Inicializando conexión con PostgreSQL...")
        postgres_db.connect()

        await postgres_db.check_connection()

        log.ok("Base de datos PostgreSQL lista.")
        log.ok("Aplicación inicializada correctamente.")
        log.bloque_fin("Startup completo")

        yield

    except Exception as error:
        log.error(f"Error durante el ciclo de vida de la aplicación: {error}")
        raise

    finally:
        log.bloque_inicio("Apagando Data Bridge")

        try:
            await postgres_db.disconnect()
            log.ok("Recursos liberados correctamente.")

        except Exception as error:
            log.error(f"Error cerrando recursos de la aplicación: {error}")
            raise

        finally:
            log.bloque_fin("Shutdown completo")
