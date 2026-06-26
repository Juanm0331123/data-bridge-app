from app.integrations.zoho_analytics import zoho_analytics
from app.modules.sync.schemas import (
    ZohoToPostgresUpsertResponse,
    PreviewPostgresTableRequest,
    ZohoToPostgresUpsertRequest,
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

    async def zoho_to_postgresql(
        self,
        payload: ZohoToPostgresUpsertRequest,
        db: AsyncSession,
    ) -> ZohoToPostgresUpsertResponse:
        target_table = payload.target_table.strip()
        schema_name = settings.PG_SCHEMA_MV3.strip()
        batch_size = 1000

        if not IDENTIFIER_PATTERN.fullmatch(target_table):
            raise AppError(
                "El nombre de la tabla destino no es valido.",
                status_code=HTTPStatus.BAD_REQUEST,
                error_code="postgres_invalid_table_name",
                details=f"Nombre de tabla rechazado para upsert: {target_table!r}",
            )

        upsert_key: list[str] = []
        seen_upsert_columns: set[str] = set()

        for column in payload.upsert_key:
            normalized_column = column.strip()

            if not normalized_column:
                raise AppError(
                    "La llave de upsert contiene una columna vacia.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_invalid_upsert_key",
                    details=f"Upsert key con columna vacia: {payload.upsert_key!r}",
                )

            if not IDENTIFIER_PATTERN.fullmatch(normalized_column):
                raise AppError(
                    "La llave de upsert contiene una columna no valida.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_invalid_upsert_key",
                    details=f"Columna de upsert rechazada: {normalized_column!r}",
                )

            if normalized_column in seen_upsert_columns:
                raise AppError(
                    "La llave de upsert contiene columnas repetidas.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_invalid_upsert_key",
                    details=f"Upsert key con columnas repetidas: {payload.upsert_key!r}",
                )

            upsert_key.append(normalized_column)
            seen_upsert_columns.add(normalized_column)

        column_mapping: dict[str, str] = {}
        mapped_postgres_columns: list[str] = []
        seen_postgres_columns: set[str] = set()

        for zoho_column, postgres_column in payload.column_mapping.items():
            normalized_postgres_column = postgres_column.strip()

            if not zoho_column.strip() or not normalized_postgres_column:
                raise AppError(
                    "El mapeo de columnas contiene valores vacios.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="sync_invalid_column_mapping",
                    details=f"Column mapping con valores vacios: {payload.column_mapping!r}",
                )

            if not IDENTIFIER_PATTERN.fullmatch(normalized_postgres_column):
                raise AppError(
                    "El mapeo contiene una columna PostgreSQL no valida.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="sync_invalid_column_mapping",
                    details=(
                        "Columna PostgreSQL rechazada en column_mapping: "
                        f"{normalized_postgres_column!r}"
                    ),
                )

            if normalized_postgres_column in seen_postgres_columns:
                raise AppError(
                    "El mapeo no puede apuntar varias columnas de Zoho a la misma columna PostgreSQL.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="sync_duplicate_postgres_mapping",
                    details=(
                        "Column mapping con columna PostgreSQL destino repetida: "
                        f"{normalized_postgres_column!r}"
                    ),
                )

            column_mapping[zoho_column] = normalized_postgres_column
            mapped_postgres_columns.append(normalized_postgres_column)
            seen_postgres_columns.add(normalized_postgres_column)

        missing_upsert_columns_in_mapping = [
            column for column in upsert_key if column not in seen_postgres_columns
        ]

        if missing_upsert_columns_in_mapping:
            raise AppError(
                "La llave de upsert debe estar incluida en el mapeo hacia PostgreSQL.",
                status_code=HTTPStatus.BAD_REQUEST,
                error_code="postgres_upsert_key_not_mapped",
                details=(
                    "Columnas de upsert ausentes en column_mapping: "
                    f"{missing_upsert_columns_in_mapping}"
                ),
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
                    "La tabla destino no fue encontrada en PostgreSQL.",
                    status_code=HTTPStatus.NOT_FOUND,
                    error_code="postgres_table_not_found",
                    details=(
                        "No existe la tabla PostgreSQL destino para upsert "
                        f"| schema={schema_name} | table={target_table}"
                    ),
                )

            postgres_columns_result = await db.execute(
                text("""
                    SELECT
                        column_name,
                        is_nullable,
                        column_default,
                        is_identity,
                        is_generated
                    FROM information_schema.columns
                    WHERE table_schema = :schema_name
                    AND table_name = :table_name
                    ORDER BY ordinal_position
                    """),
                {"schema_name": schema_name, "table_name": target_table},
            )
            postgres_column_rows = postgres_columns_result.mappings().all()
            postgres_columns = {
                str(row["column_name"]): row for row in postgres_column_rows
            }

            missing_postgres_columns = [
                column
                for column in mapped_postgres_columns
                if column not in postgres_columns
            ]

            if missing_postgres_columns:
                raise AppError(
                    "El mapeo contiene columnas que no existen en PostgreSQL.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_mapped_column_not_found",
                    details=(
                        "Columnas destino ausentes en PostgreSQL "
                        f"| schema={schema_name} | table={target_table} "
                        f"| columns={missing_postgres_columns}"
                    ),
                )

            missing_upsert_columns_in_table = [
                column for column in upsert_key if column not in postgres_columns
            ]

            if missing_upsert_columns_in_table:
                raise AppError(
                    "La llave de upsert contiene columnas que no existen en PostgreSQL.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_invalid_upsert_key",
                    details=(
                        "Columnas de upsert ausentes en PostgreSQL "
                        f"| schema={schema_name} | table={target_table} "
                        f"| columns={missing_upsert_columns_in_table}"
                    ),
                )

            unique_indexes_result = await db.execute(
                text("""
                    SELECT
                        index_class.relname AS index_name,
                        pg_index.indisprimary,
                        pg_index.indisunique,
                        array_agg(attribute.attname ORDER BY key_column.ordinality) AS columns
                    FROM pg_class AS table_class
                    JOIN pg_namespace AS namespace
                    ON namespace.oid = table_class.relnamespace
                    JOIN pg_index
                    ON pg_index.indrelid = table_class.oid
                    JOIN pg_class AS index_class
                    ON index_class.oid = pg_index.indexrelid
                    JOIN unnest(pg_index.indkey) WITH ORDINALITY AS key_column(attnum, ordinality)
                    ON key_column.attnum > 0
                    JOIN pg_attribute AS attribute
                    ON attribute.attrelid = table_class.oid
                    AND attribute.attnum = key_column.attnum
                    WHERE namespace.nspname = :schema_name
                    AND table_class.relname = :table_name
                    AND (pg_index.indisprimary OR pg_index.indisunique)
                    AND pg_index.indpred IS NULL
                    GROUP BY index_class.relname, pg_index.indisprimary, pg_index.indisunique
                    """),
                {"schema_name": schema_name, "table_name": target_table},
            )
            unique_index_rows = unique_indexes_result.mappings().all()
            upsert_key_set = set(upsert_key)
            upsert_key_matches_index = False

            for index_row in unique_index_rows:
                index_columns_value = index_row["columns"]
                index_columns = [str(column) for column in index_columns_value]

                if (
                    len(index_columns) == len(upsert_key)
                    and set(index_columns) == upsert_key_set
                ):
                    upsert_key_matches_index = True
                    break

            if not upsert_key_matches_index:
                raise AppError(
                    "La llave de upsert no coincide con una PK o UNIQUE existente en PostgreSQL.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_invalid_upsert_key",
                    details=(
                        "No existe una PK o UNIQUE que coincida con upsert_key "
                        f"| schema={schema_name} | table={target_table} "
                        f"| upsert_key={upsert_key}"
                    ),
                )

            log.step(
                "Sincronizando Zoho Analytics hacia PostgreSQL "
                f"| workspace_id={payload.workspace_id} | view_id={payload.view_id} "
                f"| schema={schema_name} | table={target_table}"
            )

            zoho_rows = await zoho_analytics.export_view_data(
                payload.workspace_id,
                payload.view_id,
            )
            cant_row_zoho = len(zoho_rows)

            zoho_columns: set[str] = set()
            for row in zoho_rows:
                for column in row.keys():
                    zoho_columns.add(str(column))

            missing_zoho_columns_mapping = sorted(
                column for column in zoho_columns if column not in column_mapping
            )

            if missing_zoho_columns_mapping:
                raise AppError(
                    "Zoho devolvio columnas que no estan incluidas en el mapeo.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="sync_zoho_columns_not_mapped",
                    details=(
                        "Columnas Zoho ausentes en column_mapping "
                        f"| columns={missing_zoho_columns_mapping}"
                    ),
                )

            active_postgres_columns = {
                column_mapping[column]
                for column in zoho_columns
                if column in column_mapping
            }
            required_postgres_columns: list[str] = []

            for column_name, column_metadata in postgres_columns.items():
                is_nullable = str(column_metadata["is_nullable"])
                column_default = column_metadata["column_default"]
                is_identity = str(column_metadata["is_identity"])
                is_generated = str(column_metadata["is_generated"])

                if (
                    is_nullable == "NO"
                    and column_default is None
                    and is_identity != "YES"
                    and is_generated == "NEVER"
                ):
                    required_postgres_columns.append(column_name)

            missing_required_columns = [
                column
                for column in required_postgres_columns
                if column not in active_postgres_columns
            ]

            if zoho_rows and missing_required_columns:
                raise AppError(
                    "Zoho no devolvio datos para columnas requeridas por PostgreSQL.",
                    status_code=HTTPStatus.BAD_REQUEST,
                    error_code="postgres_required_columns_not_mapped",
                    details=(
                        "Columnas PostgreSQL NOT NULL sin default ausentes en datos Zoho "
                        f"| schema={schema_name} | table={target_table} "
                        f"| columns={missing_required_columns}"
                    ),
                )

            quoted_schema = schema_name.replace('"', '""')
            quoted_table = target_table.replace('"', '""')
            qualified_table = f'"{quoted_schema}"."{quoted_table}"'
            quoted_postgres_columns = {
                column: f'"{column.replace(chr(34), chr(34) * 2)}"'
                for column in postgres_columns
            }
            where_clause = " AND ".join(
                f"{quoted_postgres_columns[column]} IS NOT DISTINCT FROM :key_{column}"
                for column in upsert_key
            )
            inserted = 0
            updated = 0
            errors_count = 0

            if not zoho_rows:
                count_result = await db.execute(
                    text(f"SELECT COUNT(*) FROM {qualified_table}")
                )

                return ZohoToPostgresUpsertResponse(
                    success=True,
                    inserted=0,
                    updated=0,
                    total=0,
                    errors_count=0,
                    cant_row_zoho=0,
                    cant_row_pg=int(count_result.scalar_one()),
                )

            await db.commit()

            for row_index, zoho_row in enumerate(zoho_rows, start=1):
                row_transaction = await db.begin_nested()

                try:
                    target_data: dict[str, Any] = {}

                    for zoho_column, postgres_column in column_mapping.items():
                        if zoho_column in zoho_row:
                            target_data[postgres_column] = zoho_row[zoho_column]

                    missing_row_key_columns = [
                        column for column in upsert_key if column not in target_data
                    ]

                    if missing_row_key_columns:
                        raise ValueError(
                            "Fila sin valores para upsert_key: "
                            f"{missing_row_key_columns}"
                        )

                    key_params = {
                        f"key_{column}": target_data[column] for column in upsert_key
                    }
                    update_values = {
                        column: value
                        for column, value in target_data.items()
                        if column not in upsert_key_set
                        and value is not None
                        and not (isinstance(value, str) and value.strip() == "")
                    }

                    if update_values:
                        update_assignments = ", ".join(
                            f"{quoted_postgres_columns[column]} = :set_{column}"
                            for column in update_values
                        )
                        update_params = {
                            f"set_{column}": value
                            for column, value in update_values.items()
                        }
                        update_params.update(key_params)
                        update_result = await db.execute(
                            text(
                                f"UPDATE {qualified_table} "
                                f"SET {update_assignments} "
                                f"WHERE {where_clause}"
                            ),
                            update_params,
                        )
                        row_exists = int(update_result.rowcount or 0) > 0
                    else:
                        existing_row_result = await db.execute(
                            text(
                                f"SELECT 1 FROM {qualified_table} "
                                f"WHERE {where_clause} LIMIT 1"
                            ),
                            key_params,
                        )
                        row_exists = (
                            existing_row_result.scalar_one_or_none() is not None
                        )

                    if row_exists:
                        updated += 1
                    else:
                        insert_columns = list(target_data.keys())
                        insert_columns_sql = ", ".join(
                            quoted_postgres_columns[column] for column in insert_columns
                        )
                        insert_values_sql = ", ".join(
                            f":insert_{column}" for column in insert_columns
                        )
                        insert_params = {
                            f"insert_{column}": value
                            for column, value in target_data.items()
                        }
                        await db.execute(
                            text(
                                f"INSERT INTO {qualified_table} ({insert_columns_sql}) "
                                f"VALUES ({insert_values_sql})"
                            ),
                            insert_params,
                        )
                        inserted += 1

                    await row_transaction.commit()

                except Exception:
                    await row_transaction.rollback()
                    errors_count += 1

                if row_index % batch_size == 0:
                    await db.commit()

            await db.commit()

            count_result = await db.execute(
                text(f"SELECT COUNT(*) FROM {qualified_table}")
            )
            cant_row_pg = int(count_result.scalar_one())

            log.ok(
                "Sincronizacion Zoho Analytics hacia PostgreSQL completada "
                f"| inserted={inserted} | updated={updated} "
                f"| errors_count={errors_count} | cant_row_zoho={cant_row_zoho} "
                f"| cant_row_pg={cant_row_pg}"
            )

            return ZohoToPostgresUpsertResponse(
                success=True,
                inserted=inserted,
                updated=updated,
                total=inserted + updated + errors_count,
                errors_count=errors_count,
                cant_row_zoho=cant_row_zoho,
                cant_row_pg=cant_row_pg,
            )

        except AppError:
            raise

        except SQLAlchemyError as error:
            raise AppError(
                "No fue posible sincronizar Zoho Analytics hacia PostgreSQL.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="sync_zoho_to_postgres_query_error",
                details=(
                    "SQLAlchemyError sincronizando Zoho Analytics hacia PostgreSQL "
                    f"| schema={schema_name} | table={target_table} | error={error}"
                ),
            ) from error

        except Exception as error:
            raise AppError(
                "Ocurrio un error interno sincronizando Zoho Analytics hacia PostgreSQL.",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                error_code="sync_zoho_to_postgres_unexpected_error",
                details=(
                    "Error inesperado sincronizando Zoho Analytics hacia PostgreSQL "
                    f"| schema={schema_name} | table={target_table} | error={error}"
                ),
            ) from error
