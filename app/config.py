from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import cached_property
from urllib.parse import quote_plus


class Settings(BaseSettings):
    APP_NAME: str = "Data Bridge"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DB_REQUIRED: bool = False

    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL CONNECTION
    PG_HOST_MV3: str
    PG_PORT_MV3: int = 5432
    PG_DATABASE_MV3: str
    PG_USERNAME_MV3: str
    PG_PASSWORD_MV3: str
    PG_SCHEMA_MV3: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @cached_property
    def database_url(self) -> str:
        username = quote_plus(self.PG_USERNAME_MV3)
        password = quote_plus(self.PG_PASSWORD_MV3)

        return (
            f"postgresql+asyncpg://{username}:{password}"
            f"@{self.PG_HOST_MV3}:{self.PG_PORT_MV3}"
            f"/{self.PG_DATABASE_MV3}"
        )

    # Zoho Analytics CONNECTION
    SEC_USER: str | None = None
    SEC_PASSWORD: str | None = None
    SEC_CITY: str = "Cali"

    ZH_TOKEN_URL: str
    ZH_TOKEN_ID: str
    ZH_TOKEN_SECRET: str
    ZHA_REFRESH_TOKEN: str
    ZHC_REFRESH_TOKEN: str | None = None
    ZH_GRANT_TYPE: str = "refresh_token"
    ZH_ACCESS_TOKEN: str | None = None
    ZH_TOKEN_EXPIRY: str | None = None

    ZHA_API_URL: str
    ZHA_API_BULK_URL: str
    ZHA_ORGID: str
    ZHA_WS_DEFAUL: str
    ZHA_WS_AUTOMATIC: str

    ZHA_FILE_JOBID_JSON: str | None = None
    ZHA_FILE_TOKEN_JSON: str | None = None
    ZHA_SCOPE: str | None = None

    ZOHO_REQUIRED: bool = True


settings = Settings()
