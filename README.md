# Data Bridge

API backend minimalista con FastAPI para conectar PostgreSQL con Zoho Analytics y permitir sincronizacion progresiva de datos entre ambos sistemas.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Zoho Analytics](https://img.shields.io/badge/Zoho%20Analytics-Bulk%20API-C8202F?style=for-the-badge)

## Vision

Data Bridge centraliza integraciones entre PostgreSQL y Zoho Analytics con una arquitectura simple, explicita y segura. El proyecto evita capas innecesarias y separa estrictamente responsabilidades entre API, servicios de negocio, base de datos, integraciones externas, configuracion, logs y manejo de errores.

Capacidades actuales:

- API FastAPI versionada bajo `/api/v1`.
- Startup y shutdown centralizados con `lifespan`.
- Conexion asincrona a PostgreSQL con SQLAlchemy y `asyncpg`.
- Cliente HTTP asincrono para Zoho Analytics con `httpx`.
- Refresh y persistencia local de tokens OAuth de Zoho.
- Preview de datos desde Zoho Analytics.
- Preview seguro de tablas PostgreSQL sin SQL libre desde requests externas.
- Sincronizacion Zoho Analytics -> PostgreSQL mediante upsert controlado.
- Manejo global de errores con respuestas seguras.
- Logs compartidos con redaccion de secretos.
- Documentacion automatica deshabilitada en produccion.
- Dockerfile y Docker Compose para despliegue basico.

## Tabla De Contenido

- [Arquitectura](#arquitectura)
- [Estructura Del Proyecto](#estructura-del-proyecto)
- [Stack Tecnico](#stack-tecnico)
- [Instalacion Local](#instalacion-local)
- [Configuracion](#configuracion)
- [Ejecucion](#ejecucion)
- [Docker](#docker)
- [Endpoints](#endpoints)
- [Flujos Principales](#flujos-principales)
- [Manejo De Errores](#manejo-de-errores)
- [Logs](#logs)
- [Seguridad](#seguridad)
- [Troubleshooting](#troubleshooting)
- [Estado Actual](#estado-actual)
- [Roadmap](#roadmap)
- [Desarrollo](#desarrollo)
- [Licencia](#licencia)

## Arquitectura

La estructura actual es la base obligatoria de crecimiento del proyecto. La regla principal es mantener el backend pequeno, legible y sin abstracciones prematuras.

```txt
Cliente HTTP / Postman / Swagger en desarrollo
        |
        v
main.py
        |
        +-- ErrorHandlerMiddleware
        +-- exception handlers seguros
        +-- app.api.v1.router
              |
              +-- /health -> app.api.v1.health
              |
              +-- /sync   -> app.modules.sync.router
                               |
                               v
                         app.modules.sync.service
                               |
                               +-- app.integrations.zoho_analytics
                               +-- app.db.postgresql

Startup / Shutdown:
main.py -> app.lifespan -> PostgreSQL + Zoho Analytics

Configuracion:
app.config -> variables de entorno / .env

Logs:
app.logging.log -> salida visual y sanitizada en terminal
```

Referencia visual:

```txt
docs/arquitecture-diagram.png
```

## Estructura Del Proyecto

```txt
data-bridge-app/
├── main.py
├── requirements.txt
├── README.md
├── AGENTS.md
├── skills-lock.json
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── docs/
│   └── arquitecture-diagram.png
└── app/
    ├── config.py
    ├── lifespan.py
    ├── logging.py
    ├── api/
    │   └── v1/
    │       ├── router.py
    │       └── health.py
    ├── db/
    │   └── postgresql.py
    ├── integrations/
    │   └── zoho_analytics.py
    ├── middleware/
    │   └── error_handler.py
    └── modules/
        └── sync/
            ├── router.py
            ├── schemas.py
            └── service.py
```

| Archivo | Responsabilidad |
| --- | --- |
| `main.py` | Crea la app FastAPI, desactiva docs en produccion, registra middleware, exception handlers y routers. |
| `app/config.py` | Configuracion central con `pydantic-settings`. No contiene logica de negocio. |
| `app/lifespan.py` | Inicializa y cierra PostgreSQL y Zoho Analytics durante startup/shutdown. |
| `app/api/v1/router.py` | Router principal de API v1. |
| `app/api/v1/health.py` | Health check liviano. |
| `app/db/postgresql.py` | Engine, pool, sesiones, health check y cierre de PostgreSQL. |
| `app/integrations/zoho_analytics.py` | Cliente Zoho Analytics: OAuth, HTTP, Bulk Export, polling, timeouts y errores de integracion. |
| `app/middleware/error_handler.py` | Manejo global de errores y respuestas seguras. |
| `app/logging.py` | Logger compartido con redaccion de secretos. |
| `app/modules/sync/router.py` | Endpoints HTTP del modulo `sync`. |
| `app/modules/sync/schemas.py` | Contratos Pydantic de requests y responses. |
| `app/modules/sync/service.py` | Orquestacion de negocio para preview y sincronizacion. |

## Stack Tecnico

| Dependencia | Uso |
| --- | --- |
| `fastapi` | Framework web asincrono. |
| `uvicorn[standard]` | Servidor ASGI. |
| `pydantic-settings` | Carga de configuracion desde variables de entorno. |
| `SQLAlchemy` | Engine y sesiones asincronas para PostgreSQL. |
| `asyncpg` | Driver PostgreSQL asincrono. |
| `httpx` | Cliente HTTP asincrono para Zoho Analytics. |
| `rich` | Logs visuales en terminal. |
| `pandas` | Dependencia disponible para trabajo futuro con dataframes. |

## Instalacion Local

Requisitos:

- Python 3.12 o superior.
- Acceso a PostgreSQL.
- Credenciales OAuth de Zoho Analytics.
- Workspace y vista real en Zoho Analytics.

Crear entorno virtual:

```bash
python -m venv .venv
```

Activar entorno virtual en Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear archivo local de variables:

```powershell
Copy-Item .env.example .env
```

`.env` esta ignorado por Git y nunca debe subirse al repositorio.

## Configuracion

La configuracion se carga desde `.env` mediante `app/config.py`.

### Servidor

| Variable | Descripcion |
| --- | --- |
| `APP_HOST` | Host donde escucha la app. |
| `APP_PORT` | Puerto HTTP. |
| `APP_NAME` | Nombre de la aplicacion. |
| `APP_ENV` | Entorno. Usar `production` en despliegue. |
| `DB_REQUIRED` | Bandera declarada para control futuro. PostgreSQL se inicializa actualmente en lifespan. |

En `APP_ENV=production`, FastAPI no expone `/docs`, `/redoc` ni `/openapi.json`.

### PostgreSQL

| Variable | Descripcion |
| --- | --- |
| `PG_HOST_MV3` | Host de PostgreSQL. |
| `PG_PORT_MV3` | Puerto. Por defecto `5432`. |
| `PG_DATABASE_MV3` | Base de datos. |
| `PG_USERNAME_MV3` | Usuario. |
| `PG_PASSWORD_MV3` | Password. No debe exponerse. |
| `PG_SCHEMA_MV3` | Schema usado como `search_path`. |

La URL se construye internamente con este formato:

```txt
postgresql+asyncpg://<usuario>:<password>@<host>:<puerto>/<database>
```

Usuario y password se escapan con `quote_plus` para soportar caracteres especiales.

### Zoho Analytics

| Variable | Descripcion |
| --- | --- |
| `ZH_TOKEN_URL` | Endpoint OAuth para refrescar access token. |
| `ZH_TOKEN_ID` | Client ID OAuth. |
| `ZH_TOKEN_SECRET` | Client secret OAuth. No debe exponerse. |
| `ZHA_REFRESH_TOKEN` | Refresh token de Zoho Analytics. No debe exponerse. |
| `ZHC_REFRESH_TOKEN` | Refresh token alternativo reservado. |
| `ZH_GRANT_TYPE` | Tipo de grant OAuth. Por defecto `refresh_token`. |
| `ZH_ACCESS_TOKEN` | Access token inicial opcional. |
| `ZH_TOKEN_EXPIRY` | Fecha de expiracion inicial opcional en formato ISO. |
| `ZHA_API_URL` | Base URL REST v2 de workspaces. |
| `ZHA_API_BULK_URL` | Base URL REST v2 Bulk API de workspaces. |
| `ZHA_ORGID` | Organization ID usado en header `ZANALYTICS-ORGID`. |
| `ZHA_WS_DEFAUL` | Workspace por defecto. |
| `ZHA_WS_AUTOMATIC` | Workspace adicional reservado. |
| `ZHA_FILE_JOBID_JSON` | Ruta reservada para job IDs locales. |
| `ZHA_FILE_TOKEN_JSON` | Ruta local donde se persisten tokens de Zoho. |
| `ZHA_HEALTHCHECK_VIEW_ID` | Vista opcional para validar Zoho en startup. |
| `ZHA_SCOPE` | Scopes OAuth requeridos. |
| `ZOHO_REQUIRED` | Si es `true`, startup valida Zoho. Si es `false`, lo omite. |

Scopes usados actualmente:

```txt
ZohoAnalytics.metadata.read ZohoAnalytics.data.read ZohoAnalytics.data.create ZohoAnalytics.data.update ZohoAnalytics.data.delete
```

### Tokens Locales

El cliente Zoho persiste tokens en `ZHA_FILE_TOKEN_JSON`. El valor habitual es:

```txt
data/tokens/za_tokens.json
```

Ese path esta protegido por `.gitignore`:

```txt
data/tokens/*.json
```

## Ejecucion

Desarrollo:

```bash
python -m uvicorn main:app --reload
```

Alternativa directa:

```bash
python main.py
```

URLs locales por defecto:

| Recurso | URL |
| --- | --- |
| API | `http://127.0.0.1:8000` |
| Swagger UI en desarrollo | `http://127.0.0.1:8000/docs` |
| OpenAPI JSON en desarrollo | `http://127.0.0.1:8000/openapi.json` |
| Health check | `http://127.0.0.1:8000/api/v1/health` |

## Docker

Construir imagen:

```bash
docker build -t data-bridge-api:latest .
```

Ejecutar con Docker Compose:

```bash
docker compose up -d --build
```

El `docker-compose.yml`:

- Usa `.env` como fuente de variables.
- Fuerza `APP_ENV=production`.
- Publica el puerto `8000`.
- Persiste tokens locales en el volumen `data_bridge_tokens`.
- Incluye healthcheck contra `/api/v1/health`.

Ver logs:

```bash
docker compose logs -f api
```

Detener:

```bash
docker compose down
```

## Endpoints

### GET `/api/v1/health`

Health check basico.

Response:

```json
{
  "status": "ok",
  "service": "data-bridge"
}
```

### POST `/api/v1/sync/preview/zoho`

Previsualiza datos desde una vista real de Zoho Analytics usando Bulk Export API.

Request:

```json
{
  "view_id": "123456789012345678",
  "workspace_id": "123456789012345678",
  "limit": 10,
  "offset": 0
}
```

Campos:

| Campo | Tipo | Requerido | Descripcion |
| --- | --- | --- | --- |
| `view_id` | `string` | Si | ID real de la vista de Zoho Analytics. |
| `workspace_id` | `string` o `null` | No | Si se omite, usa `ZHA_WS_DEFAUL`. |
| `limit` | `integer` o `null` | No | Maximo de filas a devolver. |
| `offset` | `integer` | No | Filas a omitir antes del preview. |

Response exitoso:

```json
{
  "success": true,
  "source": "zoho_analytics",
  "count": 120,
  "limit": 10,
  "offset": 0,
  "columns": ["Column A", "Column B"],
  "rows": [
    {
      "Column A": "value",
      "Column B": 123
    }
  ],
  "workspace_id": "123456789012345678",
  "view_id": "123456789012345678",
  "target_table": null
}
```

### POST `/api/v1/sync/preview/postgresql`

Previsualiza una tabla PostgreSQL del schema configurado. El endpoint no acepta SQL libre; solo acepta nombre de tabla validado.

Request:

```json
{
  "target_table": "customers",
  "limit": 10,
  "offset": 0
}
```

Campos:

| Campo | Tipo | Requerido | Descripcion |
| --- | --- | --- | --- |
| `target_table` | `string` | Si | Tabla PostgreSQL a previsualizar. Debe ser identificador valido. |
| `limit` | `integer` o `null` | No | Maximo de filas a devolver. |
| `offset` | `integer` | No | Filas a omitir antes del preview. |

Response exitoso:

```json
{
  "success": true,
  "source": "postgresql",
  "count": 120,
  "limit": 10,
  "offset": 0,
  "columns": ["id", "email"],
  "rows": [
    {
      "id": 1,
      "email": "user@example.com"
    }
  ],
  "workspace_id": null,
  "view_id": null,
  "target_table": "customers"
}
```

### POST `/api/v1/sync/zoho-to-postgresql`

Sincroniza datos desde una vista de Zoho Analytics hacia una tabla PostgreSQL mediante upsert.

Request:

```json
{
  "workspace_id": "123456789012345678",
  "view_id": "123456789012345678",
  "target_table": "customers",
  "upsert_key": ["email"],
  "column_mapping": {
    "Customer Email": "email",
    "Customer Name": "name"
  }
}
```

Reglas principales:

- `target_table`, columnas PostgreSQL y `upsert_key` deben ser identificadores validos.
- La tabla debe existir en el schema configurado.
- Las columnas mapeadas deben existir en PostgreSQL.
- `upsert_key` debe coincidir con una PK o UNIQUE existente.
- No se recibe SQL libre desde el cliente.
- El endpoint usa transacciones anidadas por fila para contabilizar errores sin detener todo el lote.

Response exitoso:

```json
{
  "success": true,
  "inserted": 10,
  "updated": 25,
  "total": 35,
  "errors_count": 0,
  "cant_row_zoho": 35,
  "cant_row_pg": 250
}
```

## Flujos Principales

### Zoho Analytics

`app/integrations/zoho_analytics.py` mantiene el cliente HTTP y la autenticacion OAuth.

1. `connect()` crea un `httpx.AsyncClient` con timeout total de `120s` y timeout de conexion de `10s`.
2. `load_tokens()` carga tokens persistidos desde disco.
3. `get_valid_token()` valida expiracion con buffer de 5 minutos.
4. `refresh_access_token()` refresca tokens si es necesario.
5. `export_view_data(workspace_id, view_id)` crea un export job en Zoho Bulk API.
6. Si Zoho no entrega `downloadUrl` inmediatamente, se hace polling cada `1s`.
7. El maximo actual es `1200` polls, equivalente a 20 minutos.
8. La descarga JSON se normaliza a `list[dict[str, Any]]`.

Si Zoho responde `EXCEEDING_USR_PLN_API_FREQ_COUNT`, el cliente espera `10s` y reintenta hasta `2` veces.

### PostgreSQL

`app/db/postgresql.py` centraliza conexion y sesiones.

1. `connect()` crea engine asincrono con `pool_pre_ping=True`.
2. Se configura `pool_size=5` y `max_overflow=10`.
3. Se establece `search_path` con `PG_SCHEMA_MV3`.
4. `check_connection()` ejecuta `SELECT 1`.
5. `get_session()` expone sesiones asincronas para dependencias FastAPI.
6. `disconnect()` cierra el pool con `engine.dispose()`.

## Manejo De Errores

El proyecto usa `AppError`, `ErrorHandlerMiddleware` y exception handlers globales.

Formato de error:

```json
{
  "success": false,
  "error": {
    "code": "request_error",
    "message": "No fue posible procesar la solicitud."
  }
}
```

Comportamiento actual:

- En produccion, `AppError` devuelve mensaje generico al cliente.
- Errores inesperados devuelven `internal_server_error` sin stack trace.
- Errores de validacion devuelven `validation_error` sin detallar campos internos.
- `HTTPException` y rutas inexistentes se transforman en JSON seguro.
- Los detalles tecnicos no se exponen al cliente.

## Logs

`app/logging.py` centraliza la salida de terminal con `rich`.

Metodos disponibles:

| Metodo | Uso |
| --- | --- |
| `log.info()` | Informacion general. |
| `log.ok()` | Operaciones exitosas. |
| `log.warn()` | Advertencias recuperables. |
| `log.error()` | Errores. |
| `log.step()` | Pasos de ejecucion. |
| `log.bloque_inicio()` | Inicio visual de un bloque. |
| `log.bloque_fin()` | Cierre visual de un bloque. |
| `log.table()` | Preview tabular en terminal. |

El logger redacta patrones sensibles antes de imprimir:

- `Authorization`
- `access_token`
- `refresh_token`
- `client_secret`
- `api_key`
- `password`
- `secret`
- `database_url`
- URLs PostgreSQL
- secretos en query params

## Seguridad

Reglas activas:

- Nunca subir `.env`.
- Nunca subir `data/tokens/*.json`.
- Nunca exponer tokens de Zoho.
- Nunca exponer passwords ni `DATABASE_URL`.
- No devolver errores internos crudos al cliente.
- No registrar payloads externos completos de Zoho.
- No registrar excepciones SQLAlchemy crudas.
- No permitir SQL libre recibido desde requests externas.
- Validar entradas con Pydantic.
- Deshabilitar documentacion automatica en `APP_ENV=production`.

CORS no esta configurado actualmente. Si se agrega, debe usarse allowlist explicita por entorno y evitar `*` en produccion.

## Troubleshooting

### `/docs` no aparece

Causa: `APP_ENV=production` deshabilita Swagger UI, ReDoc y OpenAPI JSON.

Solucion: usar `APP_ENV=development` solo en entorno local.

### Zoho responde `URL_RULE_NOT_CONFIGURED`

Causa: `workspace_id` o `view_id` no corresponden a IDs reales.

Solucion: reemplazar los valores de ejemplo por IDs reales de Zoho Analytics.

### Zoho responde `EXCEEDING_USR_PLN_API_FREQ_COUNT`

Causa: demasiados requests a Zoho en poco tiempo.

Solucion: el cliente ya espera `10s` y reintenta hasta `2` veces. Si persiste, esperar antes de volver a probar.

### Zoho responde `INVALID_OAUTHSCOPE`

Causa: el refresh token no tiene los permisos necesarios.

Solucion: regenerar el refresh token con los scopes configurados en `ZHA_SCOPE`.

### PostgreSQL no conecta en startup

Revisar:

- `PG_HOST_MV3`
- `PG_PORT_MV3`
- `PG_DATABASE_MV3`
- `PG_USERNAME_MV3`
- `PG_PASSWORD_MV3`
- `PG_SCHEMA_MV3`
- Acceso de red o firewall a la base de datos

### `ModuleNotFoundError`

Causa: dependencias no instaladas o entorno virtual no activo.

Solucion:

```bash
pip install -r requirements.txt
```

## Estado Actual

Implementado:

- Bootstrap FastAPI.
- Configuracion central con `.env`.
- Middleware y exception handlers seguros.
- Logger compartido con redaccion de secretos.
- Lifecycle de app.
- Conexion PostgreSQL asincrona.
- Cliente Zoho Analytics.
- Refresh token OAuth.
- Persistencia local de tokens.
- Health check basico.
- Router v1.
- Modulo `sync`.
- `POST /api/v1/sync/preview/zoho`.
- `POST /api/v1/sync/preview/postgresql`.
- `POST /api/v1/sync/zoho-to-postgresql`.
- Zoho Bulk Export con polling, timeouts y rate limit handling.
- Dockerfile y Docker Compose.
- Reglas de arquitectura y colaboracion en `AGENTS.md`.
- Skills locales registradas en `skills-lock.json`.

No implementado todavia:

- Autenticacion JWT.
- RBAC.
- Jobs en background.
- Workers, Celery o Redis.
- Tests automatizados.
- CI/CD.
- Sincronizacion PostgreSQL -> Zoho Analytics.
- Modelos ORM propios.
- Repositories por modulo.

## Roadmap

Siguientes pasos naturales:

1. Agregar tests automatizados para errores, preview y sincronizacion.
2. Agregar CORS con allowlist explicita cuando exista frontend real.
3. Proteger endpoints con autenticacion cuando exista una necesidad concreta.
4. Proponer jobs en background para sincronizaciones largas.
5. Implementar sincronizacion PostgreSQL -> Zoho Analytics.
6. Agregar CI cuando exista suite de tests estable.

## Desarrollo

Antes de modificar el proyecto, leer `AGENTS.md`.

Principios obligatorios:

- Mantener el proyecto minimalista.
- No crear carpetas, capas ni dependencias sin necesidad concreta.
- No mezclar logica HTTP, negocio, PostgreSQL y Zoho.
- Una clase service por modulo.
- Cada ruta debe corresponder a exactamente un metodo publico del service.
- No crear helpers dentro de services salvo instruccion explicita.
- No modificar contracts existentes sin autorizacion explicita.

### Commits

Formato:

```txt
type(scope): message
```

Ejemplos:

- `feat(sync): add zoho to postgresql service`
- `security(api): harden error handling`
- `docs(readme): update project documentation`

El comando `do-commit` esta definido en `AGENTS.md` y ejecuta el flujo de ramas, commits, merges, push y limpieza segun las reglas del repositorio.

## Licencia

Este proyecto usa licencia MIT.

Copyright (c) 2026 Juan Miguel Leon Gomez, Ingeniero Informatico.

Consulta `LICENSE` para ver los terminos completos.
