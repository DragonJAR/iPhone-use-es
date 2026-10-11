# Registro de cambios

## 0.3.8 — 2026-10-09

- Se añadió una guía breve para pasar archivos por AirDrop al Mac: comparte el archivo desde el teléfono al Mac actual y úsalo directamente desde Descargas.

- En el primer uso, ejecuta setup para comprobar el servicio y después READY; se sincronizaron las instrucciones de los skills, la descripción del plugin y la guía MCP. `start` espera hasta 20 segundos de forma predeterminada; `status` puede esperar de forma acotada al mismo `job`, reduciendo las consultas de inicio.

## 0.3.7 — 2026-10-09

- Se excluyó el atributo `accessible`, que no se usaba, al leer todo el XML, reduciendo las consultas nativas de accesibilidad por nodo. Se conservaron la estructura de nodos, el texto, los valores, las coordenadas, las opciones de visibilidad y la comprobación `hittable` antes de pulsar.
- Comparación en dispositivos reales: el contenido de los nodos UI antiguos y nuevos coincidió en pantallas de WeChat, Taobao y Fotos. El XML original se redujo aproximadamente entre un 7 % y un 8 %; el tiempo de lectura depende de la pantalla y la caché, y aún puede agotarse el tiempo de una instantánea completa.

- Se tomó como referencia la integración de Cowart y se conectó un proyecto y organización propios de PostHog para iPhone Use. Se registran inicios anónimos, uso de herramientas, resultados READY, operaciones de setup y controles de vista previa.
- El envío en segundo plano se limita a campos permitidos y excluye imágenes, texto, identificadores del dispositivo y sondeos frecuentes de fotogramas. El interruptor para desactivarlo, la cola acotada y los reintentos de red que conservan el UUID del evento no afectan las operaciones del teléfono.
- Se añadieron ocho gráficos de uso y estabilidad que separan los datos de producción de los de validación; también se agregaron la documentación de analítica, pruebas de regresión y configuración del paquete de publicación.

## 0.3.6 — 2026-10-08

- Se mantuvo una franja de luz tenue en el centro de los bordes superior e inferior del degradado de pantalla. Se conecta gradualmente con los colores y la animación de puntos existentes y luego se atenúa con suavidad. Se generan tres máscaras estáticas según el diseño y se sigue usando el fundido cruzado de opacidad.

- Se unificaron los nombres de herramientas: de `wda_*` a `pua_*`. PUA significa Phone Use Agent. Hay 17 herramientas para el modelo y 2 exclusivas del widget.
- Se sincronizaron las descripciones de herramientas, avisos del servicio, indicaciones de recuperación y siguientes llamadas, los dos skills y sus referencias, los README en chino e inglés, el widget y la CLI; los códigos de error del canal también se unificaron como `pua_*`.
- Se conservaron la dependencia subyacente de WebDriverAgent, los módulos internos, las rutas del protocolo y las variables de entorno compatibles; se siguen reutilizando los datos existentes del dispositivo, la firma, las compilaciones y la ejecución.

- La búsqueda mediante desplazamiento realiza como máximo un gesto por llamada. Se detiene de inmediato si el objetivo está cubierto o es ambiguo; si sigue sin encontrar un control pulsable después de desplazarse, adjunta una captura para que el modelo la revise antes de decidir si continúa.
- La primera falta de progreso durante la comprobación explícita del desplazamiento devuelve una captura y cancela los gestos alternativos automáticos. Se conserva la compatibilidad con el parámetro antiguo de cantidad, pero ya no se sigue desplazando a ciegas.
- La alternativa con captura ahora cubre controles tapados, cambios del contexto de desplazamiento, discrepancias al releer el texto introducido y pantallas esperadas que no aparecen. La recopilación de listas también adjunta una captura si repite una página. Se reutilizan las observaciones e imágenes existentes, y se conservan el error original y las acciones ya ejecutadas; no se repiten acciones de negocio.

