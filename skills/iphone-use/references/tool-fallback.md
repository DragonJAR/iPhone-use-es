# Fallo de MCP y llamada por código

Llama de preferencia a la herramienta ya encapsulada y ejecuta con optimismo las acciones habituales; cuando el paso siguiente necesite información, juzga de paso la acción anterior. Que falte el enlace de la herramienta, que el host reenvíe mal o que haya un problema confirmado del encapsulado no significa que PUA no esté disponible. Para la misma acción ya autorizada se puede usar el punto de entrada de código del plugin. La reserva por código conserva la misma configuración, sesión, cerrojo de operación y el tratamiento explícito de anomalías, y no añade una comprobación en cada paso.

La edición normal ofrece 17 herramientas para el modelo. Mira primero los enlaces de herramientas que de verdad se pueden llamar en este turno (si se admite, con ALL_TOOLS o la búsqueda de herramientas); no infieras que ya están enlazadas solo a partir de tools/list, de la documentación o de un chat anterior. El install.sh de 0.1.6 registra a la vez un MCP estándar del mismo nombre, para que el presupuesto de la explicación compartida del plugin de Codex no oculte herramientas, y conserva el schema completo de batch. Después de instalar una versión nueva, reconecta el chat. Usa el punto de entrada de código de abajo solo cuando sigan faltando de verdad las herramientas necesarias; no conviertas por defecto en CLI todas las operaciones ya encapsuladas.

## Distingue primero el error

- Error de schema / parámetros: corrige una llamada según argument_path, unknown_fields y allowed_fields. action_executed=false significa que la acción no se envió; si el enlace MCP sigue sin estar disponible, se puede usar el punto de entrada de código. No ignores parámetros desconocidos por tu cuenta.
- `device_busy`: otra operación tiene el cerrojo compartido. Espera a que termine; no crees otra configuración de Runtime ni otro state directory para saltarte el cerrojo.
- `stale_observation`: el ID no pertenece al Runtime actual, o ya cambiaron la app / el contexto del viewport. Localiza con la información nueva que el paso siguiente necesite. No añadas una lectura de imagen por un hash de toda la imagen, por un refresco de cifras en el texto o por un plazo fijo de 30 segundos. El ID es contexto opcional, no un permiso obligatorio de cada acción por coordenadas.
- Ante una anomalía de interfaz, mira primero la captura: fallo de selector / foco, no se encuentra un objetivo pulsable después de desplazar, no hay avance, la zona está tapada, cambió el contexto del desplazamiento, lo escrito no coincide o no apareció la página esperada. Mira primero la captura ya adjunta al resultado; solo si falta la imagen, completa una vez screenshot y después elige el objetivo visible, trata la capa flotante o decide si sigues desplazando. No releas antes el árbol, no cambies la etiqueta ni reintentes igual. `tap_point` / candidates no demuestran que no haya oclusión. Para escribir, toca primero el campo visible y después type_text; si el foco sigue fallando, hay que elegir otro punto. Las coincidencias apiladas en el mismo sitio, o cuando solo una está en pantalla, las resuelve la herramienta.
- `input_continuation_expired`: la continuación del texto largo ya no vale y esta vez no se escribió nada. Lee el texto real del campo y, con `replace=false`, completa solo la parte que falta.
- `occluded_target` / `offscreen_target`: el toque sobre el objetivo no se ejecutó, y no se puede inferir que un toque no ejecutado haya abierto una capa flotante. `occluded_target` se juzga con la captura adjunta: si el objetivo se ve, toca por coordenadas según `tap_point`; si hay una oclusión real, trátala primero. `offscreen_target` se desliza primero hacia el objetivo. Un panel a media pantalla dibujado por la app puede no tener nodos nativos Alert / Sheet; júzgalo por la captura real.
- `postcondition_failed` de una comprobación explícita: la acción se recibió, pero no se cumplió la condición. Mira el estado real y decide los pasos que quedan; no reejecutes la acción solo porque falló la comprobación.
- `action_executed=true, action_complete=false`, `uncertain=true` o timeout después de la acción: al menos parte de la acción puede haber surtido efecto. Una escritura, un envío, un envío de formulario, un borrado y acciones parecidas miran primero el campo / el registro reales; no cambies al punto de entrada de código y lo repitas a ciegas.
- Fallo breve de una consulta: la herramienta puede releer una vez con un límite. Una interfaz de consulta POST no debe tratarse como una mutación; que la consulta falle no demuestra que se haya ejecutado una acción en el teléfono.
- `local.pid.0`, `pua_foreground_unavailable` o XCTest Code 41: fallo del canal; llama a READY para recuperar. No lo trates cambiando el selector o repitiendo botones del teléfono. La pantalla bloqueada, la firma y la confianza siguen la skill de setup; la contraseña de la app / Face ID siguen la toma de control por autenticación.

