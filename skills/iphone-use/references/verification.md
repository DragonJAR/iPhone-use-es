# Comprobar el resultado crítico

Las acciones habituales se ejecutan con optimismo y no se inserta una observación solo para verificar la acción anterior. Cuando preparar el paso siguiente necesita información de la página, reutiliza esa observación y juzga el avance de paso; ajusta o repite solo si está claro que no surtió efecto. Un `verified=false` ordinario solo indica que no hubo comprobación explícita. `expect`, `verify=true` y la relectura final sirven para un resultado crítico que importa de verdad; no hace falta verificar cada toque, cada cambio de página, cada despliegue o cada desplazamiento.

## Lista y detalle

`pua_collect_list` es un recolector de páginas, no el modelo de negocio de una app cualquiera. Confirma la página y el alcance del filtro con la lectura de la lista que la tarea ya necesitaba, y conserva el límite de la primera / última página, el motivo de parada, la regla de deduplicación y los campos que faltan. Al final concilia el alcance cubierto y el número de entradas según lo que pidió el usuario. Que no haya avance, que el árbol esté truncado o que se alcance el límite de páginas no equivale a tener el conjunto completo.

El mismo nombre puede corresponder a registros distintos; el número de pedido, la fecha, el estado y el importe reales pueden distinguirlos juntos. La deduplicación por defecto de la herramienta puede plegar registros reales que se muestran igual, y hay que explicar ese hueco real en la conclusión final. Después de abrir el detalle, lee directamente los campos necesarios; esa misma lectura basta para saber si es el detalle correcto, sin añadir una ronda solo para verificar la página.

Una cabecera fija, una capa flotante nativa o un panel dibujado por la app pueden tapar un objetivo que sigue en el árbol. Un error claro de occluded / offscreen no ejecutó el toque sobre el objetivo. El error ya adjunta la captura actual: si el objetivo se ve, pasa directamente a un toque por coordenadas; si está tapado, trata primero la oclusión. Si la captura abre la capa de compartir, trata la capa actual; no cierres y repitas la captura en bucle, ni afirmes que el plugin ya implementa una captura alternativa o una exportación interna de la app.

Si después de desplazar el objetivo sigue sin poder pulsarse, mira primero la captura y decide entonces si continúas. `scroll_find` se desliza como máximo una vez por llamada y se detiene de inmediato ante oclusión o ambigüedad. La primera falta de avance de una verificación explícita de desplazamiento, una zona de desplazamiento bloqueada, un cambio de contexto o una página repetida durante la recolección también adjuntan captura. El resultado anómalo no queda limitado por las opciones ordinarias de salida none/tree; si ya hay imagen, reutilízala. La falta de avance, por sí sola, no demuestra que la lista haya llegado al final ni que la recolección sea completa.

## Vigencia y totales

Ante un refresco asíncrono, espera solo mientras el contenido que la tarea necesita aún no se ha cargado. Lee los campos reales y anota la valoración, el valor liquidativo o la fecha de ejecución que muestra la página. Abrir la app hoy no significa que los datos sean de hoy.

Anota por separado cuentas y divisas; no sumes dos veces el detalle en moneda original y el total de la cuenta. «待确认», «实扣成功» y «份额已确认» son fases de negocio distintas; el éxito final se define según lo que pidió el usuario. El efectivo, las posiciones, lo que está en tránsito y las cuentas desconocidas conservan su pertenencia, y una diferencia que no se pueda conciliar se deja como desconocida. PUA no valora, no convierte divisas ni define el patrimonio neto.

Antes de escribir en una base de datos externa, contrasta con el conector de ese servicio el tipo y el significado de los campos. Tras escribir, una relectura de los objetivos críticos, el cuerpo, los campos y el número de duplicados basta para aceptar la entrega final. El plugin ofrece capacidad de interfaz del iPhone; no tiene una API genérica de Notion ni de documentos.

## Escritura y envío

Escribe de una vez el contenido completo que la tarea necesita; no empieces con un ensayo corto en chino o en ASCII. Una búsqueda, un filtro o una edición normales no se releen paso a paso. Cuando el paso siguiente necesite ver la página, juzga de paso si la escritura y la navegación surtieron efecto. Usa texto sintético solo para depurar un problema de escritura ya confirmado, y no uses como prueba el patrimonio ni los datos de cuenta reales del usuario.

El borrador final crítico puede releerse con exactitud mediante `pua_type_text(verify=true)`, o contrastarse con la observación que ya hacía falta antes de enviar: destinatario y contenido completo. Después de confirmar el contenido, envía una sola vez y comprueba al final, en el mensaje, el registro o la página de resultado, el contenido, el lugar y el número de duplicados. Una edición multilínea exige un TextView que se sepa adecuado; permitir saltos de línea no es permitir el envío.

Si aparece con claridad texto corrupto, un envío parcial, timeout, uncertain o una acción completada solo en parte, lee primero el campo, la sesión o el registro de envío reales y después ejecuta la parte que falte. No vuelvas a escribir ni reenvíes a ciegas. Que la herramienta haya aceptado la petición no demuestra el éxito de negocio, pero una acción normal tampoco obliga a detenerse en cada paso. La conclusión final debe tener evidencia del resultado crítico. La contraseña, el código de desbloqueo y el código de verificación los escribe el usuario en el teléfono.

Si la relectura de lo escrito no coincide, o no aparece la página esperada, adjunta la captura actual y juzga primero el foco, el texto real, el diálogo y el resultado del envío; después completa solo lo que falte. Si la captura falla, conserva el error original y la evidencia de ejecución; si falta la imagen, haz una lectura aparte y no sigas escribiendo o enviando por tu cuenta.

## Tiempo y trazabilidad

El observation ID y la captura pueden unir la acción y la observación necesarias. Por defecto se conservan las 100 imágenes más recientes; la evidencia crítica de aceptación se guarda, antes de limpiarla, en el directorio local que indique el usuario. El XML y los parámetros no se guardan solos como una traza completa. metrics solo conserva en el proceso actual un cómputo acotado de peticiones y herramientas, y no incluye el texto escrito ni valores de negocio. Si el usuario pide la traza completa, guarda en local solo la evidencia necesaria y exclúyela de Git.

Anota por separado el primer despliegue, el diagnóstico funcional, la tarea de negocio y la generación del informe. El tiempo HTTP, el número de acciones de interfaz, el número de llamadas a herramientas y el reloj de pared de la tarea son medidas distintas. Sin el cómputo correspondiente, no atribuyas todos los intervalos a la reflexión del modelo. Al valorar una optimización, mira a la vez el tiempo real de extremo a extremo y lo completo de la entrega final.