## 0.3.4 — 2026-10-08

- `docs/` y `evals/` pasaron a ser material de mantenimiento local y se retiraron de Git y de los paquetes de publicación; las instrucciones necesarias para operar la pantalla se trasladaron a las referencias de los skills.
- Se separaron los paquetes de código fuente y de instalación. El paquete de instalación excluye las pruebas Python de raíz, CI y los scripts de benchmarks y smoke de desarrollo; conserva el código fuente del widget, la configuración de compilación, el archivo de bloqueo de dependencias, las pruebas y la página compilada.
- Los README en chino e inglés especifican que WDA debe instalarse primero en el teléfono; se añadieron los pasos de firma, instalación e inicio, la guía oficial y los agradecimientos a Appium y WebDriverAgent.
- Se añadió al fondo del widget una cuadrícula de puntos grises estática y muy tenue, con un único degradado radial CSS repetido cada 20 px; no se agregaron nodos DOM, animaciones ni ciclos de dibujo en JavaScript.

## 0.3.3 — 2026-10-08

- La descripción breve del plugin pasó a ser «Let Codex control your iPhone» en inglés, para expresar que Codex opera el iPhone de la persona usuaria.

## 0.3.2 — 2026-10-08

- La pantalla de reserva negra muestra iconos lineales en gris claro según el estado: conexión en curso, sin conexión, bloqueo, autenticación, pausa o imagen no disponible.
- Dentro de la pantalla solo aparece el icono de estado centrado; el texto de ayuda se conserva únicamente para tecnologías de asistencia.
- El icono del plugin pasó a tener una base blanca redondeada, con pantallas de cristal verdes y azules, reflejos semitransparentes y sombra suave.
- Al actualizar se muestra el icono de conexión; si falla, se recupera el aviso anterior. Los botones de operación del teléfono siguen desactivados durante la pausa por autenticación.

## 0.3.0 — 2026-10-07

- El proyecto, el plugin, los skills, el registro MCP, el recurso de pantalla y la entrada del código fuente se unificaron bajo el nombre iPhone Use.
- Se reescribió el README en chino con la instalación, los requisitos, un prompt de instalación, las funciones y los detalles técnicos; se añadió un enlace a la documentación en inglés.
- Las instalaciones nuevas usan un directorio de ejecución genérico. Las actualizaciones siguen reutilizando la configuración y compilación existentes del dispositivo, y mantienen compatibilidad con las variables de entorno anteriores.
- Tras una instalación correcta se desactiva el registro del plugin antiguo. Solo se limpian entradas MCP que se hayan confirmado como pertenecientes a la instalación anterior; se conserva la caché necesaria para los trabajos en segundo plano.

## 0.2.7 — 2026-10-07

- Si falla la localización en la interfaz o el foco de entrada, primero se revisa una captura; se gestiona la obstrucción y se calculan las coordenadas de pulsación a partir de los píxeles. Se añadió el reenvío de bloques de imagen para evitar mostrar la captura como texto base64.
- Los errores por obstrucción ya no recomiendan pulsar directamente las coordenadas de un control en segundo plano. Los errores de foco indican que se debe elegir otro punto, evitando la repetición a ciegas y la transferencia prematura a la persona usuaria.
- Se distinguen el bloqueo de pantalla y la pausa por autenticación de una app: después de confirmar el desbloqueo, READY o la actualización manual reanudan la pausa por bloqueo correspondiente; la autenticación explícita y las pausas desconocidas de versiones antiguas requieren completar el aviso antes de continuar.
- El botón Actualizar vuelve a conectar y comprueba el desbloqueo. La actualización manual puede reanudar la pausa de vista previa iniciada al pulsar; una pausa nueva que ocurra durante la comprobación no se borra con un resultado anterior.
- Si no hay imagen, se conserva el marco del iPhone con la pantalla negra y la etiqueta pequeña «Sin conexión». En pausa se muestra el motivo; READY devuelve el estado de pausa.

