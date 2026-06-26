from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PreviewZohoDataRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "view_id": "123456789012345678",
                    "workspace_id": "123456789012345678",
                    "limit": 10,
                    "offset": 0,
                }
            ]
        }
    )

    view_id: str = Field(
        min_length=1,
        description="ID real de la vista de Zoho Analytics.",
        examples=["123456789012345678"],
    )
    workspace_id: str | None = Field(
        default=None,
        description=(
            "ID real del workspace de Zoho Analytics. "
            "Si se omite, usa el workspace configurado por defecto."
        ),
        examples=["123456789012345678"],
    )
    limit: int | None = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)


class PreviewPostgresTableRequest(BaseModel):
    target_table: str = Field(..., min_length=1)
    limit: int | None = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)


class DataPreviewResponse(BaseModel):
    success: bool
    source: str
    count: int
    limit: int | None = None
    offset: int
    columns: list[str]
    rows: list[dict[str, Any]]

    workspace_id: str | None = None
    view_id: str | None = None
    target_table: str | None = None
