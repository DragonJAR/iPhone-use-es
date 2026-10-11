# Plan de localización al español — iPhone Use

> Estado: la implementación está aplicada; los checks de escritorio pasan y la revisión cruzada independiente está cerrada. La captura auténtica en español y su revisión en un iPhone físico siguen pendientes.

## Objetivo y terminado

Traducir al español el contenido escrito por el proyecto que leen las personas y el modelo: documentación, instrucciones y descripciones del servidor, metadatos del plugin, mensajes de instalación y textos de la interfaz. Mantener la documentación inglesa en inglés y los datos literales que el modelo necesita para reconocer un iPhone o una app real.

El trabajo está terminado cuando:

- El contenido incluido en el alcance está en español y usa el glosario de este plan.
- Se preservan contratos, identificadores, datos reales y fixtures que prueban Unicode, seguridad o comportamiento.
- La interfaz compilada coincide con sus fuentes y las dos configuraciones del plugin conservan los valores compartidos.
- Pasan los checks del repositorio y se revisa manualmente la captura y los resultados de la búsqueda de CJK.
- Un revisor distinto de quien hizo los cambios confirma alcance, consistencia y validaciones.

## Hallazgos comprobados en el código

| Hallazgo | Consecuencia para el plan |
| --- | --- |
| `scripts/package.py` limita `shortDescription` a 30 caracteres; «Deja que Codex controle tu iPhone» tiene 33. | Usar «Codex controla tu iPhone» (24 caracteres) y dejar que el validador compruebe el límite. |
| `plugin.json` y `.codex-plugin/plugin.json` tienen estructuras distintas; el empaquetador valida sus campos compartidos. | Mantener cada esquema y sincronizar solo los valores compartidos traducidos. |
| CI reconstruye `assets/phone-screen.html` y exige que no haya diferencias después del build. | Editar las fuentes de `ui/`, reconstruir el HTML generado y versionar el resultado. Nunca editarlo a mano. |
| `scripts/check.sh` ya ejecuta unittest, validación de paquete, comprobaciones Node y `scripts/check_screen_ui.py`. | Ejecutar la secuencia una vez, después del build; no duplicar comandos ya incluidos. |
| `ui/tests/widget.test.mjs` comprueba «Live» y que el atributo `title` del estado bloqueado incluya `刷新`; no comprueba el título del documento. | Traducir el estado y su ayuda emergente; actualizar las expectativas de esos textos sin asumir cobertura sobre `index.html`. |
| Las pruebas incluyen alias reales de apps, respuestas reales simuladas de App Store, consultas de inyección, Unicode y una cadena de longitud exacta. | No traducir esos datos de prueba: no son textos de interfaz del proyecto. |
| El test de skills prohíbe `WDA` y `wda_` en Markdown de skills. Los títulos MCP `Pua <name>` también tienen una aserción exacta. | En las skills escribir «WebDriverAgent»; mantener los títulos generados `Pua <name>` y traducir las descripciones. |
| `assets/iphone-use-demo.png` muestra la interfaz en chino; en el árbol actual solo la enlaza `README.en.md`, mientras `README.md` ya no la incluye. | La captura española queda pendiente hasta disponer de un iPhone; entonces reemplazar el PNG e incluirlo en ambos README con texto alternativo en el idioma de cada documento. |
| El panel de PostHog del repositorio es configuración local. | Traducir sus etiquetas locales; no se actualiza ningún dashboard remoto en este trabajo. |

## Alcance

### Se traduce

