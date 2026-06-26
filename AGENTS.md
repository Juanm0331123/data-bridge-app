# AGENTS.md

Antes de hacer cualquier tarea en este repositorio, el agente debe:

1. Leer completo este `AGENTS.md`.
2. Revisar la arquitectura actual del proyecto.
3. Revisar las skills instaladas en `skills-lock.json`.
4. Determinar qué skills aplican a la tarea.
5. Usar las skills correspondientes antes de implementar, modificar, refactorizar, documentar o hacer commits.
6. Evitar crear archivos, carpetas, abstracciones o dependencias innecesarias.

## Proyecto

`Data Bridge` es una API backend con FastAPI para conectar PostgreSQL con Zoho Analytics API y permitir, progresivamente, sincronización en ambos sentidos:

- Zoho Analytics -> PostgreSQL
- PostgreSQL -> Zoho Analytics

El proyecto debe mantenerse minimalista, claro, seguro y escalable.

## Arquitectura actual

Respetar estrictamente esta estructura actual:

- `main.py`: punto de entrada principal. Debe exponer o crear la instancia principal de FastAPI.
- `app/config.py`: configuración central y carga de variables de entorno. No contiene lógica de negocio.
- `app/lifespan.py`: startup y shutdown de FastAPI. Inicialización, validación y cierre de recursos. No contiene rutas ni lógica de negocio.
- `app/api/v1/router.py`: router principal de la API v1. Registra routers de módulos o endpoints de esta versión.
- `app/api/v1/health.py`: endpoint de health check.
- `app/db/postgresql.py`: conexión y utilidades de PostgreSQL. Solo engine, pool, sesiones y cierre de conexión. No lógica de negocio.
- `app/integrations/zoho_analytics.py`: cliente o funciones de comunicación con Zoho Analytics API. Solo requests HTTP, headers, autenticación, manejo básico de respuestas y errores de integración. No lógica de negocio ni sincronización.
- `app/logging.py`: logger compartido para la salida de terminal. Centraliza el formato visual de logs y debe reutilizarse desde otros archivos.
- `app/middleware/error_handler.py`: manejo centralizado de errores HTTP. Debe devolver respuestas seguras al cliente y registrar el detalle real en terminal.
- `app/modules/`: módulos funcionales del negocio. Cada módulo representa una capacidad concreta del sistema.
- `docs/arquitecture-diagram.png`: referencia visual de arquitectura.

No proponer arquitectura nueva ni agregar carpetas globales innecesarias. La estructura actual es la base obligatoria de crecimiento.

Como el repositorio todavía está en una etapa inicial, no asumir que ya existen capas adicionales, autenticación JWT, workers, jobs, caché, tests, CI o tooling extra si no están realmente implementados.

## Módulos nuevos

Cada módulo nuevo debe iniciar con esta estructura mínima:

```txt
app/modules/<module_name>/
├── router.py
├── schemas.py
└── service.py
```

Responsabilidades:

- `router.py`: endpoints FastAPI, dependencias HTTP, status codes y response models.
- `schemas.py`: modelos Pydantic para request bodies, query params relevantes y responses.
- `service.py`: lógica de negocio y orquestación.

Solo agregar archivos adicionales si son realmente necesarios:

- `repository.py`
- `models.py`
- `exceptions.py`
- `utils.py`

Reglas:

- No crear `repository.py` si el módulo no tiene acceso propio a base de datos.
- No crear `models.py` si no hay modelos ORM.
- No crear `exceptions.py` si no hay excepciones propias del módulo.
- No crear carpetas internas complejas desde el inicio.
- No aplicar arquitectura hexagonal completa si el módulo todavía es pequeño.
- En `app/modules/<module>/service.py`, debe existir una clase service por módulo.
- Cada ruta del `router.py` debe corresponder a exactamente un método público en la clase service.
- Si hay 3 rutas en un módulo, debe haber 3 métodos públicos en el service de ese módulo.
- Quedan prohibidos los helpers dentro de los services: no crear métodos privados tipo `_helper`, funciones auxiliares ni extraer lógica a helpers si el usuario no lo pide explícitamente.
- No modificar rutas, schemas ni contracts existentes sin autorización explícita.

