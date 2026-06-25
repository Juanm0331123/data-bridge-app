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


settings = Settings()