- Documentación: `README.md` (chino → español), `CHANGELOG.md`, `ANALYTICS.md` y la prosa propia de `THIRD_PARTY_NOTICES.md`. `README.en.md` permanece en inglés y enlaza a `[Español](README.md)`; sus instrucciones de instalación apuntan al fork público `DragonJAR/iPhone-use-es`, usan el directorio `iPhone-use-es` y conservan las guardas de inicio seguro del README español. Aclara que los documentos enlazados solo están en español.
- Skills activos: texto explicativo de `skills/**/*.md`, incluidas las dos skills principales y sus referencias.
- Servidor MCP: prosa que se presenta a la persona o al modelo en `server/*.py`, incluidas instrucciones de inicialización, descripciones de herramientas, campos de esquema y mensajes de error. Traducir a «Pantalla del iPhone» los títulos propios del recurso/pantalla; conservar los títulos generados `Pua <name>`, fijados por una prueba. En los mensajes de setup, mantener completos los nombres literales de las rutas de iOS que ya ofrece el servidor; no mezclar idiomas dentro de una ruta.
- Interfaz: textos propios en `ui/index.html` y `ui/src/app.ts`; expectativas de textos visibles en `ui/tests/widget.test.mjs`.
- Metadatos del plugin: descripciones, prompt y demás prosa visible de `plugin.json` y `.codex-plugin/plugin.json`.
- Mensaje de instalación en `scripts/install.sh` y nombres/descripciones locales de `scripts/posthog-dashboard.json`.
- Captura `assets/iphone-use-demo.png`: reemplazo e inserción en ambos README pendientes de una captura real de la interfaz española.

### Se conserva tal cual

- `README.en.md` conserva el inglés. Se permiten los ajustes necesarios de URL de clonación, directorio, seguridad de setup y disponibilidad de documentos para que instale este fork; se preservan las demás URLs, comandos, nombres de herramientas, códigos, claves, schemas, bundle IDs y contratos MCP.
- `skills/iphone-use/references/apps.json`, nombres y alias reales de apps, resultados de App Store simulados y etiquetas chinas que sirven para que el modelo seleccione controles reales en un teléfono configurado en chino. También se conservan citas, comandos y valores literales que deben copiarse de una pantalla.
- Fixtures de `tests/**`, excepto expectativas de cadenas visibles del widget en `ui/tests/widget.test.mjs` y cualquier expectativa explícita de metadatos localizados que cambie intencionalmente. Se mantienen muestras CJK/Unicode, caracteres de control, consultas de inyección, cadenas con longitud contractual y datos que representan apps reales. `scripts/benchmark.py` mantiene su frase fija de medición.
- `assets/phone-screen.html` como archivo generado: solo cambia mediante el build de `ui/`.
- `LICENSE` y bloques de licencia upstream en `THIRD_PARTY_NOTICES.md`; solo se traduce el texto editorial que los presenta.
- Comentarios internos, logs y salida de desarrollo que no ve una persona usuaria; `mcp.json`, `.mcp.json` y `.agents/plugins/marketplace.json`, que no contienen prosa de producto que requiera traducción.

La prosa explicativa alrededor de una muestra se traduce; la muestra se conserva si representa texto literal de un dispositivo, una app, un protocolo o una prueba.

## Glosario breve

| Concepto | Forma acordada |
| --- | --- |
| Estado de conexión | «Conectando», «En vivo», «En pausa», «Sin conexión» |
| Inicio de iOS | «pantalla de inicio» |
| Vista del widget | «vista previa» |
| Desbloqueo | «desbloquear el iPhone» |
| Solicitud de autenticación | «Completa la autenticación» |
| Resultado listo | «Listo» |
| Respuesta positiva a la toma de control del teléfono | «Listo, continuar» |
| Respuesta si no puede completarla | «No puedo terminar por ahora» |
| Función, herramienta y producto | Conservar los nombres oficiales: Codex, iPhone Use, WebDriverAgent, Xcode, Appium, PostHog, AirDrop, Face ID, Touch ID, XCTest y MJPEG |
| Skill | Mantener `skill` al nombrar el artefacto; traducir la prosa circundante con naturalidad |

El par de opciones de toma de control debe coincidir exactamente en el servidor y en todas las instrucciones activas. El texto «En vivo» reemplaza «Live» como etiqueta visible; las dos variantes internas de conexión usan «Conectando».

