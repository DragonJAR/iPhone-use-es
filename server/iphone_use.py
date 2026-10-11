#!/usr/bin/env python3
"""Dependency-free local MCP stdio entrypoint for iPhone Use."""
import argparse
import base64
import collections
import fcntl
import inspect
import json
import math
import os
import queue
import re
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from wda_client import WDAClient, WDAError
from wda_controller import CALL_BUDGET, PhoneController, TYPING_FREQUENCY
from wda_setup import SetupManager, state_directory
from wda_apps import AppCatalog
from wda_screen import ScreenHub
import wda_image
from analytics import Analytics

PUAError=WDAError
VERSION="0.3.8"
SCREEN_URI="ui://iphone-use/phone-0.3.8.html"
# Codex scopes reuse to the host, chat, server and UI resource. A stable result
# ID keeps repeated READY/open/pause/resume calls in that chat on one panel,
# including after the MCP process reconnects; no device identifiers are needed.
SCREEN_SESSION_ID="iphone-use-screen"
SCREEN_META={"ui":{"csp":{"connectDomains":[],"resourceDomains":[]},"prefersBorder":False},"openai/ui":{"availableDisplayModes":["fullscreen"],"preferredDisplayMode":"fullscreen"}}
PROTOCOLS=("2025-11-25","2025-06-18","2025-03-26","2024-11-05")
# Seconds PUA may wait for animations to end before a post-action tree read; WDA_SETTLE_SECONDS overrides it.
SETTLE_SECONDS=0.8


def obj(properties,required=()):
    return {"type":"object","properties":properties,"required":list(required),"additionalProperties":False}


def string(description="",max_length=1000,enum=None):
    result={"type":"string","minLength":1,"maxLength":max_length}
    if description:result["description"]=description
    if enum:result["enum"]=enum
    return result


def num(low,high,kind="number"):
    return {"type":kind,"minimum":low,"maximum":high}


BOOL={"type":"boolean"}
SEL=obj({
 "label":string("Etiqueta de accesibilidad exacta, copiada de nodos recientes; se conservan saltos de línea y puntuación.",max_length=1000),
 "label_contains":string("Subcadena de la etiqueta, para textos largos o cambiantes. Distingue mayúsculas y se codifica de forma segura.",max_length=1000),
 "name":string("Identificador o name de accesibilidad exacto. El nodo omite name cuando es igual a label.",max_length=1000),
 "value":string("Valor de accesibilidad actual exacto; no es el texto a escribir. Omite valores que cambian solos.",max_length=1000),
 "type":string("Tipo de elemento exacto, como lo muestra el nodo, p. ej. Button. No es un bundle ID.",max_length=1000),
 "enabled":{"oneOf":[{"type":"boolean"},{"type":"string","enum":["true","false"]}],"description":"Filtro exacto opcional de enabled. No demuestra que se pueda pulsar."},
 "index":{**num(0,199,"integer"),"description":"Posición base 0 entre coincidencias, en orden del árbol, como las lista pua_find o un error ambiguous_target. Solo para elegir entre varias."},
 "predicate":string("Consulta NSPredicate, usada sola; index puede acompañarla. Prefiere campos exactos.",max_length=2000)})