## Restricciones puntuales de la tarea Zoho preview

- Para la optimización puntual de `preview_zoho_data`, está estrictamente prohibido modificar `app/modules/sync/router.py`, `app/modules/sync/schemas.py` y `app/modules/sync/service.py`.
- Esta optimización solo puede tocar `app/integrations/zoho_analytics.py` y, si es estrictamente necesario, configuración interna relacionada con HTTP, timeouts, caché o conexión.
- No cambiar la API pública, body, response model, nombre de endpoint ni la firma pública `zoho_analytics.export_view_data(workspace_id, view_id)`.
- No crear helpers nuevos en services ni cambiar la estructura del módulo `sync`.

## Skills instaladas

Skills verificadas en `skills-lock.json`:

- `find-skills`
- `grill-me`
- `improve-codebase-architecture`
- `tdd`
- `fba`
- `context7`

### `find-skills`

Usarla cuando no esté claro qué skill aplicar o cuando haga falta una guía más específica.

Usarla especialmente cuando:

- se vaya a trabajar en una parte nueva del backend
- no esté claro qué guía técnica usar
- se necesite una skill más especializada

### `grill-me`

Usarla antes de tomar decisiones importantes.

Uso obligatorio antes de decidir sobre:

- arquitectura
- seguridad
- autenticación
- JWT
- manejo de tokens
- estructura de módulos
- sincronizaciones pesadas
- background jobs
- caching
- nuevas dependencias
- cambios que afecten varias carpetas
- cambios que condicionen el crecimiento futuro del backend

### `improve-codebase-architecture`

Usarla cuando la tarea toque arquitectura, estructura o separación de responsabilidades.

Uso obligatorio cuando:

- se creen nuevas carpetas
- se muevan responsabilidades
- se divida un módulo
- se agreguen capas nuevas
- se proponga `repository.py`, `models.py`, `exceptions.py`, `workers`, `jobs`, `auth`, `services` globales u otra estructura adicional
- se revise si una abstracción es necesaria

### `tdd`

Usarla cuando se creen funcionalidades críticas o endpoints nuevos.

Usarla especialmente para:

- endpoints de sincronización
- validaciones importantes
- servicios que escriban en PostgreSQL
- servicios que lean desde PostgreSQL
- servicios que llamen a Zoho Analytics
- seguridad
- JWT
- casos donde un error pueda alterar datos o sincronizar información incorrecta

### `fba`

Usarla para tareas relacionadas con FastAPI backend.

Uso obligatorio cuando se trabaje con:

- routers
- schemas Pydantic
- dependencias de FastAPI
- response models
- status codes
- autenticación JWT
- RBAC
- paginación
- caching
- background jobs
- estructura de endpoints
- buenas prácticas de FastAPI

### `context7`

Usarla cuando se necesite documentación actualizada.

Uso obligatorio antes de implementar o modificar código relacionado con:

- FastAPI
- Pydantic
- SQLAlchemy
- asyncpg
- httpx
- Uvicorn
- JWT
- OAuth
- Zoho Analytics API, si hay documentación disponible
- cualquier dependencia cuya API pueda haber cambiado

## Seguridad

- Nunca hardcodear credenciales.
- Nunca subir `.env`.
- Nunca exponer tokens de Zoho.
- Nunca exponer `DATABASE_URL`.
- Nunca exponer secretos JWT.
- No permitir SQL libre recibido desde requests externas.
- Usar variables de entorno para secretos.
- Validar entradas con Pydantic.
- No devolver errores internos crudos al cliente.
- Registrar el error real solo en terminal mediante el logger compartido y devolver mensajes sanitizados al cliente.
- Preparar JWT solo cuando sea necesario.
- Cuando se implemente JWT, centralizar la lógica de seguridad y proteger rutas privadas mediante dependencias FastAPI.

## Rendimiento