## Principios DRY

- Este glosario es la única fuente de decisión terminológica; no crear traducciones alternativas ni mantener un segundo glosario por área.
- `README.md` es la única versión española y `README.en.md` la versión inglesa. Se mantienen sus enlaces cruzados sin duplicar documentos por idioma.
- `ui/` es la fuente del widget; `assets/phone-screen.html` se genera desde ella. Los textos de estados compartidos se referencian desde una sola tabla para no bifurcar el glosario. Los dos manifiestos conservan sus esquemas propios y comparten exactamente los valores de metadatos equivalentes.
- El par de respuestas de toma de control se define aquí y se normaliza en una pasada coordinada después de traducir en paralelo servidor y skills. La aceptación comprueba que todas las instrucciones activas usan los dos literales exactos.

## Descomposición y dependencias

Cada agente trabaja solo en los archivos asignados. La revisión final corresponde a una persona/agente que no haya editado esos archivos.

| Subtarea | Agente/rol sugerido | Depende de | Entrada → salida | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| Cerrar inventario de textos protegidos y aplicar este glosario | Coordinación | Auditoría de código | Hallazgos y términos → alcance/allowlist estable | Las etiquetas de dispositivo, fixtures, contratos y ejemplos que deben permanecer literales están identificados. |
| Traducir documentación raíz y mensaje de instalación | Agente de documentación | Glosario | README, changelog, analytics, notices, `scripts/install.sh` → prosa española | README principal en español; el inglés sigue inglés; enlaces relativos y comandos funcionan; bloques legales y ejemplos literales preservados. |
| Traducir las instrucciones y referencias de skills | Agente de skills | Glosario | `skills/**/*.md` → instrucciones españolas | Se preserva cada literal de selector/terminal; no se añade `WDA` ni `wda_` al Markdown; las referencias entre archivos siguen apuntando a rutas existentes. |
| Traducir metadatos y textos del servidor | Agente backend | Glosario | `plugin.json`, `.codex-plugin/plugin.json`, `server/*.py`, `scripts/posthog-dashboard.json` → valores y prosa en español | Esquemas intactos; opciones de autenticación idénticas; `shortDescription` dentro del límite; validador del paquete pasa. |
| Traducir la interfaz y sus expectativas | Agente de interfaz | Glosario | `ui/index.html`, `ui/src/app.ts`, `ui/tests/widget.test.mjs` → interfaz española y expectativas acordes | `lang`, título del documento, texto visible, `aria-label`, `alt`, `title`/ayudas y estados quedan localizados; las expectativas de widget reflejan el nuevo texto; los fixtures de protocolo no se reescriben. |
| Normalizar las opciones exactas de toma de control | Coordinación | Traducción de servidor y skills | Referencias activas a las opciones → literales españoles uniformes | Cuando una instrucción ofrezca opciones de toma de control, usa exactamente «Listo, continuar» y «No puedo terminar por ahora»; otras referencias pueden citar solo la opción que necesiten. No quedan variantes chinas. |
| Capturar la interfaz localizada | Agente de interfaz/documentación | Interfaz traducida | iPhone Use en ejecución → `assets/iphone-use-demo.png` | Captura auténtica en español, legible y sin datos privados; ambas descripciones alternativas siguen el idioma de su README. |
| Integrar, validar y revisar el conjunto | Coordinación + revisor independiente | Todas las subtareas; captura lista | Cambios integrados → resultado validado | Build, checks, revisión de CJK con allowlist y revisión cruzada completados; hallazgos corregidos antes de cerrar. |

Las traducciones de documentación, skills, servidor y widget pueden avanzar en paralelo tras fijar el glosario. La normalización del par de opciones depende de la entrega de servidor y skills; la captura depende de la interfaz localizada. La integración, el build y la revisión cruzada son posteriores a todas las ediciones. No se asigna a dos agentes el mismo archivo.

## Validación de la implementación