## 0.2.6 — 2026-10-07

- El icono del plugin tomó como referencia una base redondeada y un teléfono en capas; se cambió a un fondo gris oscuro, una capa posterior gris y otra frontal blanca semitransparente, conservando una sombra 3D y un reflejo sutiles.
- `logo` y `composerIcon` comparten un SVG autocontenido. Se mantiene la nitidez vectorial y se actualiza la caché local de instalación con cada versión.

## 0.2.5 — 2026-10-07

- READY y las herramientas de pantalla del teléfono devuelven un identificador estable de sesión del widget, para que Codex reutilice en el chat actual la pestaña de pantalla que ya está abierta.
- La repetición de setup, la recuperación de conexión y las acciones de vista previa `open`, `pause` y `resume` reutilizan el mismo panel; el identificador de sesión no cambia al reconectar MCP.
- Se actualizaron las instrucciones de setup y uso: si ya existe un panel, se continúa allí; la herramienta de pantalla solo se llama cuando hay que volver a abrir un panel que se cerró.
- El espacio superior del widget aumentó de 14 px a 28 px y el fondo claro pasó a ser gris muy tenue `#f8f8f8`.
- La barra de estado superior y la barra inferior de herramientas usan fondo blanco, borde gris muy claro de 0,5 px y una sombra difusa sutil.
- Los puntos y el degradado se separaron en capas de animación: el tamaño de los puntos cambia en ciclos de 4 segundos y la alternancia y respiración del degradado conservan un ciclo de 8 segundos.

## 0.2.4 — 2026-10-07

- El patrón ondulado de puntos alterna cada 4 segundos en vez de cada 12, para que el cambio sea más visible.
- El radio de los puntos pasó del 6–23 % al 4–27 % del espacio de la cuadrícula. Los puntos grandes son algo mayores y los pequeños, menores, ampliando la variación de tamaño de la onda.
- Se corrigió la prioridad CSS de las capas de color y puntos: las animaciones se desactivan si el sistema reduce el movimiento y se pausan cuando la página queda oculta.

## 0.2.3 — 2026-10-07

- El indicador de gesto pasó a gris neutro, con borde fino y sombra leve, sin relleno azul.
- La pulsación se muestra durante 1,6 segundos: se contrae ligeramente, rebota, permanece y desaparece. El arrastre dura entre 1,6 y 2 segundos e incluye la pulsación inicial, el movimiento suave, la liberación con rebote y la pausa final.
- Las acciones consecutivas muestran indicadores independientes; una acción nueva no cancela antes de tiempo la anterior. La pausa por autenticación, el corte o cambio de flujo, la ocultación y la destrucción de la página limpian todos los gestos. Con movimiento reducido los indicadores permanecen quietos, pero siguen visibles durante el mismo tiempo.

## 0.2.2 — 2026-10-07

- La barra de herramientas adoptó iconos lineales redondeados y coherentes: Actualizar, Inicio y Captura usan la misma cuadrícula de 24×24, tamaño visible de 18 px y trazo de 1,75. La casa y la cámara tienen contornos suavemente redondeados.
- La flecha de actualización se une al arco en el mismo extremo y se corrigió el desajuste de su vértice; el icono de captura pasó a ser el contorno de una cámara.
- Se actualizaron la versión de la caché de instalación y la URI del widget a 0.2.2, con el fundido de bordes y el patrón ondulado de puntos de 0.2.1.

## 0.2.1 — 2026-10-07

- Siguiendo la imagen de referencia, los bordes central superior e inferior y las zonas medias de los laterales se difuminan de forma natural hasta ser transparentes; las cuatro esquinas conservan un resplandor azul cielo. El halo, el borde fino luminoso y los puntos comparten la misma máscara de fundido.
- La cuadrícula de puntos, antes uniforme, pasó a una textura ondulada que varía continuamente de tamaño y brillo. Tres texturas estáticas aparecen alternadamente con las capas de color. Solo se anima la opacidad; la animación se pausa al ocultar la página y queda quieta si se reduce el movimiento.
- Se actualizaron la versión de la caché del plugin y la URI del recurso del widget; el HTML autocontenido compilado se publica con el paquete.

