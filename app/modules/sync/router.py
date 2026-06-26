from fastapi import APIRouter, status

from app.modules.sync.schemas import (
    PreviewZohoDataRequest,
    DataPreviewResponse,
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
