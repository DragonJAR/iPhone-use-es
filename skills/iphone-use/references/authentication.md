# Toma de control para contraseña y Face ID

Pide al usuario que tome el control solo cuando la observación actual o la herramienta muestren con claridad un bloqueo de autenticación. La página de contraseña de la app, el código de desbloqueo, el código de verificación, la confirmación de Face ID / Touch ID y la renovación del inicio de sesión los completa el usuario en el teléfono. Un árbol de elementos vacío o una captura negra no bastan, por sí solos, para demostrar que hay una autenticación en curso. Distingue antes, según el aviso actual, la pantalla bloqueada, la ocupación por la duplicación de pantalla, el contenido dibujado por la app y un fallo del canal.

## Distingue primero la capa del bloqueo

| Evidencia actual | Qué hacer |
| --- | --- |
| Aviso de inicio de sesión / contraseña / biometría de la app | Pide al usuario que complete la autenticación dentro de esa app. Pausa las llamadas al teléfono y, después, vuelve a observar la página de destino. READY no demuestra que la app haya iniciado sesión. |
| `phone_locked` o el iPhone realmente bloqueado | Pide al usuario que desbloquee el iPhone en persona y lo mantenga despierto; al terminar, vuelve a comprobar READY y observa la app de destino. |
| `local.pid.0` / `pua_foreground_unavailable` / XCTest Code 41 | Recupera el canal PUA según la skill de setup. No lo trates como una contraseña de app incorrecta. Solo si el sistema pide de verdad confianza o autenticación, deja que el usuario complete esa operación. |

## Qué explicar en el traspaso

Cuando haya un bloqueo claro de autenticación de la app, llama primero a `pua_screen(action="pause")`, detén la captura de la vista previa USB y vacía la imagen; después muestra al usuario el aviso de toma de control. Una pausa explícita por autenticación de la app no se levanta sola por READY / open. `phone_locked` ya registra `device_locked` y pausa; no hace falta otro pause explícito. Tras el aviso real de desbloqueo, un READY correcto levanta solo esa pausa de pantalla bloqueada. Que el usuario pulse actualizar también es una petición activa de reanudar la vista previa. Si actualizar confirma el desbloqueo, puede levantar la pausa App / unknown que había en el momento del clic; el modelo no puede pulsar por el usuario ese botón reservado a la app. Una pausa nueva ocurrida durante la comprobación no la borra una comprobación antigua. Una pausa antigua sin motivo se conserva como unknown. Durante la toma de control no sondees fotogramas, capturas ni la entrada del usuario.

Hay que llamar a la función de pregunta que el host tenga disponible para pedir la toma de control; no basta con escribir en un mensaje ordinario o en el final «responde continuar cuando termines». La pregunta indica la app real, el paso bloqueado, la acción que debe completar el usuario y el trabajo que seguirá después. La primera opción es siempre **«Listo, continuar»**; la segunda puede ser «No puedo terminar por ahora». La pregunta solo pide si ya se completó la operación en el teléfono; no recoge contraseña, PIN ni código de verificación.

En el modo Default de Codex, llama de preferencia a `functions.request_user_input_async`. Por ejemplo, cuando se muestra con claridad Face ID:

```json
{
  "questions": [{
    "title": "Esta app necesita verificación con Face ID. Completa la autenticación en el iPhone y quédate en la página de destino; cuando termines, elige «Listo, continuar» y seguiré leyendo el detalle restante.",
    "options": ["Listo, continuar", "No puedo terminar por ahora"]
  }]
}
```

Sustituye la app, el método de autenticación y el trabajo posterior según la evidencia actual. Si el teléfono está bloqueado, pide al usuario que lo desbloquee en persona y lo mantenga despierto. Si el host ofrece otra herramienta de pregunta, llámala según su schema real; el texto de la primera opción sigue siendo «Listo, continuar». No cambies de modo para poder llamar a la función de pregunta. Solo si el host actual no tiene de verdad una función de pregunta invocable, usa un aviso en texto y deja explícito el estado incompleto de «a la espera de la autenticación del usuario».