## 0.2.0 — 2026-10-07

Optimización de latencia: reducir los datos que entran al contexto del modelo en cada ciclo, las llamadas necesarias para completar un paso y los timeouts que podían bloquear la tarea. Los detalles y las mediciones están en el material local de desarrollo.

- **Observaciones más compactas.** Se quitó el prefijo `XCUIElementType` de los nodos; no se repiten `name`/`value` cuando coinciden con el texto, se omiten los valores predeterminados y `rect` usa enteros `[x, y, width, height]`. En una pantalla de 99 nodos, el mismo resultado pasó de 18 424 a 6 868 bytes. `wda_find`, `scroll_find` y `collect_list` usan el mismo formato y ya no devuelven IDs de elemento. Cambió el formato de salida; los scripts que dependían de los campos anteriores deben actualizarse.
- **Las capturas llegan al modelo.** Los resultados para el modelo devuelven únicamente un bloque de texto JSON compacto y un bloque de imagen; ya no adjuntan `structuredContent`, porque Codex descartaba el bloque de imagen cuando había contenido estructurado. La captura primero se reduce con el `sips` del sistema a un JPEG de unos 722×1568, y devuelve el valor exacto de `image.pixel_to_point`; el PNG original se conserva con el mismo nombre y extensión `.png`.
- **Si falla el selector, se usan coordenadas de inmediato.** Si no encuentra el selector, no es único o se considera que el control no se puede pulsar o editar, el error adjunta la captura actual y un punto de coordenadas para la siguiente llamada. El texto se puede introducir después de pulsar el campo por coordenadas, llamando a `wda_type_text` sin selector. Si hay elementos del mismo nombre en la misma posición, o solo uno está en pantalla, se selecciona automáticamente el objetivo visible. El selector añadió `label_contains` e `index`.
- **Entrada de textos largos.** El texto se envía en segmentos de aproximadamente 200 caracteres y el timeout se calcula según su longitud; se evita que unos 450 caracteres acaben como «resultado incierto». Si se supera el presupuesto de tiempo de una llamada, se devuelve `continue_token` para continuar sin volver a enviar el texto. El batch también tiene un presupuesto y se detiene entre pasos cuando se agota.
- **La observación posterior espera a que termine la transición.** Antes de leer el árbol adjunto a una acción, WDA espera a que termine la animación, hasta un máximo de 0,8 segundos, para evitar árboles que mezclen dos pantallas.
- **Menos solicitudes.** La consulta de un elemento devuelve su tipo y posición en una llamada; el nodo raíz del código fuente de la página proporciona la app en primer plano y el tamaño de pantalla; las acciones por coordenadas reutilizan una caché breve del viewport. El clic por selector en la ruta optimizada pasó de 5 a 3 solicitudes; la observación del árbol, de 3 a 1.
- **Vista previa y respuesta.** Las solicitudes de fotogramas y la barra de herramientas responden directamente en el hilo de lectura; las operaciones largas del teléfono ya no congelan la vista previa. El hilo de transmisión almacena en caché el estado según la firma del archivo.
- **Rediseño del widget de pantalla.** En la parte superior se muestran el modelo del teléfono y el estado En vivo. Abajo hay botones de actualización, inicio y captura al portapapeles (solo los pulsa la persona usuaria; los dos últimos se desactivan durante la pausa por autenticación). Se rediseñó el efecto de luz de los bordes: sigue las esquinas grandes, se rellena más en las cuatro esquinas y alterna tres degradados estáticos principalmente azul cielo, con una capa de puntos blancos. Solo se anima la opacidad; los bordes suaves están integrados en una máscara y no dependen de un filtro blur en tiempo real. La interfaz sigue el tema claro u oscuro del host.
- **Mediciones.** `wda_metrics` ahora incluye, para cada herramienta, los bytes de la respuesta, los bytes por interfaz y el tiempo entre llamadas; también admite `reset`. Se añadió `scripts/benchmark.py` con una tarea fija en un dispositivo real.
- La parte visible para el modelo de las descripciones de herramientas se redujo de 29 568 a 21 419 bytes; los detalles de inicio y recuperación de los dos skills se movieron a referencias. El servidor tiene 19 herramientas: 17 para el modelo y 2 exclusivas de la app.
- La versión del manifiesto de dependencias de `tooling/` ya no cambia con la versión del plugin: el hash de su archivo de bloqueo determina si se reinstalan las dependencias USB. Una publicación sin cambios de dependencias ya no provoca otro `npm ci` en el siguiente inicio en frío.