SEL["description"]="Campos exactos o label_contains, o un predicate solo. rect, visible e in_viewport no son del selector. Coincidencias anidadas, o una sola en pantalla, eligen ese elemento; varias separadas devuelven candidatos con puntos de pulsación y un index."
SEL["examples"]=[{"label":"返回","type":"Button"}]
SEL["minProperties"]=1
OBS=string("Salida tras la acción; por defecto none. Usa tree/both si la siguiente decisión necesita la página resultante; screenshot devuelve una imagen. Es contexto del paso siguiente, no prueba de esta acción; expect/verify controlan la comprobación.",enum=["none","tree","screenshot","both"])
OBS["default"]="none"
EXPECT={"expect":SEL,"observe":OBS}
VERIFY={"type":"boolean","default":False,"description":"false ejecuta una vez y deja la comprobación para después. No repitas a ciegas una mutación incierta."}
REGION=obj({k:num(0 if k in ("x","y") else 1,10000) for k in ("x","y","width","height")},("x","y","width","height"))
REGION["description"]="Rectángulo en puntos del iPhone, no en píxeles. Omite region para el centro o usa los límites de la lista. Con verify=true debe caber en el viewport y en los modales."
SCHEMAS={
 "observe":obj({"mode":string("Salida independiente; por defecto tree. Aquí es mode; observe es la opción posterior. none no vale como modo independiente.",enum=["tree","screenshot","both"]),"include_invisible":BOOL,"max_nodes":num(1,500,"integer"),"expensive_visibility":BOOL}),
 "find":obj({"selector":SEL,"limit":num(1,30,"integer")},("selector",)),
 "tap":obj({"selector":SEL,"x":num(0,10000),"y":num(0,10000),"observation_id":string("ID opcional de este Runtime. Comprueba la app y el viewport, no la igualdad de píxeles de toda la página ni la antigüedad."),**EXPECT}),
 "swipe":obj({"direction":string("Movimiento del dedo; up suele mostrar filas posteriores. Por defecto up.",enum=["up","down","left","right"]),"region":REGION,"observation_id":string("ID opcional de este Runtime; comprueba la app y el viewport, no cambios de números, carruseles ni antigüedad."),"expect":SEL,"verify":{**VERIFY,"description":"false: un gesto, sin XML. true: comprueba una vez el ancla; si falla, devuelve una captura. Renovar números no es avance."},"max_attempts":{**num(1,2,"integer"),"default":1,"description":"Límite heredado: incluso 2 se detiene tras el primer gesto no demostrado."},"observe":OBS}),
 "type_text":obj({"selector":SEL,"text":string("Texto completo a escribir. Obligatorio con selector, salvo que se pase continue_token.",max_length=10000),"allow_newlines":BOOL,"submit":BOOL,"replace":BOOL,"verify":{**VERIFY,"description":"false escribe una vez, sin releer. true exige el valor exacto y no envía si falla. Los campos seguros los completa la persona."},**EXPECT,"continue_token":string("Token de un resultado con input_complete=false. Pásalo solo para escribir el resto de ese texto con sus opciones originales.",max_length=64)}),
 "press_button":obj({"name":string(enum=["home","volumeup","volumedown"]),"verify":VERIFY,**EXPECT},("name",)),
 "launch_app":obj({"bundle_id":string(),"verify":VERIFY,**EXPECT},("bundle_id",)),
 "wait":obj({"selector":SEL,"timeout_seconds":num(0,20)},("selector",)),
 "scroll_find":obj({"selector":SEL,"direction":string("Movimiento del dedo; up suele mostrar filas posteriores.",enum=["up","down","left","right"]),"max_swipes":{**num(0,10,"integer"),"default":1,"description":"0 solo consulta. Un valor positivo permite como máximo un deslizamiento; si no se resuelve, devuelve una captura."}},("selector",)),
 "collect_list":obj({"row_type":string(),"max_pages":num(1,10,"integer"),"end_selector":SEL}),
 "apps":obj({"query":string(max_length=100),"country":string(max_length=2),"source":string(enum=["auto","catalog","installed","apple"]),"limit":num(1,30,"integer")},("query",)),
 "doctor":obj({}),"ready":obj({"screenshot":{"type":"boolean","default":True,"description":"Comprueba también la captura; false mantiene las comprobaciones de status, sesión, source, viewport y desbloqueo."},"recover":{"type":"boolean","default":True,"description":"true encola un solo reinicio acotado de un PUA propio cuya pertenencia está verificada ante un fallo persistente de local.pid/XCTest. false solo si se prohibió reiniciar o es un diagnóstico: ready=false y state=recovery_required solo si un fallo del canal necesita reinicio; unas comprobaciones sanas pueden seguir devolviendo ready=true. En cola, state=recovering. Ni recovery_required ni recovering demuestran que esté listo."}}),"metrics":obj({"reset":{"type":"boolean","default":False,"description":"Devuelve los totales y abre una ventana de medición nueva."}}),
 "setup":obj({"action":string(enum=["discover","fetch","configure","build","start","stop","status"]),"udid":string(),"team_id":string(),"bundle_id":string(),"source_dir":string(max_length=4096),"local_port":num(1024,65535,"integer"),"device_port":num(1024,65535,"integer"),"job_id":string(),"wait_seconds":{**num(0,30),"description":"Espera acotada: start usa 20 s y status usa 0. Con job_id y 20 espera un start o una recuperación. Al agotar el tiempo el trabajo sigue; no lo reinicies."}},("action",))
}
# Each batch operation carries the same closed argument schema as its standalone tool.
BATCH_OPS=["tap","swipe","type_text","launch_app","press_button","wait","observe","scroll_find"]
SCHEMAS["batch"]=obj({"steps":{"type":"array","minItems":1,"maxItems":20,"items":{"oneOf":[obj({"op":{"type":"string","const":op},"args":SCHEMAS[op]},("op","args")) for op in BATCH_OPS]}}},("steps",))
SCHEMAS["ready"]["examples"]=[{"recover":True,"screenshot":False}]
SCHEMAS["screen"]=obj({"action":string("open, por defecto, muestra el iPhone en vivo. Pausa antes de una contraseña o Face ID; reanuda solo cuando la persona confirme.",enum=["open","pause","resume"])})
SCHEMAS["screen_frame"]=obj({"after_seq":num(0,9007199254740991,"integer"),"last_event_id":num(0,9007199254740991,"integer")})
SCHEMAS["screen_action"]=obj({"action":string("refresh reconecta la vista previa, home va a la pantalla de inicio y screenshot copia una captura al portapapeles del Mac.",enum=["refresh","home","screenshot"])},("action",))
# Tools the preview App calls itself; the model never sees them.
APP_TOOLS=("screen_frame","screen_action")
DESCRIPTIONS={
 "doctor":"Diagnostica Xcode, USB, la firma y PUA sin cambiar el iPhone. Empieza aquí la configuración.",
 "setup":"Primer uso en este chat: setup(status) antes de READY. Reutiliza un start o una recuperación activos, o inicia una vez con la config y el build existentes. start espera hasta 20 s; si sigue pendiente, consulta status con el mismo job_id y wait_seconds=20. Luego READY. Si faltan config, fuente o build, usa la skill iphone-use-setup. No reinstales ni pidas aprobación extra para un arranque autorizado; respeta la prohibición de reiniciar. Nunca desinstala apps.",
 "ready":"Primer uso en este chat: setup(status), reutiliza o inicia, espera y luego READY con recover=true. Solo ready=true permite tareas en el iPhone. Después reutiliza el canal sano. pua_unreachable o not_ready piden setup, no el fin de la tarea. recover=true cubre fallos de un runtime propio, no el arranque en frío. En recovering o recovery_required sigue la guía. No repitas acciones del teléfono.",
 "observe":"Controles recientes y/o una captura, con el viewport en puntos y un observation_id. type va sin el prefijo XCUIElementType; rect=[x,y,width,height] en puntos. name omitido equivale a label, value omitido repite el texto y enabled, visible e in_viewport omitidos son true. Un nodo listado no está demostrado como pulsable: cabeceras fijas y capas pueden cubrirlo. La captura está escalada: píxeles por image.pixel_to_point [x,y] = puntos.",
 "find":"Consulta campos del selector o un predicate de PUA sin pedir el árbol entero. Devuelve coincidencias en orden del árbol, con index, type, textos y rect. El selector de esta herramienta documenta los campos que acepta cualquier selector.",
 "tap":"Pulsa el elemento que resuelve un selector, tras comprobar que está en pantalla y es pulsable, o pulsa x/y con observation_id opcional. Si el selector falla, el error trae captura y puntos: pulsa x/y en la llamada siguiente. Se ejecuta una vez; expect activa una poscondición. Pide tree o both si la siguiente decisión necesita la página nueva.",
 "swipe":"Un gesto. verify=false y observe=none, los valores por defecto, omiten el XML. verify=true comprueba la geometría una vez; si falla, devuelve una captura sin otro gesto. Inspecciónala antes de actuar. La falta de avance no demuestra que la lista esté completa.",
 "type_text":"Escribe el Unicode previsto en un campo editable no seguro, sin ensayo corto ni relectura obligatoria. Omite selector para escribir en el campo que ya tiene el foco: pulsa el campo por x/y y luego escribe. Envía el texto entero en una llamada. Si input_complete=false, el continue_token se pasa solo en la siguiente; después corren verify, submit, expect y observe. verify=true relee el valor exacto antes de enviar. Los saltos de línea exigen intención; submit es false por defecto. No repitas una escritura o un envío inciertos.",
 "press_button":"Home usa una vez el endpoint de pantalla de inicio de PUA; por defecto no sondea el primer plano. verify=true comprueba SpringBoard y expect puede comprobar una página. El volumen no se puede verificar por significado.",
 "launch_app":"Activa una vez un bundle ID resuelto, de forma optimista por defecto. verify=true espera el primer plano hasta cinco segundos; expect comprueba la página prevista. Pide observación para la siguiente decisión. No repitas a ciegas una activación incierta.",
 "wait":"Espera acotada a que aparezca el objetivo. La presencia es una poscondición de interfaz, no prueba de que el negocio esté correcto.",
 "batch":"Hasta 20 pasos conocidos en una vuelta. Las acciones rutinarias sin verificar siguen con observe=none. Se detiene ante error, comprobación fallida, incertidumbre, envío sin expectativa explícita, texto largo inacabado (input_continues) o el tiempo de la llamada (time_budget). Continúa desde stopped_at sin repetir lo hecho. Observa el último paso si la siguiente decisión necesita la página.",
 "scroll_find":"Busca un objetivo pulsable con como máximo un deslizamiento. La ambigüedad o la oclusión detienen al momento; una consulta sin resolver tras el gesto devuelve una captura. Mira el final, la región y las capas antes de deslizar otra vez. No repitas a ciegas ni subas el límite.",
 "collect_list":"Recoge y deduplica filas de accesibilidad en páginas acotadas. Devuelve evidencia y límites de cobertura. Reconcílialos antes de declarar que el negocio está completo.",
 "metrics":"Totales del proceso, sin texto, datos de apps ni imágenes: tiempo y bytes HTTP de PUA, tiempo de herramienta, bytes de respuesta y la espera entre una respuesta y la siguiente petición (host, modelo y persona). reset=true abre una ventana nueva."
}
DESCRIPTIONS["apps"]="Resuelve un bundle ID real por el inventario del iPhone, alias verificados o la Search API de Apple. Consulta el nombre antes de abrir la app; no lo adivines. Los metadatos de la tienda no prueban la instalación: revisa installed_verified, publisher y country."
READS={"doctor","observe","find","wait","metrics","apps"}
READS.update(("screen","screen_frame"))
DESCRIPTIONS["screen"]="Abre o reutiliza el iPhone en vivo en el panel lateral de Codex. No actúa sobre el teléfono ni sus controles. Pausa la vista previa antes de una contraseña o Face ID y reanúdala solo tras la confirmación. READY también abre o reutiliza esta vista."
DESCRIPTIONS["screen_frame"]="Solo la app: vista previa en caché y eventos del cursor. No lee XML, no abre sesión ni toma el bloqueo de operación."
DESCRIPTIONS["screen_action"]="Solo la app: barra de la vista previa que pulsa la persona. refresh reconecta, home va a la pantalla de inicio y screenshot copia una captura al portapapeles del Mac. Se rechaza mientras la vista previa está en pausa por autenticación."


