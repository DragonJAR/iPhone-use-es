# Vista previa de la pantalla del iPhone y recuperación

El widget muestra la imagen del teléfono al usuario; el modelo solo usa la observación que devuelven de verdad las herramientas. En vivo, una imagen en caché, el efecto de luz o el indicador del gesto no sustituyen a READY ni demuestran que la tarea haya terminado. Abrir, pausar, reanudar y reconectar reutilizan el mismo panel de este chat; si el panel ya existe, continúa directamente, y si está cerrado llama una vez a `pua_screen()`. No repitas READY ni abras un panel nuevo solo para actualizar la imagen.

## Sin imagen o con la vista en pausa

- Mientras no llega el primer fotograma, `frame_available=false` no demuestra un fallo de conexión. La vista previa usa un canal USB MJPEG independiente, separado del canal de control de PUA. Si las herramientas de control responden y a la vista previa le falta un fotograma, no reinicies PUA una y otra vez, no crees una session nueva ni entres en un bucle de capturas por eso.
- Cuando no hay ninguna imagen válida, conserva la carcasa del iPhone y la pantalla negra; en el centro solo se muestra el icono que corresponda: conexión, pantalla bloqueada, autenticación, pausa o imagen no disponible. Un corte breve conserva el último fotograma; la caché no es prueba del estado actual del teléfono.
- Con `preview.paused=true`, mira primero `pause_reason`. `device_locked` significa que se espera a que el usuario desbloquee el iPhone, y un READY correcto solo reanuda la pausa de ese mismo bloqueo. `authentication`, o un `unknown` de una versión anterior, esperan a que el usuario termine de verdad según [toma de control por autenticación](authentication.md) y solo entonces hacen resume explícito.
- El usuario puede pulsar el botón inferior de actualizar para reconectar la vista previa y comprobar el desbloqueo; si tiene éxito, se reanuda la pausa que había en el momento del clic, y una pausa nueva ocurrida durante la comprobación se conserva. Actualizar no reinicia PUA, no crea una sesión de control nueva y no envía gestos al teléfono. El modelo no puede pulsar por el usuario el botón reservado a la app.
- Después de actualizar el plugin, un chat antiguo puede seguir conectado al proceso o a los recursos de interfaz viejos. Reconecta el chat, cierra la página de pantalla antigua y llama una vez a `pua_screen()` para cargar el recurso nuevo. No hace falta reinstalar o reiniciar PUA solo para actualizar la imagen.

Si la propia herramienta de control devuelve un fallo de conexión, sigue [arranque y recuperación](startup.md). Si falla la localización en la interfaz, continúa con el flujo de captura y coordenadas de la skill principal.

## Autenticación y límite de las herramientas

Cuando la app pide contraseña, PIN, código de verificación o Face ID / Touch ID, pausa la vista previa según [toma de control por autenticación](authentication.md), pide al usuario que lo complete en el teléfono y pausa las acciones, las lecturas y las capturas. Abrir el widget o un READY correcto no significa que la autenticación haya terminado. Tras el aviso real de que terminó, obtén una observación nueva y continúa; no reutilices coordenadas antiguas ni reejecutes una acción de negocio que quizá ya surtió efecto.

`pua_screen_frame` y `pua_screen_action` son solo para la app; no son herramientas de observación o control del modelo. Los botones inferiores de actualizar, pantalla de inicio y captura los pulsa el usuario. Durante la pausa por autenticación, la pantalla de inicio y la captura no están disponibles. Ocultar o cerrar la página detiene el sondeo de fotogramas; la pausa por autenticación detiene la captura de inmediato y borra la imagen real.

## Widget que viaja con el plugin

El plugin incluye la página autocontenida `assets/phone-screen.html` y también el fuente completo de `ui/`, los estilos, el archivo de bloqueo de dependencias, la configuración de build y las pruebas del widget. La instalación y el uso normal cargan directamente la página ya compilada. Para reconstruir, ejecuta en el directorio del plugin:

```sh
npm ci --prefix ui --no-audit --no-fund
npm run build --prefix ui
python3 scripts/check_screen_ui.py
```

La interfaz no depende de una CDN ni de fuentes remotas. El script del flujo USB del que depende la vista previa en el servidor y el manifiesto de dependencias de `tooling/` también viajan con el plugin. `docs/` y `evals/` son material de desarrollo local, no dependencias de ejecución.