## 0.1.14 — 2026-10-07

- Se conserva en memoria el último fotograma de vista previa cuando vence el lease de una ventana oculta, hay cortes de transmisión, fallan solicitudes o se reconecta el puente; el sondeo se reanuda al volver la visibilidad o la página desde la caché. La pausa por autenticación y el cierre siguen borrando todas las copias de la imagen, y las respuestas retrasadas anteriores a la pausa ya no pueden restaurarla.
- Solo se codifican los JPEG más recientes solicitados; se omiten los fotogramas idénticos, se evita repetir el diseño del mismo tamaño, el sondeo se limita a 4 fps y se usan timeouts y retrocesos acotados.
- Se eliminaron los registros de depuración del SDK que contenían fotogramas completos; los anillos de degradado redondeados permanecen estáticos y solo se anima la opacidad compuesta, con pausa cuando la página está oculta. Los cursores de arrastre usan transformaciones en vez de animar `left/top`.

## 0.1.13 — 2026-10-07

- Se añadió una Dynamic Island en la parte superior, posicionada según la proporción del lado corto y con un detalle sutil de cámara; en horizontal gira hacia el lado izquierdo del marco.
- Las cuatro bandas luminosas rectangulares se cambiaron por un halo de degradado que sigue el contorno redondeado, manteniendo el resplandor continuo y respetando la preferencia de reducir movimiento.
- El dispositivo se redujo un 4 % dentro del área disponible y se añadió espacio adaptable arriba y abajo; se conservaron la proporción de la imagen, el mapeo de coordenadas del cursor y las solicitudes de captura y acción.

## 0.1.12 — 2026-10-07

- La descripción del plugin y los skills de operación y setup indican que los chats nuevos inicializan READY de forma predeterminada; para tareas de texto se usa `recover=true, screenshot=false` y se continúa con la observación que devuelve READY.
- Si WDA no está iniciado, la conexión se rechaza o el estado es `not_ready`, se pasa a la rama de inicio mediante `status/start`. Se reutilizan trabajos `queued/running`, la configuración y las compilaciones válidas; se ejecuta `fetch/build` solo si falta algo. La tarea no termina ni se reinstala todo el sistema directamente.
- Los errores de servicio detenido conservan el código exacto y adjuntan `ready=false`, `initialization_required=true` y el siguiente paso de setup status; no se inicia ni reinicia el servicio automáticamente.
- Se distinguen el arranque en frío y la recuperación automática de XCTest con propiedad verificada; un Runner de larga duración no necesita finalizar con succeeded, pero la disponibilidad del servicio aún debe probarse con READY. Se conservan las restricciones de solo lectura y la prohibición de iniciar o reiniciar; los requisitos reales de la persona usuaria usan el flujo de preguntas «Listo, continuar».
- Abrir el widget o ver temporalmente una pantalla vacía no significa que READY o la tarea hayan fallado. Después de «enséñame primero» se continúa con la inicialización y la tarea autorizada, y solo se pausa si se pide explícitamente esperar una confirmación.

