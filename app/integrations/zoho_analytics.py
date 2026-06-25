import json
import os
import threading
from collections.abc import Mapping
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.logging import log
from app.middleware.error_handler import AppError


class ZohoAnalyticsClient:
    TOKEN_REFRESH_BUFFER_MINUTES = 5

    def __init__(self) -> None:
        self.client: httpx.AsyncClient | None = None
        self.access_token: str | None = None
        self.token_expiry: datetime | None = self._parse_datetime(settings.ZH_TOKEN_EXPIRY)
        self.expires_in: int | None = None
        self.token_type: str | None = None
        self.scope: str | None = settings.ZHA_SCOPE
        self.api_domain: str | None = None

        self.default_workspace_id = settings.ZHA_WS_DEFAUL
        self.healthcheck_view_id = (
            os.getenv("ZHA_HEALTHCHECK_VIEW_ID") or ""
        ).strip() or None

        project_root = Path(__file__).resolve().parents[2]
        token_file_env = (settings.ZHA_FILE_TOKEN_JSON or "data/tokens/za_tokens.json").strip()
        self.token_file = (project_root / token_file_env).resolve()

        self._lock = threading.Lock()

    async def connect(self) -> None:
        try:
            log.step("Creando cliente HTTP para Zoho Analytics...")

            self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
            self.load_tokens()

            if not self.access_token:
                self.access_token = settings.ZH_ACCESS_TOKEN

            log.info("Cliente HTTP para Zoho Analytics creado correctamente.")

        except Exception as error:
            log.error(f"Error al crear el cliente HTTP para Zoho Analytics: {error}")
            raise AppError(
                "No fue posible preparar la conexion con Zoho Analytics.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_client_error",
                details=f"Error al crear el cliente HTTP para Zoho Analytics: {error}",
            ) from error

    async def check_connection(self) -> None:
        try:
            log.step("Verificando conexion con Zoho Analytics...")

            await self.get_valid_token()

            if self.healthcheck_view_id:
                response = await self.get(
                    self._bulk_view_data_url(
                        self.default_workspace_id,
                        self.healthcheck_view_id,
                    ),
                    params={"CONFIG": json.dumps({"responseFormat": "json"})},
                )
                data = response.json()

                if not isinstance(data, Mapping):
                    raise AppError(
                        "Zoho Analytics respondio con un formato inesperado.",
                        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                        error_code="zoho_response_error",
                        details=f"Respuesta inesperada en check_connection: {data}",
                    )

            else:
                log.info(
                    "No se configuro ZHA_HEALTHCHECK_VIEW_ID; se valida solo OAuth de Zoho Analytics."
                )

            log.ok("Conexion con Zoho Analytics verificada correctamente.")

        except Exception as error:
            if isinstance(error, AppError):
                raise

            log.error(f"Error al verificar la conexion con Zoho Analytics: {error}")
            raise AppError(
                "No fue posible verificar la conexion con Zoho Analytics.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_connection_error",
                details=f"Error al verificar la conexion con Zoho Analytics: {error}",
            ) from error

    async def disconnect(self) -> None:
        if self.client is None:
            log.warn("No hay cliente HTTP de Zoho Analytics para cerrar.")
            return

        try:
            log.step("Cerrando cliente HTTP de Zoho Analytics...")
            await self.client.aclose()

            self.client = None
            self.access_token = None

            log.ok("Cliente HTTP de Zoho Analytics cerrado correctamente.")

        except Exception as error:
            log.error(f"Error al cerrar el cliente HTTP de Zoho Analytics: {error}")
            raise AppError(
                "No fue posible cerrar la conexion con Zoho Analytics.",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                error_code="zoho_disconnect_error",
                details=f"Error al cerrar el cliente HTTP de Zoho Analytics: {error}",
            ) from error

    async def refresh_access_token(self) -> str:
        client = self._ensure_client()

        try:
            with self._lock:
                log.step("Refrescando access token de Zoho Analytics...")

            response = await client.post(
                settings.ZH_TOKEN_URL,
                params={
                    "refresh_token": settings.ZHA_REFRESH_TOKEN,
                    "client_id": settings.ZH_TOKEN_ID,
                    "client_secret": settings.ZH_TOKEN_SECRET,
                    "grant_type": settings.ZH_GRANT_TYPE,
                },
            )
            response.raise_for_status()

            data = response.json()
            access_token = data.get("access_token")

            if not access_token:
                raise AppError(
                    "No fue posible autenticar con Zoho Analytics.",
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    error_code="zoho_response_error",
                    details=f"Respuesta sin access_token: {data}",
                )

            self._update_tokens(data)
            log.ok("Access token de Zoho Analytics actualizado correctamente.")
            return access_token

        except httpx.HTTPStatusError as error:
            log.error(
                f"Error de estado HTTP al refrescar el access token de Zoho Analytics: {error}"
            )
            raise AppError(
                "No fue posible autenticar con Zoho Analytics.",
                status_code=error.response.status_code,
                error_code="zoho_auth_refresh_error",
                details=f"HTTPStatusError refrescando access token: {error}",
            ) from error

        except httpx.RequestError as error:
            log.error(
                f"Error de solicitud HTTP al refrescar el access token de Zoho Analytics: {error}"
            )
            raise AppError(
                "No fue posible autenticar con Zoho Analytics.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_auth_refresh_error",
                details=f"RequestError refrescando access token: {error}",
            ) from error

        except Exception as error:
            if isinstance(error, AppError):
                raise

            log.error(f"Error al refrescar el access token de Zoho Analytics: {error}")
            raise AppError(
                "No fue posible autenticar con Zoho Analytics.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_auth_refresh_error",
                details=f"Error al refrescar el access token de Zoho Analytics: {error}",
            ) from error

    async def get_valid_token(self) -> str:
        if self.is_token_valid():
            return self.access_token or ""

        return await self.refresh_access_token()

    def load_tokens(self) -> dict[str, Any] | None:
        try:
            if not self.token_file.exists():
                return None

            with self.token_file.open("r", encoding="utf-8") as file:
                tokens = json.load(file)

            self.access_token = (tokens.get("access_token") or "").strip() or None
            self.token_expiry = self._parse_datetime(tokens.get("token_expiry"))
            self.expires_in = self._parse_int(tokens.get("expires_in"))
            self.token_type = tokens.get("token_type")
            self.scope = tokens.get("scope") or self.scope
            self.api_domain = tokens.get("api_domain")

            return tokens

        except Exception as error:
            log.warn(f"No fue posible cargar tokens de Zoho Analytics: {error}")
            return None

    def save_tokens(self) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        tokens = {
            "access_token": self.access_token,
            "token_expiry": self.token_expiry.isoformat() if self.token_expiry else None,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
            "scope": self.scope,
            "api_domain": self.api_domain,
        }

        with self.token_file.open("w", encoding="utf-8") as file:
            json.dump(tokens, file, indent=2, ensure_ascii=False)

    def is_token_valid(self) -> bool:
        self.load_tokens()

        if not self.access_token or not self.token_expiry:
            return False

        return datetime.now() < (
            self.token_expiry - timedelta(minutes=self.TOKEN_REFRESH_BUFFER_MINUTES)
        )

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        return await self._request("GET", url, params=params)

    async def post(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        return await self._request("POST", url, params=params, json=json)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        client = self._ensure_client()
        await self.get_valid_token()

        try:
            response = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as error:
            response_payload = self._safe_response_payload(error.response)
            error_summary = self._extract_error_summary(response_payload)

            log.error(
                "Zoho Analytics respondio con error HTTP: "
                f"{error} | payload={response_payload}"
            )

            if error_summary == "INVALID_OAUTHSCOPE":
                raise AppError(
                    "El token de Zoho Analytics no tiene los permisos requeridos.",
                    status_code=HTTPStatus.UNAUTHORIZED,
                    error_code="zoho_invalid_scope",
                    details=(
                        "Zoho devolvio INVALID_OAUTHSCOPE. "
                        "Regenera el refresh token con los scopes configurados en ZHA_SCOPE. "
                        f"Payload: {response_payload}"
                    ),
                ) from error

            raise AppError(
                "Zoho Analytics devolvio un error al procesar la solicitud.",
                status_code=error.response.status_code,
                error_code="zoho_request_error",
                details=(
                    "HTTPStatusError en request a Zoho Analytics. "
                    f"Payload: {response_payload}"
                ),
            ) from error

        except httpx.RequestError as error:
            log.error(f"Error de red llamando a Zoho Analytics: {error}")
            raise AppError(
                "No fue posible comunicarse con Zoho Analytics.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_request_error",
                details=f"RequestError en request a Zoho Analytics: {error}",
            ) from error

    def _update_tokens(self, token_data: Mapping[str, Any]) -> None:
        self.access_token = (token_data.get("access_token") or "").strip() or None
        self.token_type = token_data.get("token_type")
        self.expires_in = self._parse_int(token_data.get("expires_in")) or 3600
        self.api_domain = token_data.get("api_domain")
        self.scope = token_data.get("scope") or self.scope
        self.token_expiry = datetime.now() + timedelta(seconds=self.expires_in)
        self.save_tokens()

    def _ensure_client(self) -> httpx.AsyncClient:
        if self.client is None:
            raise AppError(
                "La conexion con Zoho Analytics no esta disponible.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_client_not_initialized",
                details="El cliente HTTP para Zoho Analytics no esta inicializado.",
            )

        return self.client

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise AppError(
                "La autenticacion con Zoho Analytics no esta disponible.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                error_code="zoho_access_token_missing",
                details="No hay access token disponible para Zoho Analytics.",
            )

        return {
            "ZANALYTICS-ORGID": settings.ZHA_ORGID,
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _workspace_url(self, workspace_id: str) -> str:
        return f"{settings.ZHA_API_URL.rstrip('/')}/{workspace_id}"

    def _bulk_view_data_url(self, workspace_id: str, view_id: str) -> str:
        return f"{settings.ZHA_API_BULK_URL.rstrip('/')}/{workspace_id}/views/{view_id}/data"

    def _safe_response_payload(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    def _extract_error_summary(self, payload: Any) -> str | None:
        if not isinstance(payload, Mapping):
            return None

        summary = payload.get("summary")
        if isinstance(summary, str):
            return summary

        return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value or not isinstance(value, str):
            return None

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _parse_int(self, value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


zoho_analytics = ZohoAnalyticsClient()