Una pregunta asíncrona vuelve de inmediato; eso no es el aviso de que el usuario terminó. Mantén la pregunta pendiente y espera a que el usuario envíe la opción o responda con claridad. Una opción preseleccionada, el retorno de la herramienta, el paso del tiempo de espera y la falta de respuesta no cuentan como terminado. Puedes seguir ordenando resultados ya obtenidos u otro trabajo que no dependa de la autenticación del teléfono; no puedes reanudar las llamadas al teléfono. Si no hay trabajo independiente, espera la entrada del usuario. No repitas la pregunta ni sondees el teléfono para consumir la espera, y no marques la tarea entera como terminada.

Describe solo el método de autenticación y la página que observaste de verdad. No adivines la contraseña o el PIN ni intentes saltarte la biometría. No pidas al usuario que envíe al chat la contraseña, el código de desbloqueo o el código de verificación, ni escribas credenciales en `pua_type_text`, en un batch, en un registro, en un script o en el código de reserva. Aunque el campo de contraseña se muestre como un TextField normal, lo escribe el usuario en persona; no decidas solo por el tipo SecureTextField.

Conserva la app / página actuales, el contenido ya obtenido, los pasos ya ejecutados, lo que falta y el límite de ejecución de la acción. No exijas una comprobación paso a paso previa para guardar el avance, y no registres credenciales de autenticación. Durante la toma de control, pausa las operaciones, la observación y las capturas de ese iPhone. Puedes ordenar los resultados y el avance ya obtenidos; no puedes sondear la entrada del usuario. Si Face ID falla, si pide cambiar a contraseña o si el código de verificación caduca, deja que el usuario siga el aviso real del teléfono. No dispares la verificación en serie ni reinicies una y otra vez la app o PUA.

## Continuar cuando la autenticación termina

Continúa solo cuando el usuario elija de verdad «Listo, continuar» o diga con claridad que la autenticación ya terminó. Para una autenticación de app o una pausa unknown, llama a `pua_screen(action="resume")`; si el dispositivo estaba bloqueado, vuelve a comprobar READY y, si tiene éxito, se reanuda sola la pausa de ese bloqueo. Que haya pasado un rato de espera no es terminar ni autorizar la reanudación. Después obtén una observación nueva y, a la vez, prepara el paso siguiente y comprueba la app en primer plano, el aviso de autenticación y la página de destino actual. El usuario puede haber cambiado de app, vuelto atrás, desplazado o completado de paso una operación posterior, así que no reutilices las coordenadas, el observation_id ni el ID de elemento anteriores a la toma de control. Busca el siguiente objetivo semántico según el estado nuevo. Si hace falta, lee con una captura el contenido de una página protegida; no vuelvas a iniciar sesión ni hagas una comprobación aparte en cada paso.

Si la autenticación sigue sin completarse, indica el paso que queda y espera; no ejecutes la acción bloqueada. Si el usuario elige «No puedo terminar por ahora» o dice que de momento no puede autenticarse, explica lo ya hecho y lo que queda, y conserva el punto de control de la toma de control. Si el usuario cancela, detén las operaciones posteriores. Si el teléfono o el canal fallan, recupera READY según la skill de setup y reutiliza directamente la observación nueva para preparar el paso siguiente. No confundas una sesión de app caducada con un servicio que haya que reiniciar.

Continúa el trabajo autorizado que quede según el estado nuevo. Un envío que el usuario ya completó durante la toma de control debe releerse antes de nada; no lo reenvíes, no pagues, no hagas otro pedido ni reejecutes toda la escritura o el lote. Que la autenticación haya terminado no significa que la tarea original haya terminado. Al final hay que contrastar todas las apps, los campos, el alcance cubierto y los archivos de salida.
