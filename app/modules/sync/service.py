from app.integrations.zoho_analytics import zoho_analytics
from app.modules.sync.schemas import (
    PreviewPostgresTableRequest,
    PreviewZohoDataRequest,
    DataPreviewResponse,
)
from app.middleware.error_handler import AppError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime
from app.config import settings
from app.logging import log
from sqlalchemy import text
from decimal import Decimal
from http import HTTPStatus
from typing import Any
import re

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SyncService:

    async def preview_zoho_data(
        self,
        payload: PreviewZohoDataRequest,
    ) -> DataPreviewResponse:
        workspace_id = payload.workspace_id or settings.ZHA_WS_DEFAUL

        log.step(
            "Previsualizando data de Zoho Analytics "
            f"| workspace_id={workspace_id} | view_id={payload.view_id}"
        )

        rows = await zoho_analytics.export_view_data(
            workspace_id,
            payload.view_id,
        )

        count = len(rows)
        if payload.limit is None:
            preview_rows = rows[payload.offset :]
        else:
            preview_rows = rows[payload.offset : payload.offset + payload.limit]

        columns: list[str] = []
        seen_columns: set[str] = set()

        for row in rows:
            for column in row.keys():
                if column not in seen_columns:
                    columns.append(column)
                    seen_columns.add(column)

        serialized_rows: list[dict[str, Any]] = []

        for row in preview_rows:
            serialized_row: dict[str, Any] = {}

            for column, value in row.items():
                if isinstance(value, (datetime, date)):
                    serialized_row[str(column)] = value.isoformat()
                elif isinstance(value, Decimal):
                    serialized_row[str(column)] = float(value)
                else:
                    serialized_row[str(column)] = value

            serialized_rows.append(serialized_row)

        return DataPreviewResponse(
            success=True,
            source="zoho_analytics",
            workspace_id=workspace_id,
            view_id=payload.view_id,
            count=count,
            limit=payload.limit,
            offset=payload.offset,
            columns=columns,
            rows=serialized_rows,
        )

    async def preview_postgresql_data(
        self,
        payload: PreviewPostgresTableRequest,
        db: AsyncSession,
    ) -> DataPreviewResponse:
        target_table = payload.target_table.strip()
        schema_name = settings.PG_SCHEMA_MV3.strip()

        if not IDENTIFIER_PATTERN.fullmatch(target_table):
            raise AppError(
                "El nombre de la tabla solicitada no es valido.",
                status_code=HTTPStatus.BAD_REQUEST,
                error_code="postgres_invalid_table_name",
                details=f"Nombre de tabla rechazado para preview PostgreSQL: {target_table!r}",
            )

        try:
            if not schema_name:
                current_schema_result = await db.execute(
                    text("SELECT current_schema()")
                )
                current_schema = current_schema_result.scalar_one_or_none()
                schema_name = str(current_schema or "").strip()

            if not schema_name:
                raise AppError(
                    "La configuracion de PostgreSQL no esta disponible.",
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    error_code="postgres_invalid_schema_config",
                    details="PG_SCHEMA_MV3 esta vacio y PostgreSQL no devolvio current_schema().",
                )

            log.step(
                "Previsualizando data de PostgreSQL "
                f"| schema={schema_name} | table={target_table}"
            )

            table_exists_result = await db.execute(
                text("""
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = :schema_name
                    AND table_name = :table_name
                    AND table_type = 'BASE TABLE'
                    LIMIT 1
                    """),
                {"schema_name": schema_name, "table_name": target_table},
            )

            if table_exists_result.scalar_one_or_none() is None:
                raise AppError(
                    "La tabla solicitada no fue encontrada.",
                    status_code=HTTPStatus.NOT_FOUND,
                    error_code="postgres_table_not_found",
                    details=(
                        "No existe la tabla PostgreSQL solicitada "
                        f"| schema={schema_name} | table={target_table}"
                    ),
                )

            quoted_schema = schema_name.replace('"', '""')
            quoted_table = target_table.replace('"', '""')
            qualified_table = f'"{quoted_schema}"."{quoted_table}"'
            count_result = await db.execute(
                text(f"SELECT COUNT(*) FROM {qualified_table}")
            )
            count = int(count_result.scalar_one())

            if payload.limit is None:
                rows_result = await db.execute(
                    text(f"SELECT * FROM {qualified_table} OFFSET :offset"),
                    {"offset": payload.offset},
                )
            else:
                rows_result = await db.execute(
                    text(
                        f"SELECT * FROM {qualified_table} LIMIT :limit OFFSET :offset"
                    ),
                    {"limit": payload.limit, "offset": payload.offset},
                )

            columns = [str(column) for column in rows_result.keys()]
            rows = rows_result.mappings().all()
            serialized_rows: list[dict[str, Any]] = []

            for row in rows:
                serialized_row: dict[str, Any] = {}

                for column, value in row.items():
                    if isinstance(value, (datetime, date)):
                        serialized_row[str(column)] = value.isoformat()
                    elif isinstance(value, Decimal):
                        serialized_row[str(column)] = float(value)
                    else:
                        serialized_row[str(column)] = value

                serialized_rows.append(serialized_row)

            return DataPreviewResponse(
                success=True,
                source="postgresql",
                count=count,
                limit=payload.limit,
                offset=payload.offset,
                columns=columns,
                rows=serialized_rows,
                target_table=target_table,
            )

        except AppError:
            raise

        except SQLAlchemyError as error:
            raise AppError(
                "No fue posible previsualizar la tabla solicitada.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="postgres_preview_query_error",
                details=(
                    "SQLAlchemyError previsualizando tabla PostgreSQL "
                    f"| schema={schema_name} | table={target_table} | error={error}"
                ),
            ) from error

        except Exception as error:
            raise AppError(
                "Ocurrio un error interno previsualizando la tabla solicitada.",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                error_code="postgres_preview_unexpected_error",
                details=(
                    "Error inesperado previsualizando tabla PostgreSQL "
                    f"| schema={schema_name} | table={target_table} | error={error}"
                ),
            ) from error