## 0.1.11 — 2026-10-07

- El degradado en los bordes de la pantalla y sus ondas permanecen visibles durante las pausas entre llamadas; los fotogramas ausentes temporalmente y la ocultación conservan el estado. La pausa por autenticación, la desconexión o cambio de flujo y el cierre de la página sí limpian el contenido.
- Se añadió un marco de iPhone adaptable con esquinas redondeadas, borde metálico fino, cristal negro y botones laterales. En vertical y horizontal mantiene la proporción completa; el cursor sigue mapeado al área interna de pantalla.
- El marco toma como referencia Apple Product Bezels y devices.css de la comunidad, pero se dibuja con CSS original: no cubre los píxeles reales ni añade recursos remotos o dependencias.
- Solo se ajustaron el estado y el diseño de la interfaz; no aumentaron las solicitudes de lectura u operación de WDA ni la frecuencia de sondeo. Se actualizó la versión del recurso para cargar el nuevo widget. El efecto de luz no demuestra que la tarea haya terminado.

## 0.1.10 — 2026-10-07

- Antes de ceder el control para una contraseña, Face ID o el desbloqueo del teléfono, se exige usar la función de preguntas disponible en el host. La primera opción queda fijada como «Listo, continuar» y la segunda puede ser «No puedo terminar por ahora»; se añadió un ejemplo exacto de los parámetros de preguntas asíncronas de Default.
- La vista previa y las operaciones del teléfono solo se reanudan tras una respuesta real de la persona usuaria; una opción preseleccionada, una respuesta inmediata de la herramienta o el paso del tiempo no indican que haya terminado. Se conserva el progreso y continúa el trabajo que no depende de la autenticación.
- Se sincronizaron las instrucciones de setup y operación, la referencia de autenticación, las indicaciones del widget y las instrucciones MCP.

## 0.1.9 — 2026-10-07

- Se corrigió la pantalla en blanco del widget en dispositivos reales: el socket de la transferencia usbmux quedaba en pausa y debía reanudarse cuando se montara el analizador HTTP. El canal USB MJPEG independiente ahora recibe fotogramas reales del teléfono.
- El fixture de regresión HTTP simula el socket pausado real para evitar que el problema pase inadvertido cuando solo se usan conexiones TCP nuevas; se conservaron la decodificación chunked, el control de presión y la limpieza de conexiones propias.
- Se actualizaron el recurso UI y la versión de instalación para renovar la caché, sin reiniciar WDA, crear una sesión ni aumentar las solicitudes de observación u operación del teléfono.

## 0.1.8 — 2026-10-07

- Siguiendo la imagen de referencia, el borde exterior luminoso se cambió por un resplandor azul violeta dentro de la pantalla; se difumina hacia dentro desde los cuatro lados y deja el centro nítido. Una respiración y un ligero cambio de tamaño representan la onda.
- El cursor queda por encima del efecto y conserva una interfaz solo de pantalla; se sigue respetando la preferencia de reducir movimiento. No cambian la frecuencia de sondeo ni la cantidad de operaciones o lecturas del teléfono.
- Se actualizaron la versión del recurso UI y la ruta de caché del plugin para evitar mostrar el efecto anterior.

## 0.1.7 — 2026-10-07

