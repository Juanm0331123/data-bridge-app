# Data Bridge

Backend minimalista con FastAPI para conectar PostgreSQL con Zoho Analytics y habilitar, de forma progresiva, sincronizacion de datos en ambos sentidos.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Zoho Analytics](https://img.shields.io/badge/Zoho%20Analytics-Bulk%20API-C8202F?style=for-the-badge)

## Vision

Data Bridge es una API backend clara, segura y extensible para mover datos entre PostgreSQL y Zoho Analytics sin mezclar responsabilidades.

El proyecto ya cuenta con:

- API FastAPI con versionamiento `/api/v1`.
- Startup y shutdown centralizados con `lifespan`.
- Conexion asincrona a PostgreSQL con SQLAlchemy y `asyncpg`.
- Cliente HTTP asincrono para Zoho Analytics con `httpx`.
- Refresh y persistencia local de tokens OAuth de Zoho.
- Middleware centralizado para respuestas de error seguras.
- Logger compartido con salida visual en terminal usando `rich`.
- Modulo funcional `sync` para preview de datos desde Zoho Analytics.
- Optimizacion del flujo Zoho Bulk Export con polling, timeouts, reutilizacion HTTP y manejo de rate limits.

## Tabla De Contenido

- [Arquitectura](#arquitectura)
- [Estructura Del Proyecto](#estructura-del-proyecto)
- [Stack Tecnico](#stack-tecnico)
- [Instalacion Local](#instalacion-local)
- [Configuracion](#configuracion)
- [Ejecucion](#ejecucion)
- [Endpoints](#endpoints)
- [Flujo Zoho Analytics](#flujo-zoho-analytics)
- [Flujo PostgreSQL](#flujo-postgresql)
- [Manejo De Errores](#manejo-de-errores)
- [Logs](#logs)
- [Seguridad](#seguridad)
- [Estado Actual](#estado-actual)
- [Versionamiento Reciente](#versionamiento-reciente)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

## Arquitectura

La arquitectura actual separa responsabilidades por archivo y por modulo. La regla principal es mantener el backend simple, explicito y sin capas innecesarias.

```txt
Cliente HTTP / Swagger / Postman
        |
        v
main.py
        |
        v
app.api.v1.router
        |
        +-- /health -> app.api.v1.health
        |
        +-- /sync   -> app.modules.sync.router
                         |
                         v
                   app.modules.sync.service
                         |
                         v
              app.integrations.zoho_analytics

Startup / Shutdown:
main.py -> app.lifespan -> PostgreSQL + Zoho Analytics

Errores:
AppError -> ErrorHandlerMiddleware -> respuesta segura al cliente

Logs:
app.logging.log -> salida visual en terminal
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
| `main.py` | Crea la app FastAPI, registra middleware, monta routers y permite levantar Uvicorn. |
| `app/config.py` | Carga configuracion desde `.env` con `pydantic-settings`. |
| `app/lifespan.py` | Inicializa y cierra PostgreSQL y Zoho Analytics durante startup/shutdown. |
| `app/api/v1/router.py` | Router principal de API v1. Registra `health` y `sync`. |
| `app/api/v1/health.py` | Health check liviano de la API. |
| `app/db/postgresql.py` | Engine, pool, session factory, health check y cierre de PostgreSQL. |
| `app/integrations/zoho_analytics.py` | Cliente Zoho Analytics: OAuth, requests HTTP, Bulk Export, polling, parsing y errores de integracion. |
| `app/middleware/error_handler.py` | Manejo centralizado de errores seguros para el cliente. |
| `app/logging.py` | Logger visual compartido para terminal. |
| `app/modules/sync/router.py` | Endpoints HTTP del modulo de sincronizacion. |
| `app/modules/sync/schemas.py` | Contratos Pydantic de requests y responses. |
| `app/modules/sync/service.py` | Orquestacion de negocio para preview de datos. |

## Stack Tecnico

| Dependencia | Uso |
| --- | --- |
| `fastapi` | Framework web asincrono. |
| `uvicorn[standard]` | Servidor ASGI para desarrollo y ejecucion. |
| `pydantic-settings` | Configuracion desde variables de entorno. |
| `SQLAlchemy` | Engine y sesiones asincronas para PostgreSQL. |
| `asyncpg` | Driver PostgreSQL asincrono. |
| `httpx` | Cliente HTTP asincrono para Zoho Analytics. |
| `rich` | Logs visuales en terminal. |
| `pandas` | Dependencia disponible para trabajo futuro con dataframes. |

## Instalacion Local

Requisitos recomendados:

- Python 3.12 o superior.
- Acceso a una base PostgreSQL.
- Credenciales OAuth de Zoho Analytics.
- Un workspace y una vista real en Zoho Analytics.

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

Importante: `.env` esta ignorado por Git y no debe subirse al repositorio.

## Configuracion

La configuracion se carga desde `.env` mediante `app/config.py`.

### Servidor

| Variable | Descripcion | Ejemplo |
| --- | --- | --- |
| `APP_HOST` | Host donde escucha Uvicorn. | `127.0.0.1` |
| `APP_PORT` | Puerto HTTP. | `8000` |
| `APP_NAME` | Nombre mostrado en FastAPI y logs. | `Data Bridge` |
| `APP_ENV` | Entorno de ejecucion. En `development` activa reload cuando se ejecuta `main.py`. | `development` |
| `DB_REQUIRED` | Bandera declarada para control futuro de base de datos. Actualmente PostgreSQL se inicializa en lifespan. | `false` |

### PostgreSQL

| Variable | Descripcion |
| --- | --- |
| `PG_HOST_MV3` | Host de PostgreSQL. |
| `PG_PORT_MV3` | Puerto de PostgreSQL. Por defecto `5432`. |
| `PG_DATABASE_MV3` | Base de datos. |
| `PG_USERNAME_MV3` | Usuario. |
| `PG_PASSWORD_MV3` | Password. No debe exponerse. |
| `PG_SCHEMA_MV3` | Schema usado como `search_path`. |

La URL se construye internamente asi:

```txt
postgresql+asyncpg://<usuario>:<password>@<host>:<puerto>/<database>
```

`app/config.py` escapa usuario y password con `quote_plus` para soportar caracteres especiales.

### Zoho Analytics

| Variable | Descripcion |
| --- | --- |
| `ZH_TOKEN_URL` | Endpoint OAuth para refrescar access token. |
| `ZH_TOKEN_ID` | Client ID OAuth. |
| `ZH_TOKEN_SECRET` | Client secret OAuth. No debe exponerse. |
| `ZHA_REFRESH_TOKEN` | Refresh token de Zoho Analytics. No debe exponerse. |
| `ZHC_REFRESH_TOKEN` | Refresh token alternativo reservado. |
| `ZH_GRANT_TYPE` | Tipo de grant OAuth. Por defecto `refresh_token`. |
| `ZH_ACCESS_TOKEN` | Access token inicial opcional. Normalmente se refresca y persiste. |
| `ZH_TOKEN_EXPIRY` | Fecha de expiracion inicial opcional en formato ISO. |
| `ZHA_API_URL` | Base URL REST v2 de workspaces. |
| `ZHA_API_BULK_URL` | Base URL REST v2 Bulk API de workspaces. |
| `ZHA_ORGID` | Organization ID usado en header `ZANALYTICS-ORGID`. |
| `ZHA_WS_DEFAUL` | Workspace por defecto usado si el request no envia `workspace_id`. |
| `ZHA_WS_AUTOMATIC` | Workspace adicional disponible para futuras integraciones. |
| `ZHA_FILE_JOBID_JSON` | Ruta reservada para job IDs locales. |
| `ZHA_FILE_TOKEN_JSON` | Ruta local donde se persisten tokens de Zoho. |
| `ZHA_HEALTHCHECK_VIEW_ID` | Vista opcional para validar Zoho en startup con Bulk Export real. |
| `ZHA_SCOPE` | Scopes OAuth requeridos para leer y escribir data en Zoho Analytics. |
| `ZOHO_REQUIRED` | Si es `true`, el startup valida Zoho. Si es `false`, omite la validacion Zoho. |

Scopes usados actualmente:

```txt
ZohoAnalytics.metadata.read ZohoAnalytics.data.read ZohoAnalytics.data.create ZohoAnalytics.data.update ZohoAnalytics.data.delete
```

### Tokens Locales

El cliente Zoho persiste tokens en el path configurado por `ZHA_FILE_TOKEN_JSON`. El valor por defecto del proyecto es:

```txt
data/tokens/za_tokens.json
```

Ese path esta protegido por `.gitignore`:

```txt
data/tokens/*.json
```

No subas tokens reales al repositorio.

## Ejecucion

Comando recomendado:

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
| Swagger UI | `http://127.0.0.1:8000/docs` |
| OpenAPI JSON | `http://127.0.0.1:8000/openapi.json` |
| Health check | `http://127.0.0.1:8000/api/v1/health` |

## Endpoints

### GET `/api/v1/health`

Health check basico de la API.

Response:

```json
{
  "status": "ok",
  "service": "data-bridge"
}
```

### POST `/api/v1/sync/preview/zoho`

Previsualiza datos desde una vista real de Zoho Analytics usando Bulk Export API.

Request body:

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
| `workspace_id` | `string` o `null` | No | ID real del workspace. Si se omite, usa `ZHA_WS_DEFAUL`. |
| `limit` | `integer` o `null` | No | Maximo de filas a devolver. Debe ser mayor o igual a `1`. |
| `offset` | `integer` | No | Fila inicial para paginar el preview. Debe ser mayor o igual a `0`. |

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

Notas:

- Swagger muestra IDs de ejemplo, pero debes reemplazarlos por IDs reales de Zoho.
- Si envias `string` como `workspace_id` o `view_id`, Zoho respondera que la URL no existe.
- `limit` y `offset` se aplican despues de descargar la data exportada desde Zoho.
- `count` representa el total de filas devueltas por Zoho antes del corte de preview.

## Flujo Zoho Analytics

El cliente esta en `app/integrations/zoho_analytics.py` y usa `httpx.AsyncClient`.

### Startup

1. `lifespan` llama `zoho_analytics.connect()` si `ZOHO_REQUIRED=true`.
2. Se crea un cliente HTTP con timeout total de `120s` y timeout de conexion de `10s`.
3. Se configuran limites HTTP: `max_connections=10`, `max_keepalive_connections=5`, `keepalive_expiry=30s`.
4. Se cargan tokens persistidos desde `ZHA_FILE_TOKEN_JSON`.
5. Si no hay token persistido, se usa `ZH_ACCESS_TOKEN` si existe.
6. `check_connection()` valida OAuth y, si existe `ZHA_HEALTHCHECK_VIEW_ID`, valida una exportacion real.

### Token OAuth

1. `get_valid_token()` revisa si el token en memoria sigue vigente.
2. Si no esta vigente, intenta cargar tokens desde disco.
3. Si el token expira en menos de 5 minutos, refresca con `ZHA_REFRESH_TOKEN`.
4. Los tokens nuevos se guardan en `data/tokens/za_tokens.json` o en el path configurado.

### Export View Data

`export_view_data(workspace_id, view_id)` mantiene la firma publica actual y ejecuta:

1. Crea un export job en Zoho Bulk API.
2. Extrae `jobId` desde la respuesta.
3. Si Zoho ya devuelve `downloadUrl`, evita polling innecesario.
4. Si no hay `downloadUrl`, consulta el estado del job cada `1s`.
5. El maximo actual es `1200` polls, equivalente a 20 minutos.
6. Si `jobCode` indica fallo (`1003` o `1005`), corta rapido con error seguro.
7. Descarga el archivo JSON exportado desde `downloadUrl`.
8. Normaliza filas en formato `list[dict[str, Any]]`.
9. Registra timings de create, wait, download, parse y total.

### Rate Limit

Si Zoho responde `EXCEEDING_USR_PLN_API_FREQ_COUNT`, el cliente:

- Espera `10s`.
- Reintenta hasta `2` veces.
- Registra el evento en terminal.
- Devuelve error seguro si Zoho sigue limitando.

## Flujo PostgreSQL

La conexion esta en `app/db/postgresql.py`.

Durante startup:

1. `postgres_db.connect()` crea el engine asincrono.
2. Se configura `pool_pre_ping=True` para validar conexiones del pool.
3. Se usa `pool_size=5` y `max_overflow=10`.
4. Se establece `search_path` con `PG_SCHEMA_MV3`.
5. `check_connection()` ejecuta `SELECT 1`.

Durante shutdown:

1. `postgres_db.disconnect()` hace `engine.dispose()`.
2. Limpia `engine` y `session_factory`.

Actualmente no hay endpoint publico que lea o escriba PostgreSQL. La infraestructura ya esta lista para futuros servicios.

## Manejo De Errores

El middleware `ErrorHandlerMiddleware` transforma errores internos en respuestas seguras.

Formato de error:

```json
{
  "success": false,
  "error": {
    "code": "zoho_request_error",
    "message": "Zoho Analytics devolvio un error al procesar la solicitud."
  }
}
```

Reglas actuales:

- Los detalles reales se registran en terminal.
- El cliente recibe mensajes sanitizados.
- `AppError` permite controlar `status_code`, `error_code`, `message` y `details`.
- Errores inesperados devuelven `500` con `internal_server_error`.

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

## Seguridad

Reglas activas del proyecto:

- Nunca subir `.env`.
- Nunca exponer tokens de Zoho.
- Nunca exponer `DATABASE_URL`.
- Nunca exponer passwords de PostgreSQL.
- Usar variables de entorno para secretos.
- Persistir tokens solo en `data/tokens/*.json`, path ignorado por Git.
- No devolver errores internos crudos al cliente.
- Registrar detalles reales solo en terminal.
- Validar requests con Pydantic.
- No permitir SQL libre desde requests externas.

## Estado Actual

Implementado:

- Bootstrap FastAPI.
- Configuracion central con `.env`.
- Middleware de errores.
- Logger compartido.
- Lifecycle de app.
- Conexion PostgreSQL asincrona.
- Cliente Zoho Analytics.
- Refresh token OAuth.
- Persistencia local de tokens.
- Health check basico.
- Router v1.
- Modulo `sync`.
- Endpoint `POST /api/v1/sync/preview/zoho`.
- Zoho Bulk Export con polling y descarga.
- Manejo de rate limit de Zoho.
- Ejemplos OpenAPI para evitar payloads `string` en Swagger.
- Reglas de arquitectura y colaboracion en `AGENTS.md`.
- Skills locales registradas en `skills-lock.json`.

No implementado todavia:

- Autenticacion JWT.
- RBAC.
- Jobs en background.
- Workers, Celery o Redis.
- Tests automatizados.
- CI/CD.
- Endpoint para preview desde PostgreSQL, aunque existe schema base `PreviewPostgresTableRequest`.
- Sincronizacion completa Zoho -> PostgreSQL.
- Sincronizacion completa PostgreSQL -> Zoho.
- Modelos ORM propios.
- Repositories por modulo.

## Versionamiento Reciente

Historial reciente relevante:

```txt
45342de Merge branch 'temp/zoho-preview-sync-versioning'
a5a9b65 feat(sync): add zoho preview endpoint
4329596 perf(zoho): optimize bulk export preview
014c1f1 docs(agents): add sync module constraints
93d0f8a Merge branch 'chore/agents-skills'
2f9e9da chore(agents): add local skills files
fef8d14 Merge branch 'feat/zoho-integration'
9f23924 feat(zoho): add analytics integration lifecycle
```

La rama temporal usada para el ultimo versionamiento fue:

```txt
temp/zoho-preview-sync-versioning
```

Esa rama ya fue mergeada a `main` y `main` fue pusheada a `origin/main`.

## Troubleshooting

### Swagger envia `string` y Zoho responde `URL_RULE_NOT_CONFIGURED`

Causa: se enviaron IDs ficticios.

Solucion: reemplaza `workspace_id` y `view_id` por IDs reales de Zoho Analytics.

### Zoho responde `EXCEEDING_USR_PLN_API_FREQ_COUNT`

Causa: demasiados requests en poco tiempo.

Solucion: el cliente ya espera `10s` y reintenta hasta `2` veces. Si persiste, espera antes de volver a probar.

### Zoho responde `INVALID_OAUTHSCOPE`

Causa: el refresh token no tiene los permisos necesarios.

Solucion: regenerar el refresh token con los scopes definidos en `ZHA_SCOPE`.

### PostgreSQL no conecta en startup

Revisa:

- `PG_HOST_MV3`
- `PG_PORT_MV3`
- `PG_DATABASE_MV3`
- `PG_USERNAME_MV3`
- `PG_PASSWORD_MV3`
- `PG_SCHEMA_MV3`
- Acceso de red/firewall a la base de datos

### `ModuleNotFoundError`

Causa: dependencias no instaladas o entorno virtual no activo.

Solucion:

```bash
pip install -r requirements.txt
```

## Roadmap

Siguientes pasos naturales:

1. Agregar tests automatizados para integracion Zoho y servicios criticos.
2. Implementar preview seguro desde PostgreSQL sin SQL libre desde requests externas.
3. Implementar sincronizacion Zoho -> PostgreSQL para datasets pequenos.
4. Proponer jobs en background si una sincronizacion puede tardar demasiado.
5. Implementar sincronizacion PostgreSQL -> Zoho.
6. Agregar autenticacion JWT solo cuando exista una necesidad real de proteger endpoints.
7. Agregar CI cuando haya suite de tests estable.

## Reglas De Desarrollo

Antes de modificar el proyecto, leer `AGENTS.md`.

Principios obligatorios:

- Mantener el proyecto minimalista.
- No crear carpetas, capas ni dependencias sin necesidad concreta.
- No mezclar logica HTTP, negocio, PostgreSQL y Zoho.
- Una clase service por modulo.
- Cada ruta debe corresponder a exactamente un metodo publico del service.
- No crear helpers dentro de services salvo instruccion explicita.
- No modificar contracts existentes sin autorizacion explicita.

## Licencia

Este proyecto usa la licencia MIT.

Copyright (c) 2026 Juan Miguel León Gómez, Ingeniero Informático.

Consulta el archivo `LICENSE` para ver los terminos completos.