def undocumented(value):
    if isinstance(value,dict):return {k:undocumented(v) for k,v in value.items() if k not in ("description","examples")}
    if isinstance(value,list):return [undocumented(v) for v in value]
    return value


# Every selector has the same fields. pua_find publishes their documentation once; other
# tools publish the same closed shape with one line pointing there.
SEL_BRIEF={**undocumented(SEL),"description":"Selector; campos documentados en pua_find.selector."}
OBS_BRIEF={**undocumented(OBS),"description":"Salida posterior para la siguiente decisión; por defecto none."}


def published_schema(name):
    """Model-facing schema: same closed contract as SCHEMAS, with repeated documentation removed.

    Codex compacts a schema above 5KB and may drop argument branches, and all plugin
    tools share one description budget. Runtime validation keeps using SCHEMAS, without
    $ref parsing.
    """
    source=SCHEMAS[name]
    if name=="find":return source
    brief=name=="batch"
    counts={"selector":0,"observe":0}
    def count(value):
        if value==SEL:counts["selector"]+=1
        elif value==OBS:counts["observe"]+=1
        elif isinstance(value,dict):
            for item in value.values():count(item)
        elif isinstance(value,list):
            for item in value:count(item)
    count(source)
    shared={key for key,uses in counts.items() if uses>1}
    def publish(value):
        if value==SEL:return {"$ref":"#/$defs/selector"} if "selector" in shared else (undocumented(SEL) if brief else SEL_BRIEF)
        if value==OBS:return {"$ref":"#/$defs/observe"} if "observe" in shared else (undocumented(OBS) if brief else OBS_BRIEF)
        if isinstance(value,dict):return {k:publish(v) for k,v in value.items() if not (brief and k in ("description","examples"))}
        if isinstance(value,list):return [publish(v) for v in value]
        return value
    schema=publish(source)
    definitions={"selector":undocumented(SEL) if brief else SEL_BRIEF,"observe":undocumented(OBS) if brief else OBS_BRIEF}
    if shared:schema["$defs"]={key:definitions[key] for key in sorted(shared)}
    return schema


TOOLS=[{"name":"pua_"+name,"title":"Pua "+name.replace("_"," "),"description":DESCRIPTIONS[name],"inputSchema":published_schema(name),
        "annotations":{"readOnlyHint":name in READS,"destructiveHint":name not in READS,"idempotentHint":name in READS,"openWorldHint":name!="screen_frame"}} for name,schema in SCHEMAS.items()]
for tool in TOOLS:
    if tool["name"] in ("pua_ready","pua_screen"):
        tool["_meta"]={"ui":{"resourceUri":SCREEN_URI}}
    if tool["name"]=="pua_screen":
        tool.update(title="Pantalla del iPhone")
        tool["_meta"]["openai/ui"]={"entrypoints":[{"type":"thread"}]}
        tool["annotations"].update(readOnlyHint=False,destructiveHint=False,idempotentHint=True)
    if tool["name"][len("pua_"):] in APP_TOOLS:tool["_meta"]={"ui":{"visibility":["app"]}}
    if tool["name"]=="pua_screen_action":tool["annotations"].update(readOnlyHint=False,destructiveHint=False,idempotentHint=True)


def validate(value,schema,path="arguments"):
    if "oneOf" in schema:
        if isinstance(value,dict) and "op" in value:
            # Surface the chosen batch step's precise argument error instead
            # of hiding it behind the union of unrelated operation schemas.
            chosen=[candidate for candidate in schema["oneOf"] if candidate.get("properties",{}).get("op",{}).get("const")==value["op"]]
            if len(chosen)==1:return validate(value,chosen[0],path)
        matches=0
        for candidate in schema["oneOf"]:
            try:validate(value,candidate,path);matches+=1
            except WDAError:pass
        if matches!=1:raise WDAError("invalid_argument",f"{path} debe coincidir con exactamente un esquema de operación permitido.")
        return
    kind=schema.get("type")
    valid={"object":lambda:isinstance(value,dict),"array":lambda:isinstance(value,list),"string":lambda:isinstance(value,str),"boolean":lambda:isinstance(value,bool),"number":lambda:not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value),"integer":lambda:not isinstance(value,bool) and isinstance(value,int)}
    if kind and not valid[kind]():raise WDAError("invalid_argument",f"{path} debe ser {kind}.")
    if "const" in schema and value!=schema["const"]:raise WDAError("invalid_argument",f"Operación de {path} no válida.")
    if "enum" in schema and value not in schema["enum"]:raise WDAError("invalid_argument",f"Opción de {path} no válida.")
    if kind=="object":
        props=schema.get("properties",{})
        if schema.get("additionalProperties") is False and set(value)-set(props):raise WDAError("invalid_argument",f"Campos desconocidos en {path}: {', '.join(sorted(set(value)-set(props)))}. Usa solo los campos declarados.",details={"action_executed":False,"argument_path":path,"unknown_fields":sorted(set(value)-set(props)),"allowed_fields":sorted(props),"recovery":{"next_step":"Corrige estos campos con el esquema actual de la herramienta y llama una vez; no se ejecutó ninguna acción en el iPhone."}})
        if set(schema.get("required",[]))-set(value):raise WDAError("invalid_argument",f"Faltan campos obligatorios en {path}.")
        if len(value)<schema.get("minProperties",0):raise WDAError("invalid_argument",f"{path} no puede estar vacío.")
        for k,v in value.items():
            if k in props:validate(v,props[k],path+"."+k)
    if kind in ("number","integer") and not schema.get("minimum",-math.inf)<=value<=schema.get("maximum",math.inf):raise WDAError("invalid_argument",f"{path} está fuera de rango.")
    if kind=="string" and not schema.get("minLength",0)<=len(value)<=schema.get("maxLength",100000):raise WDAError("invalid_argument",f"{path} tiene una longitud no válida.")
    if kind=="array":
        if not schema.get("minItems",0)<=len(value)<=schema.get("maxItems",100000):raise WDAError("invalid_argument",f"{path} tiene un número de elementos no válido.")
        for i,v in enumerate(value):validate(v,schema["items"],f"{path}[{i}]")