- Se añadió una app MCP de barra lateral que muestra solo la pantalla del teléfono. READY enlaza a ella de forma predeterminada y `wda_screen` permite abrirla, pausarla y reanudarla.
- Se usa un canal USB MJPEG independiente de WDA; la interfaz obtiene como máximo cinco fotogramas recientes por segundo. No añade solicitudes XCTest, XML o capturas de WDA, ni ocupa el bloqueo de operaciones; las imágenes solo permanecen en memoria.
- Durante las operaciones de IA se muestra un efecto de ondas en los bordes y se señala con un cursor circular la coordenada real de las pulsaciones y arrastres; el indicador de actividad no demuestra que una acción haya tenido éxito.
- Antes de ceder el control para una contraseña o Face ID, se detiene la vista previa y se borra la imagen. Solo se reanuda cuando la persona usuaria confirma que terminó; al ocultarse o cerrarse el widget, el lease vence de forma acotada.
- Se añadieron `wda_screen` y `wda_screen_frame`, esta última exclusiva de la app: en total, 17 herramientas para el modelo, 1 para la app y 2 skills.

## 0.1.6 — 2026-10-07

- Durante la instalación se registra `iphone_use` con el mismo nombre MCP estándar, para evitar el límite de presupuesto de las descripciones de herramientas compartidas del plugin Codex. Se conservan los skills, el servidor y los nombres de las herramientas; no se crea un segundo espacio de nombres.
- El schema publicado de batch elimina descripciones duplicadas y mueve selector y observe a `$defs`; conserva las ocho operaciones y todos sus parámetros, por debajo del umbral predeterminado de 5 KB para compresión con pérdida del host.
- Se conserva la validación cerrada de parámetros en tiempo de ejecución; se añadieron pruebas de referencias y equivalencia de schema, presupuesto de bytes y registro de instalación, validadas con la vinculación real de herramientas del modelo y la llamada nativa de metrics.

## 0.1.5 — 2026-10-07

- En las acciones normales, `observe=none` es el valor predeterminado; la entrada, Home, la activación de apps y el desplazamiento usan `verify=false` por defecto. Los batch conocidos continúan de forma optimista; si la siguiente acción necesita la pantalla, se incluye una observación y al final se comprueba explícitamente el resultado clave.
- El texto completo se introduce de una vez, sin probar primero con una versión corta; se reutiliza la comprobación del tipo editable y la lectura exacta solo se activa cuando hace falta. El envío y las escrituras inciertas no se repiten automáticamente; la autenticación sigue a cargo de la persona usuaria.
- `observation_id` es opcional para las coordenadas y las zonas de desplazamiento elegidas manualmente. Si se proporciona, solo se comprueban el mismo Runtime, la app y el viewport; se eliminan la comparación de imágenes completas, la huella de contenido y la caducidad de 30 segundos.
- El desplazamiento predeterminado realiza un solo gesto y no lee XML si no hay progreso. La validación explícita usa movimientos estables de controles; la actualización de números no cuenta como progreso. Se reutilizan las consultas de `scroll_find` y las páginas de `collect_list` para reducir lecturas repetidas.
- Al crear una sesión o ceder el control por primera vez, se configuran `waitForIdleTimeout=0` y `animationCoolOffTimeout=0` una sola vez; las acciones en una sesión ya activa no repiten esa configuración.
- Las consultas GET y POST conocidas de elementos se tratan como lecturas y se reintentan una vez de forma acotada, sin reiniciar el timeout. Los IDs antiguos de elemento no se reutilizan entre sesiones y las escrituras reales nunca se repiten automáticamente.

## 0.1.4 — 2026-10-07

- El inicio normal activa explícitamente la recuperación predeterminada. Los diagnósticos READY no disponibles y la recuperación en segundo plano devuelven un estado normal; los rechazos reales siguen siendo errores. Durante una recuperación no se puede declarar READY al servicio anterior.
- Las tres CLI devuelven un estado distinto de cero si READY es falso; el smoke de solo lectura prohíbe explícitamente iniciar una recuperación.
- Después de activar una app, se consulta la app real en primer plano durante un máximo de cinco segundos. Si falla, se conservan la evidencia de la acción, la app solicitada y la actual y la vía de recuperación.
- Se añadió evidencia de que no se ejecutó la acción cuando el objetivo está cubierto o fuera de pantalla. Si falla el desplazamiento seleccionado, se añade el motivo concreto, una observación nueva y el diagnóstico de contenido y geometría.
- Antes de desplazarse se limita la zona de overlays nativos, incluidos Sheet y Alert superpuestos. Después de cada gesto se comprueban el viewport y los overlays; si cambian, se detienen los gestos alternativos. Estas comprobaciones se mantienen aunque `verify=false`.
- Se revisaron los 11 errores de herramientas de T01 y los errores del script de evaluación. El skill ahora contempla overlays dibujados por la app, zonas dinámicas, la detención de lotes y las transiciones; no se añadieron reglas para una app financiera concreta.

