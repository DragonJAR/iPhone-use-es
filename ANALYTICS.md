# Analítica de iPhone Use

Organización de PostHog: `iPhone-use`. Proyecto: `653022` (nube de EE. UU.).
Zona horaria del proyecto: `Asia/Shanghai`.
[Panel de uso y fiabilidad](https://us.posthog.com/project/653022/dashboard/2185876).

El envío del lado del servidor sigue el enfoque de Cowart y usa un cliente de la
biblioteca estándar de Python en `server/analytics.py`. El token del proyecto,
que solo permite escribir, está en `server/posthog.json` y se incluye con el
plugin; no hace falta una clave API personal para enviar eventos. Consulta la
[API de captura de PostHog](https://posthog.com/docs/api/capture).

## Recopilación y controles

La analítica está habilitada de forma predeterminada. Registra un UUID de
instalación aleatorio guardado en privado en el directorio de estado del plugin,
un UUID aleatorio nuevo para cada proceso o sesión, la versión del plugin, la
plataforma, la hora del evento y los campos acotados descritos abajo. El UUID de
instalación se mantiene estable entre actualizaciones que reutilizan ese
directorio. Identifica una instalación, no a una persona, un teléfono ni un
chat. No hay perfiles de personas, captura automática del frontend,
grabaciones del teléfono ni enriquecimiento de GeoIP.

Nunca se envían texto del teléfono, selectores, árboles de accesibilidad,
capturas, datos del portapapeles, bundle IDs de apps, UDID, equipos de firma,
rutas del sistema de archivos, IDs de solicitudes MCP ni mensajes de excepción.
Solo se aceptan herramientas, acciones, estados y códigos de error conocidos;
los errores desconocidos se convierten en `other`.

Configura cualquiera de estas variables de entorno en el servidor MCP y
reinícialo para desactivar toda la analítica, incluida la creación de la
identidad analítica local:

```sh
IPHONE_USE_ANALYTICS=0
# O bien:
DO_NOT_TRACK=1
```

En Codex, añade `IPHONE_USE_ANALYTICS = "0"` en
`[mcp_servers.iphone_use.env]` dentro de `~/.codex/config.toml`. En una
configuración MCP JSON portátil, añade `"env": {"IPHONE_USE_ANALYTICS": "0"}`
a la entrada del servidor.

`IPHONE_USE_POSTHOG_PROJECT_TOKEN` reemplaza el token incluido. Un valor vacío
explícito desactiva el envío. Para desarrollo local,
`server/posthog.local.json` puede contener
`{"projectToken":"your-write-only-project-token"}`; Git ignora este archivo y
se excluye de los paquetes de instalación y de código fuente. Orden de
precedencia: variable de entorno, configuración local y configuración incluida.
La captura siempre usa la nube de EE. UU.

`IPHONE_USE_ANALYTICS_ENV` acepta `production` (predeterminado), `development`
o `test`. El panel cuenta únicamente eventos `production`. `sh scripts/check.sh`
desactiva la telemetría para las pruebas y los subprocesos de validación del
paquete; las pruebas unitarias de analítica inyectan remitentes ficticios.
También desactiva la analítica al ejecutar pruebas independientes.

## Eventos

| Evento | Cuándo | Propiedades acotadas |
| --- | --- | --- |
| `iphone_use_session_started` | Una vez por proceso MCP, al inicializarse o en la primera llamada de Runtime con seguimiento | Solo propiedades comunes |
| `iphone_use_tool_called` | Cuando termina o falla una herramienta conocida, en MCP y en llamadas directas a Runtime o CLI | `tool_name`, `outcome`, `error_code`, `duration_ms`; `batch_size` para lotes |
| `iphone_use_ready_result` | En cada comprobación READY | Campos de la herramienta y `ready_state` |
| `iphone_use_setup_result` | En cada llamada de setup | Campos de la herramienta y `setup_action`, `setup_state` |
| `iphone_use_screen_action` | Al abrir, pausar o reanudar la vista previa y al usar sus controles | Campos de la herramienta y `screen_action` |

Se excluye por completo el sondeo de `pua_screen_frame`. Los eventos de
resultado específicos no se cuentan como llamadas adicionales: los gráficos
de uso y errores solo cuentan `iphone_use_tool_called`. Los pasos de un batch
no se cuentan dos veces.

`success` significa que la herramienta terminó sin error ni resultado
explícitamente incompleto. No significa que se haya completado o verificado de
forma independiente una tarea de la persona usuaria. Un resultado READY falso,
una entrada o lote incompleto y los trabajos de setup en cola o en curso se
marcan como `pending`; las excepciones y los resultados explícitamente fallidos
se marcan como `error`. Los eventos de setup registran las llamadas de envío o
consulta de estado, no la finalización autónoma del trabajo.

Las duraciones se miden en milisegundos, desde la entrada en Runtime hasta que
termina o devuelve un error. Incluyen la espera por el bloqueo de operaciones
del teléfono y su ejecución, pero excluyen la cola del worker MCP, la
serialización de la respuesta y el envío de analítica. La duración se limita a
una hora y el tamaño de batch, a 20. Nunca se serializan objetos arbitrarios de
argumentos o resultados.

## Definiciones del panel

Los ocho gráficos nativos de tendencias de PostHog muestran instalaciones
activas al día, inicios de MCP, uso de herramientas, resultados READY, tasa de
fallos de herramientas, latencia media y P95, categorías de error y acciones de
setup. Las consultas exactas se conservan en `scripts/posthog-dashboard.json`
del paquete de código fuente.

Las instalaciones activas son IDs de instalación aleatorios distintos que
realizan una llamada correcta a una herramienta de tarea o a READY; se excluyen
doctor, setup, metrics y los controles de vista previa. Los inicios de MCP
cuentan procesos, no conversaciones. La tasa de errores incluye las llamadas
`pending` en el denominador; un cero en un día sin llamadas no demuestra
fiabilidad. El panel permanece vacío hasta que llegan eventos de producción.
Los eventos de prueba y desarrollo siguen disponibles en Activity, pero no se
incluyen en estos gráficos. Son definiciones específicas de este proyecto, no
métricas aprobadas por el Data Catalog del equipo.

## Límites de envío

La captura mantiene en memoria una cola acotada de eventos en un worker de
fondo: admite como máximo 256 eventos en espera y 20 por solicitud. Cada evento
tiene un UUID aleatorio; ante un fallo de red, HTTP 429 o HTTP 5xx, se reintenta
una vez con el mismo payload y UUID. Los errores HTTP 4xx normales no se
reintentan. Las solicitudes tienen un timeout de socket de tres segundos y el
cierre espera como máximo 1,5 segundos. No se guardan eventos en disco para
reenviarlos después.

El desbordamiento de la cola, las interrupciones prolongadas del servicio o el
cierre inmediato del proceso pueden hacer que se pierdan eventos. Estas
métricas de uso no son un registro de auditoría. Los fallos de analítica nunca
cambian los resultados del teléfono, repiten operaciones ni escriben en la
salida estándar de MCP.