1. Revisar el diff por alcance y verificar que no cambien claves, nombres de herramientas, códigos, contratos ni muestras literales protegidas.
2. Instalar dependencias y compilar la interfaz: `npm ci --prefix ui --no-audit --no-fund` y luego `npm run build --prefix ui`.
3. Ejecutar `sh scripts/check.sh`. Esto cubre la suite Python, validación del paquete, sintaxis Node y pruebas/verificación del widget. Confirmar además que `assets/phone-screen.html` quedó actualizado y que CI aceptaría el artefacto generado.
4. Ejecutar un escaneo de caracteres Han sobre la lista explícita de archivos traducibles, sin recorrer `.git`, `.atl`, `node_modules` ni binarios. Revisar cada coincidencia contra una allowlist de etiquetas reales, apps, ejemplos y fixtures protegidos; no exigir cero CJK en todo el repositorio.
5. Revisar manualmente los dos primeros párrafos y enlaces de cada README, la captura, las opciones de autenticación y los valores compartidos de los manifiestos. En el widget comprobar `lang`, título, texto visible, `aria-label`, `alt` y tooltips: `widget.test.mjs` no cubre todos esos atributos. La inspección de la captura física queda pendiente hasta disponer de un iPhone.
6. Un revisor diferente verifica los hallazgos y el resultado de los checks. No repetir checks sin cambios posteriores que lo justifiquen.

## Riesgos y límites

- Si no se dispone de un iPhone para capturar la interfaz, la captura española queda pendiente y no se declara terminada esa parte; no se fabrica una captura que parezca real.
- La localización de `scripts/posthog-dashboard.json` solo modifica el archivo del repositorio. Cualquier actualización de un servicio remoto queda fuera del alcance.
- El HTML de pantalla debe incluirse en el cambio generado; dejarlo desactualizado fallará en CI.
- Las instrucciones operativas contienen texto exacto de controles de iOS y ejemplos reales. Traducir esos literales impediría al modelo encontrar el control correspondiente; se conserva el literal y se traduce su explicación.

## Estado de ejecución (2026-10-10)

| Área | Estado | Evidencia o pendiente |
| --- | --- | --- |
| README, documentación raíz e instalación | Completada | `README.md` y `README.en.md` apuntan al fork actual; los enlaces relativos del árbol resuelven. El README inglés permanece en inglés y conserva el inicio seguro. |
| Skills y datos protegidos | Completada | Prosa localizada; selectores de iOS y nombres reales de apps conservados. No aparece `WDA` ni `wda_` en Markdown de skills. El placeholder chino de `apps.md` se tradujo. |
| Servidor y metadatos | Completada | `scripts/package.py --validate-only`: 2 skills, 17 herramientas del modelo y 2 herramientas del widget validadas; los esquemas compartidos pasan. |
| Widget y artefacto | Completada | Build de `ui/` correcto; `assets/phone-screen.html` regenerado desde las fuentes; 31 pruebas del widget pasan. Las etiquetas de conexión comparten sus valores fuente. |
| Autenticación, pruebas y escaneo CJK | Completada | El par de opciones coincide exactamente; `scripts/check.sh` pasó 403 pruebas Python y la validación Node/paquete. Las coincidencias CJK restantes son selectores o datos reales protegidos. |
| Revisión cruzada final | Completada | El revisor independiente confirmó las correcciones finales, los literales protegidos y la coherencia del plan. |
| Captura española y revisión en iPhone físico | Pendiente | No hay un iPhone físico disponible en el host; `assets/iphone-use-demo.png` conserva la captura china y solo aparece en `README.en.md`. No se fabricará una captura. |

El README ahora instala el fork público del proyecto en `DragonJAR/iPhone-use-es`; el upstream `zhongerxin/iPhone-use` es el proyecto chino. Mantener las URL anteriores habría enviado a quien instala esta traducción al repositorio equivocado. El plan inicial ya se corrigió para reflejar esa distribución.