Al pasar por `functions.exec`, reenvía cada bloque de contenido: el texto con `text(block.text)` y la imagen con `image(block)`. No uses `text(result)`, que convierte la captura en texto base64. Si la imagen no se puede reenviar, abre con `view_image` `image.path` / `error.observation.image.path`. Convierte las coordenadas con `pixel_to_point`.

Un `verified=false` ordinario no es un error y no exige observe ni detener el batch. HTTP accepted solo describe el límite de la petición. Un camino habitual continúa, y el estado final crítico se comprueba de forma explícita.

Home usa el extremo dedicado a la pantalla de inicio en el teléfono. Por defecto no se espera a SpringBoard por separado; la observación al preparar el paso siguiente muestra el estado real. Cuando haga falta confirmar la pantalla de inicio, usa `verify=true` explícito; contrasta el primer plano con un límite. Que la interfaz genérica de teclas devuelva HTTP 200 y la interfaz no haya cambiado no permite deducir de ahí la causa interna de iOS / XCTest.

## Recuperación acotada de READY

Una tarea normal usa `pua_ready(recover=true)` u omite recover. false solo sirve cuando el usuario prohíbe reiniciar o pide un diagnóstico de solo lectura, y esa restricción se conserva. Un primer plano inválido de forma transitoria solo limpia la observación / la sesión antiguas y relee una vez. Solo un fallo que continúa reinicia el servicio de este plugin cuya pertenencia ya se verificó, y reutiliza la compilación válida. No reejecuta navegación, escritura ni envío.

`ready=false, state="recovering"` trae recovery.job_id y los parámetros de consulta. status devuelve un array `jobs`; encuentra el trabajo cuyo id sea igual a job_id. Revisa recovery_phase y, al pasar de stopping / starting a serving, vuelve a comprobar READY. El Runner puede seguir en running mucho tiempo; no esperes succeeded ni repitas start. Consulta según la fase, el registro y retry_after_seconds. No escribas un bucle de espera fijo de 15 segundos × 20 veces, ni leas un job individual que no existe y tragues la excepción de parseo.

Con `ready=false, state="recovery_required", reason="recovery_disabled"`, llama a recover=true según next_tool / next_arguments solo si la instrucción del usuario lo permite. Si lo prohíbe con claridad, explica el bloqueo. Un estado normal de no estar listo no trae error y MCP isError=false; aun así no se puede continuar con acciones en el teléfono. Al llegar a `ready=true`, reutiliza directamente la observation que trae para preparar el paso siguiente, sin hacer observe otra vez a continuación.

La recuperación exige que coincidan la configuración, el endpoint, el worker y la pertenencia del puerto de escucha. Si la pertenencia no está clara, hay un PUA externo, un conflicto de puerto o falta la compilación, sigue los pasos devueltos y no mates procesos por el puerto. El enfriamiento de 120 segundos se diagnostica según retry_after_seconds; no reinicies en serie. La confianza, el desbloqueo y la confirmación de la automatización de la interfaz los completa el usuario en el teléfono.

## Ejecutar directamente el script incluido

Determina `<PLUGIN_ROOT>` desde el proyecto actual o desde el plugin instalado; no copies la ruta de caché de la versión de otra persona. Home habitual:

```sh
python3 <PLUGIN_ROOT>/scripts/phone.py pua_press_button '{"name":"home","observe":"none","verify":false}'
```

El script usa la sesión compartida y el cerrojo de operación de `~/.local/share/iphone-use` por defecto, y devuelve un resultado estructurado. Si el paso siguiente necesita información de una página desconocida, elige observe de forma explícita en esta acción. Si hace falta una comprobación crítica, usa verify=true explícito. La salida del comando es solo JSON: la captura está en `image.path` (JPEG ya escalado; el `.png` del mismo nombre es la captura original). Para verla, ábrela con la herramienta de imagen disponible; multiplica los píxeles por `image.pixel_to_point` para obtener puntos del iPhone.

