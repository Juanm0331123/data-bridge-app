from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.exc import SQLAlchemyError
from collections.abc import AsyncGenerator
from sqlalchemy import text

from app.middleware.error_handler import AppError
from app.logging import log
from app.config import settings


class PostgresDatabase:
    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    def connect(self) -> None:
        try:
            log.step("Creando engine en PostgreSQL...")

            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                connect_args={
                    "server_settings": {
                        "search_path": settings.PG_SCHEMA_MV3,
                    }
                },
            )

            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            log.info("Engine de PostgreSQL creado correctamente.")

        except SQLAlchemyError as error:
            log.error(f"Error creando engine de PostgreSQL: {error}")
            raise AppError(
                "No fue posible preparar la conexion con PostgreSQL.",
                status_code=503,
                error_code="database_engine_error",
                details=f"Error creando engine de PostgreSQL: {error}",
            ) from error

        except Exception as error:
            log.error(f"Error inesperado creando engine de PostgreSQL: {error}")
            raise AppError(
                "No fue posible preparar la conexion con PostgreSQL.",
                status_code=503,
                error_code="database_engine_unexpected_error",
                details=f"Error inesperado creando engine de PostgreSQL: {error}",
            ) from error

    async def check_connection(self) -> None:
        if self.engine is None:
            raise AppError(
                "La conexion con PostgreSQL no esta disponible.",
                status_code=503,
                error_code="database_not_initialized",
                details="El engine de PostgreSQL no esta inicializado.",
            )

        try:
            log.step("Verificando la conexión a la base de datos PostgreSQL...")

            async with self.engine.connect() as connection:
                result = await connection.execute(text("SELECT 1"))
                value = result.scalar_one()

                if value != 1:
                    raise AppError(
                        "La conexion con PostgreSQL no esta disponible.",
                        status_code=503,
                        error_code="database_healthcheck_failed",
                        details="PostgreSQL respondio, pero SELECT 1 fallo.",
                    )

            log.ok("Conexión real con PostgreSQL verificada correctamente.")

        except SQLAlchemyError as error:
            log.error(f"No fue posible conectar con PostgreSQL: {error}")
            raise AppError(
                "No fue posible conectar con PostgreSQL.",
                status_code=503,
                error_code="database_connection_error",
                details=f"No fue posible conectar con PostgreSQL: {error}",
            ) from error

        except Exception as error:
            if isinstance(error, AppError):
                raise

            log.error(f"Error inesperado verificando PostgreSQL: {error}")
            raise AppError(
                "La conexion con PostgreSQL no esta disponible.",
                status_code=503,
                error_code="database_connection_unexpected_error",
                details=f"Error inesperado verificando PostgreSQL: {error}",
            ) from error

    async def disconnect(self) -> None:
        if self.engine is None:
            log.warn("No hay engine de PostgreSQL para cerrar.")
            return

        try:
            log.step("Cerrando pool de PostgreSQL...")

            await self.engine.dispose()

            self.engine = None
            self.session_factory = None

            log.ok("Pool de PostgreSQL cerrado correctamente.")

        except SQLAlchemyError as error:
            log.error(f"Error cerrando PostgreSQL: {error}")
            raise AppError(
                "No fue posible cerrar la conexion con PostgreSQL.",
                status_code=500,
                error_code="database_disconnect_error",
                details=f"Error cerrando PostgreSQL: {error}",
            ) from error

        except Exception as error:
            log.error(f"Error inesperado cerrando PostgreSQL: {error}")
            raise AppError(
                "No fue posible cerrar la conexion con PostgreSQL.",
                status_code=500,
                error_code="database_disconnect_unexpected_error",
                details=f"Error inesperado cerrando PostgreSQL: {error}",
            ) from error

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if self.session_factory is None:
            raise AppError(
                "La conexion con PostgreSQL no esta disponible.",
                status_code=503,
                error_code="database_session_not_initialized",
                details="La sesion de PostgreSQL no ha sido inicializada.",
            )

        try:
            async with self.session_factory() as session:
                yield session

        except SQLAlchemyError as error:
            log.error(f"Error en sesión de PostgreSQL: {error}")
            raise AppError(
                "No fue posible obtener una sesion de PostgreSQL.",
                status_code=503,
                error_code="database_session_error",
                details=f"Error en sesion de PostgreSQL: {error}",
            ) from error

        except Exception as error:
            log.error(f"Error inesperado en sesión de PostgreSQL: {error}")
            raise AppError(
                "No fue posible obtener una sesion de PostgreSQL.",
                status_code=503,
                error_code="database_session_unexpected_error",
                details=f"Error inesperado en sesion de PostgreSQL: {error}",
            ) from error


postgres_db = PostgresDatabase()
