# iPhone Use

**Español** · [English](README.en.md)

Deja que Codex controle tu iPhone real por USB. Describe la tarea en lenguaje natural: Codex puede abrir apps, leer pantallas, pulsar, desplazarse, escribir texto, recopilar listas y mostrar el teléfono en una barra lateral.

iPhone Use se comunica con el iPhone mediante [WebDriverAgent](https://github.com/appium/WebDriverAgent) (WDA). Incluye un servidor MCP local, skills de configuración y uso, y un widget con la pantalla en vivo. Reutiliza las conexiones y compilaciones existentes cuando están en buen estado; si no puede localizar un control, guía al modelo para que revise una captura e intente tocar por coordenadas.

De forma predeterminada, el plugin envía estadísticas de uso anónimas a un proyecto propio de PostHog. Registra inicios, llamadas a herramientas, estados de conexión, duración y categorías de error. Usa un identificador de instalación aleatorio y no envía imágenes del teléfono, texto introducido ni identificadores del dispositivo. Para desactivarlas, configura `IPHONE_USE_ANALYTICS=0` o `DO_NOT_TRACK=1` y reinicia el servidor MCP. Consulta la [documentación de analítica](ANALYTICS.md).

**Antes de usar iPhone Use, instala, firma e inicia WDA Runner en tu propio iPhone.** WDA es el servicio de ejecución que funciona en el dispositivo. El prompt y el flujo de configuración de abajo ayudan a Codex con la instalación inicial; también se puede reutilizar una instancia de WDA que ya funcione.

## Pide a Codex que lo instale

Copia este prompt en Codex en tu Mac:

```text
Ayúdame a instalar y configurar iPhone Use:
https://github.com/DragonJAR/iPhone-use-es

Lee primero el README del repositorio y el script de instalación. Comprueba Codex CLI,
Python, Node.js, npm, Xcode completo y el iPhone conectado por USB. Clona el proyecto
en la carpeta local `iPhone-use-es`, entra en ella y ejecuta `sh scripts/install.sh`.

Si este chat aún no ha cargado las herramientas nuevas, dime que vuelva a conectarlo
o que abra un chat nuevo, y continúa allí. Cuando las herramientas estén disponibles,
lee el skill iphone-use-setup. Revisa la configuración existente y reutiliza una WDA
que funcione. Para la primera configuración, detecta mi dispositivo, usa mi propio
equipo de desarrollo de Apple y un bundle ID que pueda firmar, descarga la versión
fijada de WDA, configura la firma, compila e inicia el servicio. Continúa hasta que
pua_ready devuelva ready=true y, después, muestra la pantalla del teléfono. No reutilices
los identificadores del dispositivo ni la configuración de firma del autor.

Ayúdame a resolver las dependencias que falten. Si tengo que iniciar sesión en mi
cuenta de Apple, confiar en el dispositivo, activar el modo de desarrollador o
desbloquearlo, explícame los pasos concretos y espera a que los complete.
```

Después de instalar el plugin, es posible que debas reconectar el chat actual para cargar las herramientas; el flujo puede continuar después de reconectarlo. El inicio de sesión en Apple, la confianza del dispositivo, el modo de desarrollador y el desbloqueo se completan en la interfaz del sistema por la persona propietaria del dispositivo.

## Requisitos

| Requisito | Uso |
| --- | --- |
| macOS y Codex para escritorio o CLI | Instalar el plugin local y ejecutar el servidor MCP y la barra lateral de pantalla |
| Xcode completo, con la configuración inicial terminada | Compilar, firmar, instalar y ejecutar WDA; Command Line Tools por sí solo no es suficiente |
| Una cuenta y un equipo de desarrollo de Apple disponibles en Xcode | Firmar WDA Runner en el dispositivo |
| Un iPhone real conectado por USB | Confiar en el Mac, activar el modo de desarrollador si el sistema lo requiere y mantenerlo desbloqueado durante la instalación y el inicio |
| Python 3.9 o posterior | Ejecutar el servidor MCP; Python usa la biblioteca estándar |
| Node.js 20.19+, 22.12+ o 24+, y npm 10+ | Reenvío USB y transmisión de pantalla; consulta `engines` del proyecto y las comprobaciones de `doctor` |

Xcode debe ser compatible con la versión de iOS del teléfono. No hace falta hacer jailbreak ni iniciar un Appium Server por separado. La configuración usa una versión verificada y fijada de WDA 16.14.0, y gestiona localmente las descargas, dependencias, firma y compilación.

## Instala e inicia WDA en tu propio iPhone

El servicio que funciona en el teléfono proviene de [WebDriverAgent, mantenido por Appium](https://github.com/appium/WebDriverAgent). La primera vez, firma e instala `WebDriverAgentRunner` con tu propia cuenta y equipo de desarrollo de Apple usando Xcode.

El prompt de instalación y el flujo `iphone-use-setup` descargan la versión de WDA fijada por el proyecto, configuran la firma, compilan, instalan e inician el servicio. Codex te explicará cualquier paso que requiera tu intervención.

Para configurarlo manualmente en Xcode:

1. Conecta tu iPhone por USB, confía en el Mac, activa el modo de desarrollador si se solicita y configura tu cuenta de Apple en Xcode.
2. Abre `WebDriverAgent.xcodeproj` del código fuente de WDA descargado; selecciona el scheme `WebDriverAgentRunner` y tu iPhone. En **Signing & Capabilities** del target Runner, selecciona tu Team y un Bundle Identifier que puedas firmar.
3. Usa **Product → Test** para compilar, instalar y ejecutar WDA Runner; sigue en el teléfono las indicaciones para confiar en el Mac. La ejecución de las pruebas inicia el servicio WDA; después de instalarlo, el servicio debe permanecer en ejecución.

La primera vez que uses este chat, llama a `pua_setup(action="status")` para reutilizar un servicio sano o un trabajo activo; ejecuta `start` solo si falta el servicio. `start` espera hasta 20 segundos de forma predeterminada. Si se agota el tiempo, consulta el mismo `job` y no vuelvas a iniciar el trabajo. Cuando el servicio esté listo, comprueba que `pua_ready` devuelva `ready=true` antes de empezar a usar el teléfono. Consulta la [guía de Appium para preparar un dispositivo real](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/device-setup/) sobre los requisitos del dispositivo y la firma.

## Instala el plugin

```sh
git clone https://github.com/DragonJAR/iPhone-use-es.git
cd iPhone-use-es
sh scripts/install.sh
```

El script valida y prepara el código fuente, registra el marketplace local mediante Codex CLI, instala el plugin y sus skills, y registra como MCP estándar `iphone_use` el servidor guardado en la caché de instalación. El plugin y la configuración estándar usan el mismo espacio de nombres para evitar registrar herramientas duplicadas.

También puedes descomprimir el paquete de código fuente y ejecutar el mismo script desde su carpeta. Cuando termine la instalación, reconecta Codex o abre un chat nuevo.

## Conecta tu propio iPhone

En un chat nuevo, activa **iPhone Use** y escribe:

> Usa iphone-use-setup para configurar el iPhone conectado por USB, instalar e iniciar WDA, comprobar READY y mostrar la pantalla del teléfono.

El skill guía a Codex por el diagnóstico, la detección del dispositivo, la firma, la descarga de WDA y la compilación e inicio en segundo plano. Los dispositivos ya configurados reutilizan su configuración y compilación, así que las tareas normales no requieren reinstalar cada vez. Empieza a usar el teléfono solo después de que `pua_ready` devuelva `ready=true`.

## Qué puedes hacer

| Función | Ejemplo |
| --- | --- |
| Navegación y uso de apps | Abrir una app y llegar a una pantalla de búsqueda, detalles, ajustes o borrador |
| Lectura de pantallas | Obtener un árbol compacto de controles, texto, posiciones y una captura real |
| Pulsaciones y gestos | Tocar un control o unas coordenadas, deslizar, arrastrar y esperar a que aparezca un objetivo |
| Entrada Unicode y textos largos | Introducir texto Unicode completo en una llamada; dividir textos largos y continuar la entrada |
| Tareas compuestas | Agrupar pulsaciones, texto y esperas conocidas en un `batch` para reducir los turnos del modelo |
| Búsqueda y recopilación en listas | Buscar desplazándose de forma acotada, leer con solapamiento, eliminar duplicados e indicar la cobertura |
| Recuperación visible ante fallos | Revisar una captura nueva y volver a elegir el punto si un control está cubierto, sin foco o ausente del árbol |
| Pantalla en vivo | Ver el marco del iPhone, el estado del dispositivo, los efectos de operación y los indicadores de pulsación o arrastre |
| Recuperación de conexión | Reutilizar trabajos de inicio en segundo plano, reconstruir sesiones no válidas y reconectar la vista previa con Actualizar |

Ejemplos de prompts:

```text
Usa iPhone Use para abrir Notas, crear un borrador, introducir el siguiente texto en chino,
comprobarlo y dejarlo ahí.

Abre la app indicada, busca este nombre y resume los primeros resultados.

Lee esta lista mientras te desplazas con solapamiento. Elimina duplicados e indica
el intervalo cubierto y cualquier duda pendiente.
```

La entrada de texto y el envío son acciones distintas; por defecto, el texto no se envía. El modelo comprueba las pantallas, destinatarios, cantidades y resultados clave. La persona usuaria se ocupa de contraseñas, códigos de verificación y Face ID; la vista previa se puede pausar durante esa intervención.

Las aperturas repetidas de la vista previa en el mismo chat reutilizan el widget existente. La barra inferior ofrece Actualizar, Inicio y Captura. Si no hay imagen, el marco del iPhone muestra una pantalla oscura con un icono de estado centrado; la etiqueta superior muestra el estado de conexión: **Conectando**, **En vivo**, **En pausa** o **Sin conexión**; cuando el iPhone está bloqueado, muestra **Desbloquea el iPhone**. La vista previa es para la persona usuaria; el modelo toma decisiones a partir de observaciones reales de las herramientas.

## Detalles técnicos

- **Conexión USB local.** El servidor MCP de Python accede a WDA mediante un reenviador local limitado a loopback; los datos de ejecución y firma permanecen en el Mac.
- **Reutilización.** Las conexiones HTTP persistentes, las sesiones WDA, los servicios sanos y las compilaciones existentes reducen el trabajo repetido.
- **Observaciones compactas y acciones compuestas.** Se omiten campos duplicados del árbol, no se genera XML si solo hace falta una captura y se reducen turnos con `batch`, búsqueda por desplazamiento y recopilación de listas.
- **Configuración en segundo plano.** La descarga, compilación e inicio devuelven identificadores de trabajo consultables; las configuraciones repetidas reutilizan trabajos activos compatibles.
- **Captura como alternativa.** Si no se localiza un elemento, se devuelve una captura con instrucciones. Multiplica sus píxeles por `image.pixel_to_point` para obtener coordenadas en puntos del iPhone y pasarlas a `pua_tap`.
- **Errores explícitos.** Un bloqueo compartido coordina varios procesos; si una acción agota el tiempo o se interrumpe la conexión, consulta primero el estado real antes de volver a intentarla.
- **Ciclo de vida de la vista previa.** Las imágenes transmitidas no se guardan en disco; se distinguen las pausas por bloqueo de las pausas explícitas y Actualizar permite reconectar.

Estas mejoras reducen llamadas repetidas y turnos del modelo. La velocidad de cada tarea también depende de la app, el estado de USB y WDA y la respuesta del modelo. Las regresiones de ingeniería y las comprobaciones en dispositivo se documentan por separado en material local de desarrollo.

## Herramientas

El modelo dispone de 17 herramientas y hay otras 2 herramientas exclusivas del widget.

| Herramientas | Uso |
| --- | --- |
| `pua_doctor`, `pua_setup`, `pua_ready` | Diagnóstico, configuración, instalación e inicio en segundo plano y comprobación de disponibilidad |
| `pua_observe`, `pua_find` | Árboles de controles, capturas y búsqueda de objetivos |
| `pua_apps`, `pua_launch_app` | Identificadores de apps, evidencia de instalación e inicio de apps |
| `pua_tap`, `pua_swipe`, `pua_press_button` | Pulsaciones, deslizamientos y botones del dispositivo |
| `pua_type_text`, `pua_wait` | Entrada Unicode y esperas acotadas |
| `pua_batch`, `pua_scroll_find`, `pua_collect_list` | Acciones compuestas, búsqueda y recopilación |
| `pua_screen`, `pua_metrics` | Controles de vista previa y estadísticas acotadas de duración |

Ante un estado anómalo de la interfaz, primero se devuelve una captura para que el modelo la revise antes de elegir otra acción. La búsqueda mediante desplazamiento realiza como máximo un gesto por llamada y se detiene si el objetivo sigue fuera de alcance. La misma alternativa con captura se usa si un control está cubierto, no se demuestra el avance, la entrada no coincide o no aparece la pantalla esperada. Se reutilizan las capturas existentes, sin gestos adicionales ni repetición automática de acciones.

## Datos locales y actualizaciones

Las instalaciones nuevas usan `~/.local/share/iphone-use/`. Configura `IPHONE_USE_STATE_DIR` para indicar otra carpeta externa; `WDA_STATE_DIR` sigue siendo compatible. Si aún no existe la nueva carpeta predeterminada, se reutiliza una carpeta de configuración anterior detectada para conservar la configuración del dispositivo y las compilaciones.

Las carpetas de ejecución usan permisos 700 y los archivos de configuración privada e imagen, 600. Las capturas explícitas tienen límites de conservación; las transmisiones de vista previa solo permanecen en memoria. Los datos de firma, del dispositivo, los registros de ejecución y las dependencias quedan excluidos de los paquetes de código fuente. `WDA_URL` acepta una dirección local; el puerto reenviado predeterminado es 18100 y se rechazan direcciones remotas.

Para actualizar un repositorio clonado:

```sh
git pull --ff-only
sh scripts/install.sh
```

Reconecta el chat para cargar las herramientas, skills y recursos de pantalla actualizados. Si falla la conexión con el teléfono, comprueba USB, que el dispositivo esté desbloqueado, el modo de desarrollador, la firma de Xcode y el error concreto de `setup`. Si ya hay un trabajo de inicio activo, sigue consultándolo en lugar de reiniciarlo repetidamente.

## Desarrollo y documentación

```sh
npm ci --prefix ui --no-audit --no-fund
npm run build --prefix ui
sh scripts/check.sh
python3 scripts/package.py
```

El resultado de compilación es un HTML autocontenido para la pantalla. El paquete de código fuente se guarda en `dist/iphone-use-<versión>-source.zip`. La instalación y el uso normal no requieren volver a compilar la UI. El plugin instalado conserva el código fuente, estilos, scripts de compilación, configuración, archivo de bloqueo de dependencias y pruebas del widget para facilitar su mantenimiento local.

- [Vista previa de pantalla y recuperación](skills/iphone-use/references/screen.md)
- [Referencia de identificadores de apps](skills/iphone-use/references/apps.md)
- [Instalación y solución de problemas de conexión](skills/iphone-use-setup/references/troubleshooting.md)
- [Registro de cambios](CHANGELOG.md)

## Dependencias y agradecimientos

Este proyecto depende del ecosistema [Appium](https://github.com/appium/appium) y de [WebDriverAgent](https://github.com/appium/WebDriverAgent): WDA aporta el servicio de automatización en el teléfono y [appium-ios-device](https://github.com/appium/appium-ios-device) permite la comunicación USB con el dispositivo, el reenvío de puertos y la conexión a la transmisión de pantalla. Sobre esa base, iPhone Use proporciona un plugin de Codex, herramientas MCP, una guía de instalación y un widget de pantalla, sin necesidad de ejecutar Appium Server por separado.

Gracias a las personas que mantienen y contribuyen a Appium, WebDriverAgent y los proyectos relacionados; su trabajo permite automatizar iPhones reales.

MIT License. Consulta la [información sobre componentes de terceros](THIRD_PARTY_NOTICES.md).
