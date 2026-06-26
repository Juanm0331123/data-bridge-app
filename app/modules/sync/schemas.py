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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "target_table": "customers",
                    "limit": 10,
                    "offset": 0,
                }
            ]
        }
    )

    target_table: str = Field(
        min_length=1,
        description="Nombre de la tabla PostgreSQL que se desea previsualizar.",
        examples=["customers"],
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="Cantidad maxima de filas a devolver. Si se omite, devuelve desde el offset.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Cantidad de filas a omitir antes de devolver resultados.",
    )


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