def validate_semantics(name,args):
    from wda_controller import predicate
    for k in ("selector","expect","end_selector"):
        if k in args:predicate(args[k])
    if name=="tap":
        semantic="selector" in args
        coords=all(k in args for k in ("x","y"))
        if semantic==coords or (semantic and any(k in args for k in ("x","y"))):
            raise WDAError("invalid_argument","tap exige selector o x/y; observation_id es opcional.")
    if name=="type_text":
        if "continue_token" in args:
            if len(args)!=1:raise WDAError("invalid_argument","continue_token reanuda la llamada anterior con sus opciones; pásalo solo.",details={"action_executed":False})
            return
        if "text" not in args:raise WDAError("invalid_argument","type_text necesita text, o continue_token solo.",details={"action_executed":False})
        if any(ord(c)<32 and c not in ("\n","\r") or ord(c)==127 for c in args["text"]):raise WDAError("invalid_argument","El texto no admite caracteres de control.")
        if any(c in args["text"] for c in ("\n","\r")) and not args.get("allow_newlines",False):raise WDAError("newline_requires_intent","Los saltos de línea exigen una intención multilínea explícita.")
    if name=="launch_app" and not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+",args["bundle_id"]):raise WDAError("invalid_argument","Usa el bundle ID verificado de la app.")
    if name=="batch":
        for step in args["steps"]:validate_semantics(step["op"],step["args"])


def copy_png(directory,data):
    """Put a PNG on the macOS clipboard; the file exists only for the duration of the copy."""
    fd,name=tempfile.mkstemp(prefix=".clipboard-",suffix=".png",dir=directory)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as stream:stream.write(data)
        # The path travels as an argument, never inside the script text.
        done=subprocess.run(["/usr/bin/osascript","-e","on run argv","-e","set the clipboard to (read (POSIX file (item 1 of argv)) as «class PNGf»)","-e","end run",name],
                            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8,check=False)
        if done.returncode!=0:raise WDAError("clipboard_unavailable","La captura se obtuvo, pero macOS no la aceptó en el portapapeles.")
    except (OSError,subprocess.SubprocessError) as exc:
        raise WDAError("clipboard_unavailable","No se pudo copiar la captura al portapapeles.") from exc
    finally:
        try:os.unlink(name)
        except OSError:pass


def setting(name,default,low,high):
    """A bounded numeric tuning knob from the environment; anything else keeps the default."""
    try:value=float(os.environ.get(name,""))
    except ValueError:return default
    return value if math.isfinite(value) and low<=value<=high else default