## 0.1.3 — 2026-10-07

- El skill de operación añadió un flujo de intervención de la persona usuaria y ejemplos para contraseñas de apps, PIN, códigos de verificación y Face ID o Touch ID.
- Durante la intervención se pausan las acciones, lecturas y capturas del teléfono, y se conserva el progreso. Después de que la persona usuaria termine, se vuelve a localizar el control y se continúa, sin repetir envíos ya completados.
- Se distinguen la autenticación de una app, el bloqueo del teléfono y los fallos de WDA; el skill de setup y la referencia de solución de problemas apuntan al mismo flujo.

## 0.1.2 — 2026-10-07

- `swipe` añadió la opción de salida `observe`; aunque la observación se desactive, se sigue comprobando el progreso de forma predeterminada. Si no hay progreso, el error adjunta el estado actual, la evidencia de ejecución y un punto o diagnóstico de la zona de la lista.
- El selector especifica el soporte de `enabled` y codifica de forma segura saltos de línea, comillas, barras inversas y Unicode; NUL se rechaza antes de la operación y la regresión usa el analizador real de Apple Foundation.
- Se completaron los campos de finalidad del schema; los parámetros desconocidos y batch devuelven la ruta exacta, los campos permitidos y la evidencia de que no se ejecutaron pasos.
- READY reintenta una sola vez la lectura de una app en primer plano que dejó de ser válida. Los errores persistentes `local.pid` o XCTest Code 41 inician una recuperación asíncrona del servicio cuya propiedad se verificó; la deduplicación persistente, la espera de 120 segundos y la publicación acotada del PID evitan ciclos de reinicio.
- Si falla la lectura posterior a un toque, entrada, Home, activación o gesto, se conserva la evidencia de que la acción se ejecutó y se prohíbe repetirla automáticamente; las herramientas de lectura solo ofrecen una vía de recuperación.
- Se añadieron causas para errores de captura e instrucciones de recuperación y verificación en los skills; la sección de cuentas de Futu conserva su alcance original.

## 0.1.1 — 2026-10-07

- Home usa la interfaz de pantalla de inicio específica de WDA y comprueba que SpringBoard esté en primer plano; si no funciona o falla la lectura posterior, conserva evidencia explícita del estado.
- El desplazamiento elegido solo valida el área objetivo y los overlays nativos de toda la página; un carrusel fuera de esa zona no invalida la observación. Los toques por coordenadas conservan sus comprobaciones estrictas.
- Se añadió `wda_apps` para consultar la lista de apps instaladas, 36 apps populares verificadas por Apple y la Search API pública; incluye fuente, editor y estado de instalación.
- El skill ofrece una alternativa de scripts o Python cuando falla MCP; reutiliza la sesión y el bloqueo de operaciones y protege las acciones. Se añadieron reglas para completar y continuar tareas entre apps.
- Se corrigió la detección falsa de puerto ocupado cuando una conexión de reenvío USB cerrada estaba en TIME_WAIT; se añadieron instrucciones para recuperar XCTest Code 41.
- Se documentaron la investigación y los límites de atribución de los registros del final intermedio de T01. La sección de cuentas de Futu no cambió.

## 0.1.0 — 2026-10-06

Primera versión del plugin local para controlar WDA, con 2 skills, 15 herramientas MCP y guía de instalación y verificación READY.