- Usar `async def` para endpoints y operaciones I/O.
- No bloquear el event loop.
- Usar pool de conexiones para PostgreSQL.
- Mantener endpoints livianos.
- Para sincronizaciones pequeñas, se puede responder directamente desde el endpoint.
- Para sincronizaciones grandes, proponer background jobs antes de implementarlas.
- No agregar Celery, Redis, workers o colas hasta que sean realmente necesarias.
- Si una tarea puede tardar demasiado, usar patrón de job:
    - `POST` para crear job
    - `GET` para consultar estado

## Reglas de código

- Código simple, explícito y legible.
- Type hints obligatorios en funciones nuevas.
- Preferir `async def` para I/O.
- Usar Pydantic para contratos de entrada y salida.
- Reutilizar siempre el logger compartido de `app/logging.py` para salida en terminal.
- No usar `print` en código del proyecto si el mensaje puede salir por el logger compartido.
- Reutilizar el manejador compartido de `app/middleware/error_handler.py` para respuestas de error HTTP.
- No mezclar lógica HTTP con lógica de negocio.
- No mezclar lógica de Zoho con lógica de PostgreSQL.
- No mezclar configuración con lógica de negocio.
- No crear clases si una función simple es suficiente.
- Usar nombres claros y descriptivos.
- Mantener imports limpios.
- No agregar dependencias sin justificar.
- No crear archivos vacíos innecesarios.

## Commits

Antes de cualquier commit, el agente debe:

1. Leer `AGENTS.md`.
2. Revisar qué skills aplican.
3. Usar las skills necesarias.
4. Verificar que no haya secretos.
5. Verificar que no se agregaron archivos innecesarios.
6. Ejecutar o proponer comandos de validación.
7. Generar un mensaje de commit claro.

Formato:

```txt
type(scope): message
```

Tipos permitidos:

- `feat`
- `fix`
- `refactor`
- `docs`
- `test`
- `chore`
- `security`
- `perf`

Ejemplos:

- `docs(agents): add backend project guidelines`
- `feat(sync): add zoho to postgresql service`
- `fix(config): validate environment variables`
- `security(auth): prepare jwt settings`
- `refactor(api): simplify router registration`
- `perf(db): tune postgresql connection pool`

### Comando `do-commit`

Cuando el usuario escriba exactamente `do-commit`, se considera una instruccion explicita para preparar commits, ramas, merges y push remoto. El agente debe ejecutar automaticamente este flujo completo:

1. Revisar `git status`, `git diff` y `git log --oneline -10`.
2. Verificar que no haya secretos, tokens, `.env`, archivos de tokens locales, credenciales, `DATABASE_URL`, API keys ni datos sensibles en los cambios.
3. Separar todos los cambios por funcionalidad, correccion o unidad logica independiente.
4. Crear una rama local por cada unidad logica, partiendo de `main` actualizado.
5. Llevar a cada rama solamente los cambios que correspondan a esa unidad logica.
6. Ejecutar las validaciones disponibles o, si no es posible, explicar la razon.
7. Hacer un commit por rama usando el formato `type(scope): message`.
8. Fusionar cada rama en `main` con merges no interactivos.
9. Revisar que `main` quede correcto con `git status`, `git diff`, logs recientes y validaciones disponibles.
10. Hacer push de `main` al remoto configurado.
11. Borrar las ramas locales creadas para ese flujo.
12. Si alguna rama temporal fue publicada en remoto, borrar tambien esa rama remota.

Reglas obligatorias para `do-commit`:

- No usar `git push --force` ni variantes force.
- No usar `git reset --hard` ni comandos destructivos sin autorizacion explicita adicional.
- No saltar hooks.
- No modificar ni revertir cambios ajenos salvo que el usuario lo pida explicitamente.
- Si hay conflictos, secretos, cambios ambiguos o una separacion insegura, detenerse y preguntar antes de continuar.
- Si no existe remoto configurado o el push falla por permisos/autenticacion, dejar `main` listo localmente y reportar el bloqueo.

## Comandos actuales

Comandos verificados actualmente en el proyecto:

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Si se agregan nuevos comandos, el agente debe explicar por qué son necesarios.

## Regla final

Antes de cualquier cambio, revisar este archivo y respetar la arquitectura actual del repositorio.

No crear archivos, carpetas, abstracciones, dependencias o capas nuevas sin una necesidad concreta y justificada.
