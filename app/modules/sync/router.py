from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import postgres_db

from app.modules.sync.schemas import (
    DataPreviewResponse,
    PreviewPostgresTableRequest,
    PreviewZohoDataRequest,
)
from app.modules.sync.service import SyncService

router = APIRouter()
sync_service = SyncService()


@router.post(
    "/preview/zoho", response_model=DataPreviewResponse, status_code=status.HTTP_200_OK
)
async def preview_zoho_data_route(
    payload: PreviewZohoDataRequest,
) -> DataPreviewResponse:
    return await sync_service.preview_zoho_data(payload)


@router.post(
    "/preview/postgresql",
    response_model=DataPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Previsualizar tabla PostgreSQL",
)
async def preview_postgresql_data(
    payload: PreviewPostgresTableRequest,
    db: AsyncSession = Depends(postgres_db.get_session),
) -> DataPreviewResponse:
    return await sync_service.preview_postgresql_data(payload, db)