Pasa --state-dir / --url coincidentes solo si el canal original usaba de verdad un directorio o una URL que no son los de defecto. No cambies de directorio para esquivar busy ni controles el mismo teléfono en paralelo.

## Escribir el código mínimo de llamada

Si el host no puede llamar al script, se puede importar el mismo Runtime. El ejemplo conserva la configuración por defecto y el error estructurado:

```python
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).expanduser().resolve()
sys.path.insert(0, str(root / "server"))
from iphone_use import PUAError, Runtime

runtime = Runtime()
try:
    result = runtime.call("pua_press_button", {"name": "home", "observe": "none", "verify": False})
    print(json.dumps(result, ensure_ascii=False))
except PUAError as error:
    print(json.dumps({"error": error.as_dict()}, ensure_ascii=False))
    raise SystemExit(1)
finally:
    runtime.close()
```

Los dos puntos de entrada se saltan el enlace MCP y aun así pasan por la implementación compartida. El observation ID no se comparte entre procesos. Si eliges usar un ID, obtén la observación en el mismo Runtime y pásala a la acción. Unas coordenadas o una region conocidas pueden no llevar ID; no leas una imagen o un árbol de más solo para obtener permiso. Usa coordenadas en puntos del iPhone, no coordenadas de la pantalla del Mac ni píxeles de la captura. Un fallo de la propia implementación compartida no se arregla cambiando de entrada; ajústalo según la anomalía real. No crees una session de PUA externa ni repitas una mutación a ciegas.

## Desplazamiento y lotes

El swipe por defecto es `verify=false, observe="none"`: ejecuta un gesto, no lee XML para comprobar el avance ni hace un fallback automático. Una region conocida se puede usar directamente, sin forzar árbol, ancla o ID. Cuando el paso siguiente ya necesite leer la lista, esa misma acción devuelve directamente la observación necesaria y se juzga de paso si hubo movimiento. Una respuesta por defecto no verificada no equivale a que no haya habido movimiento.

Solo `verify=true` explícito comprueba el avance del desplazamiento, las capas flotantes nativas y el cambio de contexto. Si hay que depurar, elige tree / both en esa misma llamada y reutiliza la observación devuelta; no leas otra vez por separado. El avance se juzga por el cambio geométrico de la lista; un refresco de cifras o del texto de un carrusel no debe ser, por sí solo, la base para dar el desplazamiento por bueno o para rechazar la acción. La protección de verificación de una capa flotante nativa no reconoce todos los paneles dibujados por la app. Tras una oclusión clara, elige la zona o cierra el panel según el estado real.

Si `verify=true` ve que el primer gesto no avanza, adjunta la captura y se detiene; no cambia de gesto por su cuenta. El parámetro antiguo `max_attempts=2` se puede seguir pasando, pero no provoca un reintento automático. `scroll_find` se desliza como máximo una vez por llamada y, si sigue sin encontrar un objetivo pulsable, devuelve primero la captura. La oclusión y la ambigüedad se detienen antes de deslizar. Mira de verdad la imagen y juzga entonces si continúas, la zona, la dirección y el objetivo; no aumentes `max_swipes` y vuelvas a lanzarlo directamente.

`no_scroll_progress` no demuestra una lista vacía ni que se haya llegado al final. El resultado anómalo adjunta captura aunque se haya pedido none/tree. Revisa la entrada, el límite, la capa flotante y el contenido dibujado por la app. `scroll_context_changed` indica que el contexto cambió después del gesto; mira primero la captura y actúa después. La parte ya ejecutada no se puede tratar como no ejecutada y reejecutar. Si falla la lectura de la captura, se conservan el error original y la evidencia de ejecución, y se indica que se tome la imagen por separado; no se continúa la acción por cuenta propia.

Un batch puede ejecutar seguidos navegación y escritura ordinarias no verificadas. Se detiene solo ante un error claro, uncertain o un submit no comprobado, y se continúa lo que quede según completed_steps / stopped_at. launch, por defecto, solo activa una vez. Solo verify=true / expect explícitos esperan con un límite el primer plano / la página. Si falla una comprobación crítica, mira primero el estado real y no vuelvas a hacer activate por tu cuenta.

Que la llamada por código tenga éxito, que Home termine, que se haya leído una app o que un batch termine son solo resultados de etapa. Continúa el trabajo que quede y cierra la tarea entera solo cuando estén listos el resultado crítico final y la entrega.