class Runtime:
    def __init__(self,state_dir=None,base_url=None):
        root=state_directory(state_dir)
        self.state_dir=Path(root).expanduser().resolve();self.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True);self.state_dir.chmod(0o700)
        # Configuration is private runtime data, never a project file.
        configured_url=None
        config=self.state_dir/"config.json"
        if config.is_file():
            try:configured_url="http://127.0.0.1:"+str(json.loads(config.read_text()).get("local_port",18100))
            except (ValueError,OSError):pass
        self.base_url=base_url or os.environ.get("WDA_URL") or configured_url or "http://127.0.0.1:18100"
        self.client=WDAClient(self.base_url)
        self.phone=PhoneController(self.client,self.state_dir)
        self.setup_manager=SetupManager(self.state_dir,self.base_url)
        self.apps=AppCatalog(self.state_dir,self.setup_manager)
        self.screen=ScreenHub(self.state_dir)
        self.phone.screen=self.screen
        self.phone.settle_seconds=setting("WDA_SETTLE_SECONDS",SETTLE_SECONDS,0,2)
        self.phone.call_budget=setting("WDA_CALL_BUDGET_SECONDS",CALL_BUDGET,5,240)
        self.phone.typing_frequency=int(setting("WDA_TYPING_FREQUENCY",TYPING_FREQUENCY,5,120))
        # One entry per model-facing response: size, and the idle gap before its request.
        self.responses=collections.deque(maxlen=500)
        self._replied_at=None
        self._device_lookup=None
        self.analytics=Analytics(self.state_dir,VERSION)

    def call(self,name,args):
        started=time.monotonic();data=None;error=None
        try:
            data=self._dispatch(name,args)
            return data
        except WDAError as exc:
            error=exc.code
            raise
        except Exception:
            error="internal_error"
            raise
        finally:
            try:self.analytics.tool_result(name,args,data,(time.monotonic()-started)*1000,error)
            except Exception:pass

    def _dispatch(self,name,args):
        # PUA has one active session. Serialize independent Codex MCP processes
        # sharing this runtime, and share only this plugin's session identity.
        if not isinstance(name,str) or not name.startswith("pua_") or name[4:] not in SCHEMAS:raise WDAError("unknown_tool","Herramienta PUA desconocida.")
        validate(args,SCHEMAS[name[4:]]);validate_semantics(name[4:],args)
        if name in ("pua_screen","pua_screen_frame","pua_screen_action"):self.identify_device()
        # Cached preview polling does not share the PUA action/session lock.
        if name=="pua_screen_frame":return self.screen.frame(**args)
        if name=="pua_screen_action":return self.screen_action(args["action"])
        if name=="pua_screen":
            action=args.get("action","open")
            if action=="pause":self.screen.set_paused(True)
            elif action=="resume":self.screen.set_paused(False)
            return self.screen.start()
        lock_path=self.state_dir/"operation.lock"
        cache_path=self.state_dir/"session.json"
        with lock_path.open("a") as lock:
            lock_path.chmod(0o600)
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise WDAError("device_busy","Hay otra operación de iPhone Use en curso. Espera a que termine antes de continuar; no se ejecutó ninguna acción.")
            try:
                if cache_path.is_file() and hasattr(self.client,"session_id"):
                    try:
                        cached=json.loads(cache_path.read_text())
                        sid=cached.get("session_id","")
                        if cached.get("url")==self.base_url and isinstance(sid,str) and re.fullmatch(r"[A-Za-z0-9-]{1,128}",sid):self.client.session_id=sid
                    except (ValueError,OSError,AttributeError):pass
                return self._call(name,args)
            finally:
                sid=getattr(self.client,"session_id",None)
                if sid:
                    task_temp=self.state_dir/("session-"+str(os.getpid())+".tmp")
                    try:
                        fd=os.open(task_temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                        with os.fdopen(fd,"w") as stream:json.dump({"url":self.base_url,"session_id":sid},stream)
                        os.replace(task_temp,cache_path)
                    finally:
                        if task_temp.exists():task_temp.unlink()
                elif hasattr(self.client,"session_id") and cache_path.exists():cache_path.unlink()
                fcntl.flock(lock,fcntl.LOCK_UN)

    def identify_device(self):
        """Find the phone's model name for the preview header once, away from the request path."""
        if self._device_lookup is not None:return
        def lookup():
            udid=self.setup_manager.config.get("udid")
            # Nothing is configured yet: there is no phone to name, and nothing to look up.
            if not isinstance(udid,str) or not udid:return
            cache=self.state_dir/"device.json"
            try:
                known=json.loads(cache.read_text())
                if known.get("udid")==udid and isinstance(known.get("model"),str):
                    self.screen.device={"model":known["model"][:60]};return
            except (OSError,ValueError,AttributeError):pass
            try:
                model=next((d.get("model") for d in self.setup_manager.discover().get("devices",[]) if udid and d.get("udid")==udid),None)
                if isinstance(model,str) and model:
                    self.screen.device={"model":model[:60]}
                    fd=os.open(cache,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                    with os.fdopen(fd,"w") as stream:json.dump({"udid":udid,"model":model},stream)
            except Exception:
                # The header falls back to a generic name; the preview must never fail over a label.
                pass
        self._device_lookup=threading.Thread(target=lookup,name="wda-device-model",daemon=True)
        self._device_lookup.start()

    def screen_action(self,action):
        """Toolbar of the preview App: the user's own click, outside the model's tool sequence."""
        if action=="refresh":
            pause_id=self.screen.reconnect_pause_id()
            state=self.screen.restart()
            probe=WDAClient(self.base_url,timeout=2)
            try:
                ready=(probe.request("GET","/status").get("value") or {}).get("ready") is True
                if ready:
                    if probe.request("GET","/wda/locked").get("value") is False:
                        # Clicking refresh is the user's explicit request to resume.
                        self.screen.resume_after_unlock(pause_id,explicit=True)
                    else:self.screen.set_paused(True,reason="device_locked")
            except WDAError:ready=False
            finally:probe.close()
            return {"ok":True,"action":action,"service_ready":ready,**state,**self.screen.pause_status()}
        if self.screen.paused():
            raise WDAError("preview_paused","La vista previa está en pausa mientras la persona se autentica en el iPhone. No se hizo ninguna captura ni acción.",details={"action_executed":False})
        client=WDAClient(self.base_url,timeout=8)
        try:
            if action=="home":
                lock_path=self.state_dir/"operation.lock"
                with lock_path.open("a") as lock:
                    lock_path.chmod(0o600)
                    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError:raise WDAError("device_busy","El iPhone está en medio de otra operación. Inténtalo en un momento; no se envió nada.",details={"action_executed":False})
                    try:client.request("POST","/wda/homescreen",{})
                    finally:fcntl.flock(lock,fcntl.LOCK_UN)
                self.phone.external_action()
                return {"ok":True,"action":action}
            encoded=client.request("GET","/screenshot").get("value")
            try:data=base64.b64decode(encoded,validate=True)
            except (ValueError,TypeError):raise WDAError("invalid_response","Codificación de la captura no válida.")
            size=wda_image.png_size(data[:32])
            if size is None:raise WDAError("invalid_response","La captura de PUA no es PNG.")
            copy_png(self.state_dir,data)
            return {"ok":True,"action":action,"copied":True,"width":size[0],"height":size[1]}
        finally:client.close()

    @staticmethod
    def channel_fault(error):
        text=str(error).lower()
        if "not authorized for performing ui testing actions" in text or ("xctdaemonerrordomain" in text and "code=41" in text):
            return "xctest_authorization"
        if error.code=="pua_foreground_unavailable" or ("local.pid." in text and error.code=="stale element reference"):
            return "foreground_unavailable"
        return None

    def ready_once(self,screenshot):
        try:lock_pause=self.screen.locked_pause_id()
        except Exception:lock_pause=None
        status=self.client.request("GET","/status").get("value") or {}
        if status.get("ready") is not True:raise WDAError("not_ready","PUA no acepta comandos. Ejecuta pua_doctor y revisa el estado de setup.")
        if self.client.request("GET","/wda/locked").get("value") is not False:raise WDAError("phone_locked","Desbloquea el iPhone tú mismo, mantenlo activo y comprueba READY otra vez.")
        sid=self.client.ensure_session()
        observation=self.phone.observe("both" if screenshot else "tree")
        if observation.get("total_nodes",0)==0 and self.setup_manager.mirroring_running():raise WDAError("mirroring_conflict","iPhone Mirroring está activo y PUA muestra un árbol vacío. Cierra Mirroring, desbloquea el iPhone si hace falta y comprueba READY otra vez.")
        result={"ready":True,"state":"ready","proof":{"status_ready":True,"phone_unlocked":True,"session_usable":bool(sid),"foreground_resolved":True,"source_readable":True,"viewport_readable":True,"screenshot_readable":screenshot},"observation":observation}
        try:
            self.screen.resume_after_unlock(lock_pause)
            result["preview"]=self.screen.pause_status()
        except Exception:pass  # Display state must not invalidate a healthy control channel.
        return result

    def recovering_result(self,info,screenshot,recover,retried=False,cause=None):
        info=dict(info)
        job_id=info["job_id"]
        self.client.close();self.client.session_id=None;self.phone.reset()
        info.update(status_tool="pua_setup",status_arguments={"action":"status","job_id":job_id},next_tool="pua_ready",next_arguments={"screenshot":screenshot,"recover":recover},retry_after_seconds=1,replay_action=False)
        result={"ready":False,"state":"recovering","message":"La recuperación de un PUA propio sigue en segundo plano. Sondea el trabajo de setup indicado; cuando el servicio responda, ejecuta READY otra vez. Ninguna tarea del iPhone puede seguir hasta ready=true. No repitas la acción fallida.","action_executed":False,"category":"channel_runtime","session_read_retried":retried,"recovery":info}
        if cause is not None:result["cause"]=cause.as_dict()
        return result

    def ready(self,screenshot=True,recover=True):
        pending=self.setup_manager.pending_recovery() if hasattr(self.setup_manager,"pending_recovery") else None
        if pending and pending.get("job_id"):
            # The old listener may still answer before the owned worker stops
            # it. Never return that soon-to-be-invalid session as READY.
            return self.recovering_result(pending,screenshot,recover)
        retried=False
        try:return self.ready_once(screenshot)
        except WDAError as error:
            original=error
        fault=self.channel_fault(original)
        if fault=="foreground_unavailable":
            # The one retry is a fresh session/source read, never a replay of
            # a click, key, submission or an element ID from an older session.
            self.client.close();self.client.session_id=None;self.phone.reset()
            retried=True
            try:
                result=self.ready_once(screenshot)
                result["recovery"]={"state":"read_recovered","session_recreated":True,"replayed_action":False}
                return result
            except WDAError as error:
                original=error;fault=self.channel_fault(error)
        if original.code=="phone_locked":raise original
        pending=self.setup_manager.pending_recovery() if hasattr(self.setup_manager,"pending_recovery") else None
        if pending and original.code in ("pua_unreachable","not_ready","invalid session id","pua_foreground_unavailable","stale element reference","unknown error","invalid argument"):
            recovery={"ok":True,"recovery":pending,"job_id":pending.get("job_id")}
        elif fault and recover:
            recovery=self.setup_manager.recover()
        else:
            if fault:
                return {"ready":False,"state":"recovery_required","reason":"recovery_disabled","message":"El canal PUA/XCTest necesita recuperación, pero esta llamada prohibió reiniciar el servicio. No se inició ninguna recuperación. Reanuda con recover=true solo si las instrucciones actuales de la persona lo permiten.","action_executed":False,"category":"channel_runtime","session_read_retried":retried,"cause":original.as_dict(),"recovery":{"state":"disabled","next_tool":"pua_ready","next_arguments":{"screenshot":screenshot,"recover":True},"permission_note":"Respeta cualquier instrucción de la persona que prohíba reiniciar; no la anules automáticamente.","replay_action":False}}
            if original.code in ("pua_unreachable","not_ready"):
                # A stopped service needs setup/start, not an owned-listener restart.
                # Keep the failure truthful, but give the next read-only diagnostic.
                original.details.update(ready=False,action_executed=False,initialization_required=True,
                    recovery={"next_tool":"pua_setup","next_arguments":{"action":"status"},"replay_action":False,
                              "next_step":"Sigue la inicialización; no cierres la tarea del iPhone solo porque PUA no está iniciado. Revisa configured, jobs y service: reutiliza un start o una recuperación activos, o inicia una vez con la configuración y el build existentes si está permitido, y luego comprueba READY. Si faltan requisitos, usa la skill iphone-use-setup. Respeta una prohibición explícita de reiniciar o un modo de solo lectura."})
            raise original
        info=dict(recovery.get("recovery") or {})
        job_id=recovery.get("job_id") or info.get("job_id")
        if recovery.get("ok") and job_id:
            info["job_id"]=job_id
            return self.recovering_result(info,screenshot,recover,retried,original)
        info.update(next_steps=recovery.get("next_steps",[]),replay_action=False)
        raise WDAError("pua_recovery_required","No se inició la recuperación automática de PUA: "+str(recovery.get("error","no se pudo demostrar la propiedad del servicio")),details={"ready":False,"action_executed":False,"category":"channel_runtime","session_read_retried":retried,"cause":original.as_dict(),"recovery":info})

    def _call(self,name,args):
        if not isinstance(name,str) or not name.startswith("pua_") or name[4:] not in SCHEMAS:raise WDAError("unknown_tool","Herramienta PUA desconocida.")
        op=name[4:];validate(args,SCHEMAS[op]);validate_semantics(op,args)
        start=time.monotonic();error=None;activity=None
        try:
            if op not in ("doctor","apps","setup","metrics"):
                try:activity=self.screen.begin(op)
                except Exception:pass
            if op=="doctor":return self.setup_manager.doctor()
            if op=="apps":return self.apps.lookup(**args)
            if op=="setup":
                manager=self.setup_manager
                candidate_url=self.base_url
                if args["action"]=="configure" and "local_port" in args:
                    candidate_url="http://127.0.0.1:"+str(args["local_port"])
                    manager=SetupManager(self.state_dir,candidate_url)
                result=manager.setup(**args)
                if result.get("ok") and args["action"] in ("stop","configure","start"):
                    self.client.close();self.client.session_id=None;self.phone.reset()
                if result.get("ok") and args["action"]=="configure" and "local_port" in args:
                    self.base_url=candidate_url;self.setup_manager=manager
                    self.apps.setup_manager=manager
                    self.client=WDAClient(self.base_url);self.phone.client=self.client
                return result
            if op=="ready":
                try:self.screen.start()
                except Exception:pass
                return self.ready(**args)
            if op=="metrics":
                result=self.metrics()
                if args.get("reset"):
                    self.client.clear_metrics();self.phone.tool_records.clear();self.responses.clear();self._replied_at=None
                return result
            if op in ("tap","swipe","type_text","launch_app","press_button","batch","scroll_find","collect_list"):
                if self.client.request("GET","/wda/locked").get("value") is not False:raise WDAError("phone_locked","Desbloquea el iPhone tú mismo antes de operar; observa otra vez después.")
            return getattr(self.phone,op)(**args)
        except WDAError as exc:
            error=exc.code
            if exc.code=="phone_locked" or (exc.code=="not_editable" and exc.details.get("secure_field")):
                try:self.screen.set_paused(True,reason="device_locked" if exc.code=="phone_locked" else "authentication")
                except Exception:pass
            if op in READS:
                exc.details.setdefault("action_executed",False)
            if self.channel_fault(exc):
                exc.details.update(category="channel_runtime",recovery={"tool":"pua_ready","arguments":{"screenshot":False},"replay_action":False})
            raise
        except (ValueError,TypeError) as exc:error="invalid_argument";raise WDAError(error,str(exc)) from exc
        finally:
            if activity is not None:
                try:self.screen.end(activity)
                except Exception:pass
            self.phone.tool_records.append({"tool":name,"seconds":round(time.monotonic()-start,4),"error":error})

    def metrics(self):
        records=list(self.phone.tool_records);responses=list(self.responses)
        def grouped(items,fields):
            groups={}
            for item in items:
                entry=groups.setdefault(item["tool"],{"count":0,**{field:0 for field in fields}})
                entry["count"]+=1
                for field in fields:entry[field]=round(entry[field]+(item[field] or 0),4)
            return groups
        waits=[item["wait_seconds"] for item in responses if item["wait_seconds"] is not None]
        return {**self.client.metrics(),
                "tools":{"count":len(records),"seconds":round(sum(r["seconds"] for r in records),4),"errors":sum(bool(r["error"]) for r in records),
                         "by_tool":grouped([{**r,"errors":int(bool(r["error"]))} for r in records],("seconds","errors"))},
                "responses":{"count":len(responses),"text_bytes":sum(r["text_bytes"] for r in responses),"image_bytes":sum(r["image_bytes"] for r in responses),
                             "by_tool":grouped(responses,("text_bytes","image_bytes"))},
                "rounds":{"count":len(responses),"waits":len(waits),"wait_seconds":round(sum(waits),3),
                          "median_wait_seconds":round(statistics.median(waits),3) if waits else None,"max_wait_seconds":round(max(waits),3) if waits else None,
                          "scope":"Tiempo desde una respuesta de herramienta hasta la siguiente petición: host, modelo y persona juntos. Una espera larga puede ser de la persona, no del modelo."},
                "latency_scope":"Aquí se miden el HTTP, el tiempo de herramienta y el tamaño de las respuestas. La espera entre llamadas se observa, no se controla; este plugin no puede separarla en tiempo de modelo, host y persona."}

    def note_response(self,name,result,arrived):
        """Record what one model-facing response cost and how long the previous one waited for it."""
        if name=="pua_screen_frame":return
        content=result.get("content",[])
        self.responses.append({"tool":name if isinstance(name,str) else "invalid",
            "text_bytes":sum(len(item["text"].encode()) for item in content if item.get("type")=="text"),
            "image_bytes":sum(len(item["data"]) for item in content if item.get("type")=="image"),
            "wait_seconds":None if self._replied_at is None else max(0.0,arrived-self._replied_at)})

    def replied(self):self._replied_at=time.monotonic()

    def close(self):
        try:self.screen.close();self.client.close()
        finally:self.analytics.close()


def result_content(data,structured=False):
    """One compact JSON text block, plus the screenshot when the result carries one.

    structuredContent is left out on purpose: a host that receives it may give the model
    only that object and drop every content block, including the image.
    """
    content=[{"type":"text","text":json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(",",":"))}]
    image=data.get("image") or data.get("observation",{}).get("image")
    if not image and isinstance(data.get("error"),dict):image=data["error"].get("observation",{}).get("image")
    if not image and data.get("results"):
        last=data["results"][-1];image=last.get("image") or last.get("observation",{}).get("image")
    if image and Path(image["path"]).is_file():content.append({"type":"image","data":base64.b64encode(Path(image["path"]).read_bytes()).decode(),"mimeType":image.get("mimeType","image/png")})
    result={"content":content,"isError":"error" in data}
    if structured:result["structuredContent"]=data
    return result


def tool_result(runtime,params):
    name=params.get("name")
    try:
        data=runtime.call(name,params.get("arguments",{}))
        # The preview App reads structuredContent; frames never become model text.
        if name=="pua_screen_frame":return {"content":[],"structuredContent":data,"isError":False}
        result=result_content(data,structured=name in ("pua_screen","pua_screen_action"))
        if name in ("pua_ready","pua_screen"):
            result["_meta"]={"openai/widgetSessionId":SCREEN_SESSION_ID}
        return result
    except WDAError as exc:return result_content({"error":exc.as_dict()},structured=name=="pua_screen_action")
    except Exception as exc:
        print("iphone-use tool failure: "+type(exc).__name__,file=sys.stderr)
        return result_content({"error":{"code":"internal_error","message":"Falló la herramienta local; revisa el estado de setup o el stderr local.","uncertain":True}})


INSTRUCTIONS=(
 "PUA significa Phone Use Agent; todas las herramientas de iPhone Use usan el prefijo pua_. "
 "Lee la skill iphone-use-setup antes de configurar y la skill iphone-use para las tareas. Primer uso en este chat: pua_setup(action=status) antes de cualquier READY; reutiliza un servicio listo o un trabajo activo y, si no, inicia una vez con el build existente. start espera hasta 20 segundos; un trabajo pendiente usa status(job_id, wait_seconds=20) y luego pua_ready(recover=true, screenshot=false). Solo ready=true permite tareas en el iPhone; después reutiliza la observación de READY y el canal sano. "
 "Si READY falla con pua_unreachable o not_ready, sigue la inicialización: pua_setup(action=status), reutiliza un start o una recuperación activos o inicia una vez con la config y el build existentes, sondea ese trabajo hasta service.ready=true y vuelve a READY. Si faltan config, fuente o build, usa la skill de setup. "
 "recover=true es recuperación del runtime, no el arranque en frío. Con state=recovering sigue su trabajo de setup hasta que el servicio esté listo y vuelve a READY. Respeta un diagnóstico explícito o la prohibición de iniciar o reiniciar. "
 "La pantalla del iPhone en vivo abre o reutiliza el mismo panel lateral con READY. setup, la recuperación y la pausa o reanudación de la vista previa conservan ese panel. Usa pua_screen para reabrir un panel cerrado, no para refrescar uno ya abierto. Abrirlo no demuestra que esté listo ni pide otra confirmación. Los fotogramas del widget no sustituyen una observación del modelo ni la comprobación final. "
 "Cada resultado es un JSON compacto. En el árbol, type va sin el prefijo XCUIElementType y rect=[x,y,width,height] en puntos del iPhone. name omitido equivale a label, value omitido repite el texto y enabled, visible e in_viewport omitidos son true. Un nodo listado no está demostrado como pulsable: cabeceras fijas y capas pueden cubrirlo. "
 "La captura llega como imagen en el mismo resultado. Con functions.exec reenvía cada bloque de imagen con image(block) y los de texto con text(block.text); nunca text del resultado entero ni el base64. Si no puedes reenviar la imagen, usa view_image en image.path o error.observation.image.path. Está escalada: píxeles por image.pixel_to_point [x,y] = puntos del iPhone. La observación independiente usa mode; la salida de una mutación usa observe. "
 "Los selectores copian label, name, value y type de nodos recientes; usa label_contains para etiquetas largas o cambiantes. Las coincidencias anidadas en un punto, o una sola en pantalla, se resuelven solas. "
 "Inspeccionar la captura es el recurso ante una interfaz anómala: fallo de selector o de foco, búsqueda por desplazamiento sin resolver, falta de avance, contexto de desplazamiento cambiado o bloqueado, texto que no coincide o una expectativa de página fallida. Inspecciona primero la captura adjunta antes de otra mutación; si no hay una imagen usable, toma una con pua_observe(mode=screenshot). Decide según lo visible si paras, atiendes una ventana emergente, cambias región o dirección, pulsas x/y o sigues el trabajo pendiente. scroll_find no encadena otro deslizamiento tras una consulta sin resolver. tap_point y los candidatos localizan elementos, pero no demuestran que estén libres; cierra la ventana emergente visible antes de pulsar un objetivo de fondo cubierto. Para escribir, pulsa el campo editable visible y luego type_text con text y sin selector. Si un toque o el foco fallaron, elige un objetivo nuevo en una captura reciente: no repitas el mismo punto ni pases a la persona un problema rutinario de interfaz. No pruebes otras formas del selector ni vuelvas a leer el árbol primero. Corrige los errores de esquema, canal o autenticación con su propia recuperación. No repitas a ciegas una acción incierta. Resuelve un bundle ID desconocido con pua_apps. "
 "Ejecuta las acciones rutinarias de forma optimista: observe=none y verify=false son los valores por defecto. verified=false y verification_deferred=true son normales y no piden otra llamada de comprobación. Si la siguiente decisión necesita la página resultante, pide observe=tree o both en la acción e inspecciona el éxito anterior al planear ese paso. "
 "Encadena en batch los pasos ya conocidos; no agrupes deslizamientos especulativos hacia un objetivo desconocido. Inspecciona primero la página siguiente y usa una captura si el árbol truncado oculta el límite. expect o verify explícitos activan la comprobación del resultado clave. Envía el texto largo entero: si type_text devuelve input_complete=false, llámalo otra vez solo con continue_token. Un batch detenido por input_continues o time_budget continúa desde stopped_at. "
 "Comprueba los resultados críticos antes de informar de que terminaste. Reintenta o replantea solo tras observar un fallo definido. No repitas una escritura o un envío inciertos, ni una operación de varios pasos ya ejecutada. no_scroll_progress en una comprobación explícita no demuestra que los datos estén vacíos o completos. "
 "Para contraseñas de una app o Face ID llama a pua_screen(action=pause). phone_locked ya pausa la vista previa para desbloquear el iPhone; no sustituyas ese motivo con otra pausa. Deja de invocar herramientas del iPhone y usa la pregunta del host (request_user_input_async en Default). La primera opción debe ser exactamente «Listo, continuar» y la segunda exactamente «No puedo terminar por ahora». Espera la respuesta real de la persona: el retorno asíncrono o una preselección no confirman. Tras la respuesta real de que terminó, llama a pua_screen(action=resume) si la pausa es de autenticación de la app o es antigua o desconocida, y lee el estado reciente. Para desbloquear el iPhone ejecuta READY una vez; un READY correcto solo limpia la pausa device_locked que le corresponde. READY y open nunca limpian una pausa de autenticación de app ni una pausa desconocida. Continúa el trabajo pendiente desde ese estado reciente. "
 "action_complete y verified de una operación no significan que la tarea entera de la persona esté terminada. Sigue los entregables, informa del avance y continúa con herramientas mientras quede trabajo. Cierra solo al terminar o ante un bloqueo concreto. Si el enlace MCP no está disponible, usa el Runtime directo de la skill con el mismo bloqueo de operación."
)


def serve(runtime):
    """Read requests on this thread; run phone tools in order on one worker.

    The preview App polls frames several times a second. Answering those, pings and the
    catalog here keeps the preview live and the host responsive while a long phone
    operation is still running. Phone tools stay strictly sequential.
    """
    writing=threading.Lock()
    def send(response):
        line=json.dumps(response,ensure_ascii=False,allow_nan=False)
        with writing:print(line,flush=True)
    jobs=queue.Queue()
    def work():
        while True:
            job=jobs.get()
            if job is None:return
            ident,params,arrived=job
            result=tool_result(runtime,params)
            runtime.note_response(params.get("name"),result,arrived)
            send({"jsonrpc":"2.0","id":ident,"result":result})
            runtime.replied()
    worker=threading.Thread(target=work,name="wda-tools",daemon=True)
    worker.start()
    try:
        for line in sys.stdin:
            request=None
            try:
                if len(line)>1024*1024:raise ValueError("Request exceeds 1 MiB")
                request=json.loads(line,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
                if not isinstance(request,dict) or request.get("jsonrpc")!="2.0" or not isinstance(request.get("method"),str):raise ValueError("Invalid request")
                if "id" not in request:continue
                ident=request["id"]
                if isinstance(ident,bool) or not isinstance(ident,(str,int)):raise ValueError("Invalid identifier")
                params=request.get("params",{})
                if not isinstance(params,dict):raise WDAError("invalid_argument","params debe ser un objeto.")
                method=request["method"]
                if method=="initialize":
                    offered=params.get("protocolVersion")
                    result={"protocolVersion":offered if offered in PROTOCOLS else PROTOCOLS[0],"capabilities":{"tools":{"listChanged":False},"resources":{"listChanged":False}},"serverInfo":{"name":"iphone-use","version":VERSION},"instructions":INSTRUCTIONS}
                    try:runtime.analytics.start()
                    except Exception:pass
                elif method=="ping":result={}
                elif method=="tools/list":result={"tools":TOOLS}
                elif method=="resources/list":
                    result={"resources":[{"uri":SCREEN_URI,"name":"iPhone Use Screen","title":"Pantalla del iPhone","mimeType":"text/html;profile=mcp-app","_meta":SCREEN_META}]}
                elif method=="resources/read":
                    if params.get("uri")!=SCREEN_URI:raise WDAError("invalid_argument","URI de recurso de pantalla desconocido.")
                    html=(Path(__file__).resolve().parents[1]/"assets/phone-screen.html").read_text()
                    result={"contents":[{"uri":SCREEN_URI,"mimeType":"text/html;profile=mcp-app","text":html,"_meta":SCREEN_META}]}
                elif method=="tools/call":
                    arrived=time.monotonic()
                    if params.get("name") not in ("pua_screen_frame","pua_screen","pua_screen_action"):
                        jobs.put((ident,params,arrived));continue
                    # Preview polls, its toolbar and opening or pausing the panel never wait behind a phone operation.
                    result=tool_result(runtime,params)
                    if params.get("name")=="pua_screen":
                        runtime.note_response("pua_screen",result,arrived);runtime.replied()
                else:
                    send({"jsonrpc":"2.0","id":ident,"error":{"code":-32601,"message":"Method not found"}});continue
                response={"jsonrpc":"2.0","id":ident,"result":result}
            except WDAError as exc:response={"jsonrpc":"2.0","id":request.get("id") if isinstance(request,dict) else None,"error":{"code":-32602,"message":str(exc)}}
            except (ValueError,TypeError,KeyError):response={"jsonrpc":"2.0","id":request.get("id") if isinstance(request,dict) else None,"error":{"code":-32700 if request is None else -32600,"message":"Parse error" if request is None else "Invalid request"}}
            send(response)
    finally:
        # Finish the phone operation already accepted, then stop: its outcome must be reported.
        jobs.put(None);worker.join()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--state-dir");parser.add_argument("--url");parser.add_argument("--doctor",action="store_true");parser.add_argument("--ready",action="store_true")
    args=parser.parse_args();runtime=Runtime(args.state_dir,args.url)
    try:
        if args.doctor or args.ready:
            try:data=runtime.call("pua_doctor" if args.doctor else "pua_ready",{})
            except WDAError as exc:data={"error":exc.as_dict()}
            print(json.dumps(data,ensure_ascii=False));return 1 if "error" in data or (args.ready and data.get("ready") is not True) else 0
        serve(runtime);return 0
    finally:runtime.close()


if __name__=="__main__":sys.exit(main())
