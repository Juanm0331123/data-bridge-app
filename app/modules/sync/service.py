from app.integrations.zoho_analytics import zoho_analytics
from app.modules.sync.schemas import (
    PreviewZohoDataRequest,
    DataPreviewResponse,
)
from app.middleware.error_handler import AppError
from datetime import date, datetime
from app.config import settings
from app.logging import log
from sqlalchemy import text
from decimal import Decimal
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
