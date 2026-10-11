"""Private, asynchronous Xcode / USB lifecycle for a pinned WebDriverAgent.

No shell command input is accepted. Long jobs survive the MCP process; stop only
signals a process group whose live leader carries this job's ownership token.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

WDA_COMMIT = "d17782422d55ff1e5e0ceb74eb1fd509cc0c35b6"
WDA_VERSION = "16.14.0"
WDA_REPOSITORY = "https://github.com/appium/WebDriverAgent.git"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = Path.home() / ".local/share/iphone-use"


def state_directory(explicit=None):
    """Prefer the new identity while reusing an existing installation's state."""
    configured = explicit or os.environ.get("IPHONE_USE_STATE_DIR") or os.environ.get("WDA_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    current = Path.home() / ".local/share/iphone-use"
    previous = Path.home() / ".local/share/iphone-use-wda"
    if not current.exists() and (previous / "config.json").is_file():
        return previous
    return current
ACTIVE_STATES = {"queued", "running"}
RECOVERY_COOLDOWN_SECONDS = 120
PID_PUBLICATION_GRACE_SECONDS = 5


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _redact(value):
    """Keep diagnostic hints while withholding Apple IDs and credential text."""
    value = str(value)
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted email]", value)
    value = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:bearer|basic)\s+\S+", r"\1[redacted]", value)
    value = re.sub(r"(?i)((?:password|passwd|authorization|access[_ -]?token|api[_ -]?key|secret)\s*[:=]\s*)([^\s,;]+)", r"\1[redacted]", value)
    value = re.sub(r"https?://[^/\s:@]+:[^/\s@]+@", "https://[redacted]@", value)
    return value


def _read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def _write_json(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(name)


def _run(argv, timeout=12, cwd=None):
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=False)
        return {"ok": result.returncode == 0, "code": result.returncode,
                "stdout": result.stdout, "stderr": _redact(result.stderr[-4000:])}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"ok": False, "code": None, "stdout": "", "stderr": _redact(error)}


def _fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def _node_supported(version):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return False
    major, minor, _ = map(int, match.groups())
    return (major == 20 and minor >= 19) or (major == 22 and minor >= 12) or major >= 24


def _diagnose(text):
    text = text.lower()
    cases = [
        (("not authorized for performing ui testing actions", "xctdaemonerror code=41", "xctdaemonerror code = 41"),
         "La autorización de automatización de interfaz de XCTest no está disponible aunque status.ready sea true. Revisa el estado de setup, detén solo el trabajo start propio de este plugin, inícialo de nuevo y comprueba pua_ready con una observación de interfaz actual. Conserva los servicios externos y pide a su dueño que los reinicie. Si la autorización sigue fallando, revisa Developer Mode y Enable UI Automation en el iPhone desbloqueado; no eludas los avisos de confianza ni de autenticación."),
        (("maximum number", "three apps", "3 apps", "0xe8008029"),
         "Límite de apps del Personal Team: revisa tú las apps de desarrollo en el iPhone. No desinstales nada solo; quita una app solo con la instrucción explícita de su dueño, o usa un equipo de pago."),
        (("no accounts", "authentication", "not logged in", "unable to log in", "session has expired"),
         "Abre Xcode Settings > Accounts e inicia sesión o actualiza la cuenta de Apple tú mismo. Nunca envíes contraseñas ni códigos de verificación al asistente."),
        (("no profiles", "provisioning profile", "requires a development team", "signing certificate"),
         "Revisa las cuentas de Xcode, el Team ID elegido y un bundle ID único. Permite la firma automática de Xcode y comprueba que este iPhone pertenece al perfil de aprovisionamiento."),
        (("expired", "0xe8008015", "0xe8008018"),
         "El certificado de firma o el perfil de aprovisionamiento pueden haber caducado. Actualiza la cuenta de Xcode, vuelve a compilar WebDriverAgent y reinstala el runner. Los perfiles de Personal Team suelen renovarse a los 7 días."),
        (("developer mode", "developermode"),
         "En el iPhone activa Settings > Privacy & Security > Developer Mode, reinicia y confirma el aviso tú mismo."),
        (("untrusted", "invalid code signature", "0xe800801c", "not trusted"),
         "En el iPhone abre Settings > General > VPN & Device Management y confía tú en el certificado de desarrollo; luego desbloquea el iPhone y reintenta."),
        (("locked", "unlock", "passcode"),
         "Desbloquea el iPhone tú mismo y mantenlo activo mientras arranca el runner de prueba de WebDriverAgent. No compartas el código."),
        (("not paired", "trust this computer", "pairing"),
         "Reconecta el USB, desbloquea el iPhone, acepta tú Trust This Computer y comprueba el emparejamiento en Xcode Window > Devices and Simulators."),
        (("address already in use", "eaddrinuse", "local forward port is occupied", "puerto local de reenvío está ocupado"),
         "El puerto local de reenvío está en uso. Reutiliza un WebDriverAgent ya sano, detén solo el trabajo propio de este plugin o configura otro puerto local; no mates procesos ajenos."),
    ]
    return [hint for needles, hint in cases if any(needle in text for needle in needles)]


class SetupManager:
    def __init__(self, state_dir: Path = None, base_url="http://127.0.0.1:18100"):
        self.state_dir = state_directory(state_dir).resolve()
        if self.state_dir == PLUGIN_ROOT or PLUGIN_ROOT in self.state_dir.parents:
            raise ValueError("El estado del runtime debe quedar fuera del checkout del plugin.")
        if any((ancestor / ".git").exists() for ancestor in (self.state_dir, *self.state_dir.parents)):
            raise ValueError("El estado del runtime debe quedar fuera de todos los checkouts de Git, para que las credenciales, la configuración del iPhone y los registros no entren en un repositorio.")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("La configuración de WebDriverAgent exige una URL base HTTP de loopback, sin credenciales ni ruta.")
        self.base_url = base_url.rstrip("/")
        self.port = parsed.port or 80
        self._workers = {}
        for directory in (self.state_dir, self.state_dir / "jobs", self.state_dir / "logs", self.state_dir / "runtime"):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)

    @property
    def config(self):
        return _read_json(self.state_dir / "config.json", {})

    @contextlib.contextmanager
    def _lock(self):
        path = self.state_dir / ".lock"
        with open(path, "a") as stream:
            path.chmod(0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def _validate_config(self, config):
        for key, pattern in (("udid", r"[A-Za-z0-9-]{8,64}"), ("team_id", r"[A-Z0-9]{10}"),
                             ("bundle_id", r"[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+){2,}")):
            if not isinstance(config.get(key), str) or not re.fullmatch(pattern, config[key]):
                raise ValueError(f"Indica un {key} explícito y válido; los Team ID de Apple tienen 10 letras o dígitos en mayúsculas y los bundle ID usan DNS inverso.")
        for key in ("local_port", "device_port"):
            value = config.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not 1024 <= value <= 65535:
                raise ValueError(f"{key} debe ser un entero entre 1024 y 65535.")
        if config["local_port"] != self.port:
            raise ValueError(f"local_port debe coincidir con el puerto de la URL base de MCP ({self.port}); actualiza la URL del plugin y reinicia MCP para cambiar de puerto.")
        return config

    def _source(self, config):
        source = Path(config["source_dir"]).expanduser().resolve()
        if not (source / "WebDriverAgent.xcodeproj/project.pbxproj").is_file():
            raise ValueError("Falta la fuente de WebDriverAgent. Ejecuta fetch o configura source_dir a un checkout fijado que ya exista.")
        revision = _run(["git", "-C", str(source), "rev-parse", "HEAD"])
        if not revision["ok"] or revision["stdout"].strip() != WDA_COMMIT:
            raise ValueError(f"La fuente de WebDriverAgent debe estar fijada en {WDA_VERSION} ({WDA_COMMIT}); los checkouts existentes no se cambian solos.")
        dirty = _run(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"])
        if not dirty["ok"] or dirty["stdout"].strip():
            raise ValueError("La fuente fijada de WebDriverAgent tiene cambios rastreados. Usa fetch para un checkout aislado y limpio; el trabajo existente se conserva.")
        return source

    @staticmethod
    def parse_devices(document):
        """Support Xcode's legacy and current CoreDevice JSON formats."""
        result = []
        for item in document.get("result", {}).get("devices", []):
            props = item.get("properties", {})
            hardware = props.get("hardware", item.get("hardwareProperties", {}))
            state = props.get("state", item.get("deviceProperties", {}))
            connection = props.get("connection", item.get("connectionProperties", {}))
            software = props.get("software", item.get("deviceProperties", {}))
            if hardware.get("reality") != "physical" or hardware.get("deviceType") not in {"iPhone", "iPad"}:
                continue
            version = software.get("osVersionNumber", "unknown")
            if isinstance(version, dict):
                version = version.get("stringValue", "unknown")
            developer = state.get("developerModeStatus", "unknown")
            if isinstance(developer, dict):
                developer = "enabled" if "enabled" in developer else "disabled" if "disabled" in developer else "unknown"
            result.append({"udid": hardware.get("udid", item.get("identifier")),
                           "core_device_id": item.get("identifier"), "name": state.get("name", "iPhone"),
                           "model": hardware.get("marketingName"), "ios_version": version,
                           "pairing_state": connection.get("pairingState", "unknown"),
                           "connection_state": connection.get("state", connection.get("tunnelState", "unknown")),
                           "transport": connection.get("transportType", "unknown"),
                           "developer_mode": developer, "unlocked": "user_check_required"})
        return result

    def discover(self):
        fd, name = tempfile.mkstemp(prefix="devices-", suffix=".json", dir=self.state_dir)
        os.close(fd)
        try:
            probe = _run(["xcrun", "devicectl", "list", "devices", "--json-output", name, "--timeout", "8"], timeout=12)
            document = _read_json(name, {})
            devices = self.parse_devices(document)
            if not probe["ok"] or not document:
                fallback = _run(["xcrun", "xcdevice", "list", "--timeout", "5"], timeout=9)
                try:
                    devices = [{"udid": item["identifier"], "name": item.get("name"), "model": item.get("modelName"),
                                "ios_version": item.get("operatingSystemVersion"), "available": item.get("available"),
                                "pairing_state": "unknown", "developer_mode": "unknown", "unlocked": "user_check_required"}
                               for item in json.loads(fallback["stdout"])
                               if not item.get("simulator") and item.get("platform") == "com.apple.platform.iphoneos"]
                except (ValueError, TypeError, KeyError):
                    pass
            return {"ok": bool(document) or bool(devices), "devices": devices,
                    "selected_udid": self.config.get("udid"), "error": probe["stderr"] if not probe["ok"] else None,
                    "next_steps": [] if devices else ["Conecta el iPhone por USB, desbloquéalo, acepta tú Trust This Computer y abre Devices and Simulators en Xcode."]}
        finally:
            with contextlib.suppress(OSError):
                os.unlink(name)

    def _probe_status(self):
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            request = urllib.request.Request(self.base_url + "/status", headers={"Accept": "application/json"})
            with opener.open(request, timeout=1.5) as response:
                document = json.loads(response.read(1024 * 1024))
            value = document.get("value", {})
            return {"reachable": True, "ready": value.get("ready") is True, "wda": value,
                    "next_step": "Ejecuta la comprobación de sesión MCP y de source antes de dar el iPhone por usable."}
        except (OSError, ValueError, urllib.error.URLError) as error:
            return {"reachable": False, "ready": False, "error": _redact(error)}

    def mirroring_running(self):
        if sys.platform != "darwin":
            return False
        return _run(["pgrep", "-f", "/iPhone Mirroring.app/Contents/MacOS/iPhone Mirroring"], timeout=2)["ok"]

    def doctor(self):
        binaries = {name: shutil.which(name) for name in ("xcodebuild", "xcrun", "git", "node", "npm")}
        xcode = _run(["xcodebuild", "-version"]) if binaries["xcodebuild"] else {"ok": False, "stdout": "", "stderr": "Hace falta el Xcode completo."}
        developer_dir = _run(["xcode-select", "-p"])
        node_version = _run(["node", "--version"])["stdout"].strip() if binaries["node"] else ""
        npm_version = _run(["npm", "--version"])["stdout"].strip() if binaries["npm"] else ""
        discovery = self.discover() if xcode["ok"] else {"devices": [], "ok": False}
        config = self.config
        chosen = next((device for device in discovery["devices"] if device.get("udid") == config.get("udid")), None)
        checks = {"macos": sys.platform == "darwin", "full_xcode": xcode["ok"],
                  "git": bool(binaries["git"]), "node": _node_supported(node_version),
                  "npm": bool(re.match(r"^(1[0-9]|[2-9][0-9])\.", npm_version)),
                  "configured": bool(config), "selected_device_present": bool(chosen),
                  "paired": chosen.get("pairing_state") == "paired" if chosen else False,
                  "developer_mode": chosen.get("developer_mode") == "enabled" if chosen else False}
        try:
            self._validate_config(config)
            source = self._source(config)
            checks["pinned_source"] = True
        except (ValueError, KeyError):
            source = None
            checks["pinned_source"] = False
        next_steps = []
        if not checks["full_xcode"]:
            next_steps.append("Instala el Xcode completo, ábrelo para aceptar la licencia e instalar componentes, y selecciónalo con xcode-select.")
        if not checks["node"] or not checks["npm"]:
            next_steps.append("Instala Node.js 20.19+ / 22.12+ / 24+ con npm 10+ para el reenvío USB en loopback.")
        if not checks["configured"]:
            next_steps.append("Descubre el iPhone y configura su UDID explícito, tu Team ID de Apple y un bundle ID único en DNS inverso.")
        if config and not chosen:
            next_steps.append("Reconecta por USB el iPhone seleccionado y confirma su UDID en Xcode Devices and Simulators.")
        if not checks["paired"]:
            next_steps.append("Desbloquea el iPhone y acepta tú Trust This Computer; comprueba el emparejamiento en Xcode.")
        if not checks["developer_mode"]:
            next_steps.append("Activa en el iPhone Settings > Privacy & Security > Developer Mode, reinicia y confírmalo tú mismo.")
        if not checks["pinned_source"]:
            next_steps.append("Ejecuta fetch para la fuente aislada y fijada de WebDriverAgent de Appium, o reutiliza un checkout sin cambios en el commit fijado.")
        next_steps.extend(["En Xcode Settings > Accounts, inicia sesión tú y elige tu equipo de firma; no compartas contraseñas ni códigos de verificación.",
                           "Mantén el iPhone desbloqueado y activo. Activa Settings > Developer > Enable UI Automation y, si iOS lo pide, confía en el certificado de desarrollo en VPN & Device Management."])
        live = self._probe_status()
        profile = self._profile_status()
        if profile.get("expired"):
            next_steps.append("El perfil de aprovisionamiento compilado ha caducado. Actualiza la cuenta de firma de Xcode y vuelve a compilar antes de start.")
        mirroring = self.mirroring_running()
        if mirroring:
            next_steps.append("Cierra iPhone Mirroring si el iPhone muestra la pantalla de bloqueo de uso del Mac o WebDriverAgent tiene un árbol de accesibilidad vacío, y comprueba READY otra vez.")
        return {"ok": all(checks.values()), "checks": checks, "devices": discovery["devices"],
                "iphone_mirroring_running": mirroring,
                "selected_device": chosen, "xcode_version": xcode["stdout"].strip(),
                "developer_dir": developer_dir["stdout"].strip(), "binaries": binaries,
                "node_version": node_version, "npm_version": npm_version, "provisioning": profile,
                "source_dir": str(source) if source else config.get("source_dir"),
                "wda_version": WDA_VERSION, "wda_commit": WDA_COMMIT, "runtime": str(self.state_dir),
                "service": live, "next_steps": next_steps,
                "manual_checks": {"apple_account_login": "user_check_required", "certificate_trust": "user_check_required", "phone_unlocked": "user_check_required"},
                "signing_note": "Personal Team tiene un número limitado de apps de desarrollo (normalmente 3) y un aprovisionamiento de corta duración (normalmente 7 días). Nunca desinstales apps ajenas de forma automática."}

    def _profile_status(self):
        profiles = list((self.state_dir / "derived_data/Build/Products").glob("Debug-iphoneos/*.app/embedded.mobileprovision"))
        if not profiles:
            return {"known": False, "note": "Aún no hay un perfil de aprovisionamiento compilado; la firma de Xcode y la confianza del certificado en el iPhone las debe verificar la persona."}
        profile = max(profiles, key=lambda path: path.stat().st_mtime)
        decoded = _run(["security", "cms", "-D", "-i", str(profile)], timeout=5)
        try:
            values = plistlib.loads(decoded["stdout"].encode())
            expiration = values["ExpirationDate"].replace(tzinfo=dt.timezone.utc)
            return {"known": True, "expires_at": expiration.isoformat(), "expired": expiration <= dt.datetime.now(dt.timezone.utc),
                    "note": "La caducidad del aprovisionamiento no comprueba la confianza del certificado en el iPhone ni el inicio de sesión de la cuenta de Apple."}
        except (ValueError, KeyError, AttributeError):
            return {"known": False, "note": "No se pudo decodificar el perfil de aprovisionamiento compilado; verifica la firma en Xcode."}

    def _owned(self, job, *, base_url=None):
        pid = job.get("pid")
        if not isinstance(pid, int) or pid <= 1 or not job.get("owner_token"):
            return False
        entrypoint = job.get("worker_entrypoint", str(Path(__file__).resolve()))
        if not isinstance(entrypoint, str) or not entrypoint or not Path(entrypoint).is_absolute() or Path(entrypoint).name != "wda_setup.py":
            return False
        try:
            if os.getpgid(pid) != pid:
                return False
        except ProcessLookupError:
            return False
        process = _run(["ps", "-ww", "-p", str(pid), "-o", "command="], timeout=2)
        command = process["stdout"]
        # Private job metadata identifies the original worker even when this
        # manager now runs from a different Codex install or upgraded cache.
        marker = f" {entrypoint} --worker {self.state_dir} {job['id']} {job['owner_token']}"
        owned = process["ok"] and marker in command and (marker + " " in command or command.rstrip().endswith(marker))
        if base_url is not None:
            # Old installs did not record base_url, but every worker argv did.
            # Recovery must prove which endpoint that live worker owns.
            endpoint = marker + " --base-url " + base_url
            owned = owned and (command.rstrip().endswith(endpoint) or endpoint + " " in command)
        return owned

    def _listener_pids(self, timeout=3):
        """Return proven loopback listeners, or None when proof is unavailable.

        lsof is used only for ownership evidence; a port number is never a
        signal target. Refuse wildcard/non-loopback listeners on the same port.
        """
        query = _run(["lsof", "-nP", f"-iTCP:{self.port}", "-sTCP:LISTEN", "-Fpn"], timeout=timeout)
        if not query["ok"]:
            return [] if query.get("code") == 1 and not query.get("stdout") and not query.get("stderr") else None
        current_pid, listeners = None, set()
        accepted = {f"127.0.0.1:{self.port}", f"[::1]:{self.port}"}
        for line in query["stdout"].splitlines():
            if line.startswith("p"):
                try:
                    current_pid = int(line[1:])
                except ValueError:
                    return None
            elif line.startswith("n"):
                if not current_pid or current_pid <= 1 or line[1:] not in accepted:
                    return None
                listeners.add(current_pid)
        return sorted(listeners) if listeners else None

    def _owns_listener(self, job):
        if not self._owned(job, base_url=self.base_url):
            return False
        listeners = self._listener_pids()
        if not listeners:
            return False
        try:
            return (all(os.getpgid(pid) == job["pid"] for pid in listeners)
                    and self._owned(job, base_url=self.base_url))
        except (ProcessLookupError, PermissionError):
            return False

    def _matching_job(self, job, config):
        return (isinstance(job.get("config"), dict)
                and _fingerprint(job["config"]) == _fingerprint(config)
                and job["config"].get("local_port") == self.port
                and job.get("base_url", self.base_url) == self.base_url)

    def _require_build(self, config):
        marker = _read_json(self.state_dir / "build.json", {})
        if marker.get("config_fingerprint") != _fingerprint(config) or marker.get("commit") != WDA_COMMIT:
            raise ValueError("Ejecuta build con éxito para esta configuración antes de start; start usa test-without-building.")

    @staticmethod
    def _publishing_pid(job):
        """Only a newly queued job may briefly await Popen's PID publication."""
        if job.get("state") != "queued" or job.get("pid") is not None:
            return False
        try:
            created = dt.datetime.fromisoformat(job["created_at"].replace("Z", "+00:00"))
            elapsed = (dt.datetime.now(dt.timezone.utc) - created).total_seconds()
            return 0 <= elapsed <= PID_PUBLICATION_GRACE_SECONDS
        except (ValueError, TypeError, KeyError, AttributeError):
            return False

    def pending_recovery(self):
        """Read an existing startup recovery; never queue or stop anything."""
        config = self.config
        jobs = [_read_json(path, {}) for path in (self.state_dir / "jobs").glob("*.json")]
        for job in sorted((job for job in jobs if isinstance(job, dict)), key=lambda item: str(item.get("created_at", "")), reverse=True):
            if (job.get("action") == "recover" and job.get("state") in ACTIVE_STATES
                    and job.get("recovery_phase") != "serving" and self._matching_job(job, config)
                    and (self._publishing_pid(job) or self._owned(job, base_url=self.base_url))):
                return {"state": job["state"], "phase": job.get("recovery_phase", "starting"),
                        "job_id": job["id"], "recovery_of": job.get("recovery_of")}
        return None

    def recover(self):
        """Queue one bounded restart of a verified owned service, never external WDA.

        Called by READY after classified persistent UI failures. This method
        only examines local ownership and starts an asynchronous worker; it
        performs no phone action and does not wait for Xcode.
        """
        try:
            with self._lock():
                config = self.config
                self._validate_config(config)
                jobs = self._jobs()
                recoveries = [job for job in jobs if job.get("action") == "recover" and self._matching_job(job, config)]
                for job in reversed(recoveries):
                    if (job.get("state") in ACTIVE_STATES and job.get("recovery_phase") != "serving"
                            and (self._publishing_pid(job) or self._owned(job, base_url=self.base_url))):
                        return {"ok": True, "job_id": job["id"], "already_running": True,
                                "job": self._job_status(job), "recovery": {"state": job["state"], "job_id": job["id"], "recovery_of": job.get("recovery_of")},
                                "next_steps": ["Sondea pua_setup status con este job_id y vuelve a comprobar pua_ready. No encoles otro reinicio."]}
                for job in reversed(recoveries):
                    try:
                        last_attempt = max(dt.datetime.fromisoformat(job[key].replace("Z", "+00:00"))
                                           for key in ("created_at", "service_started_at", "completed_at") if job.get(key))
                        elapsed = (dt.datetime.now(dt.timezone.utc) - last_attempt).total_seconds()
                    except (ValueError, TypeError, KeyError, AttributeError):
                        continue
                    if 0 <= elapsed < RECOVERY_COOLDOWN_SECONDS:
                        return {"ok": False, "error": "Un intento de recuperación reciente sigue dentro de la espera entre reinicios.",
                                "job_id": job["id"], "job": self._job_status(job),
                                "recovery": {"state": "cooldown", "job_id": job["id"], "retry_after_seconds": max(1, int(RECOVERY_COOLDOWN_SECONDS - elapsed + 1))},
                                "next_steps": ["Revisa el trabajo de recuperación y su registro, desbloquea el iPhone y comprueba Developer Mode y Enable UI Automation. No reinicies WebDriverAgent en bucle."]}
                targets = [job for job in jobs if (job.get("action") == "start" or
                                                  (job.get("action") == "recover" and job.get("recovery_phase") == "serving"))
                           and job.get("state") in ACTIVE_STATES
                           and self._matching_job(job, config) and self._owns_listener(job)]
                if len(targets) != 1:
                    return {"ok": False, "error": "El listener actual de WebDriverAgent no pertenece de forma única a un trabajo start vivo y coincidente de este plugin; se rechazó la recuperación automática.",
                            "recovery": {"state": "manual"},
                            "next_steps": ["Conserva los servicios externos de WebDriverAgent. Pide a su dueño que los reinicie, o revisa pua_setup status e inicia un servicio propio de este plugin."]}
                self._source(config)
                self._require_build(config)
                if sys.platform != "darwin" or not all(shutil.which(name) for name in ("xcodebuild", "node", "npm")):
                    raise ValueError("La recuperación exige macOS, el Xcode completo y un Node.js / npm admitidos.")
                if not _node_supported(_run(["node", "--version"])["stdout"]):
                    raise ValueError("El reenvío USB exige Node.js 20.19+ / 22.12+ / 24+; actualiza Node.js antes de la recuperación.")
                target = targets[0]
                snapshot = {key: target.get(key) for key in ("id", "pid", "owner_token", "worker_entrypoint")}
                snapshot.update(config_fingerprint=_fingerprint(config), base_url=self.base_url)
                result = self._create_job("recover", config, recovery_target=snapshot)
                result["recovery"] = {"state": result.get("job", {}).get("state", "failed"),
                                      "job_id": result.get("job_id"), "recovery_of": target["id"]}
                return result
        except (ValueError, OSError, KeyError) as error:
            return {"ok": False, "error": _redact(error), "recovery": {"state": "manual"},
                    "next_steps": _diagnose(str(error)) or ["Revisa pua_setup status y corrige el requisito indicado antes de la recuperación."]}

    def _group_running(self, group, timeout=2):
        members = _run(["ps", "-ax", "-o", "pid=,pgid=,stat="], timeout=timeout)
        if not members["ok"]:
            return True
        for line in members["stdout"].splitlines():
            try:
                _, pgid, state = line.split()[:3]
                if int(pgid) == group and not state.startswith("Z"):
                    return True
            except (ValueError, IndexError):
                continue
        return False

    def _stop_recovery_target(self, job):
        """Revalidate the private target snapshot immediately before signalling."""
        snapshot = job.get("recovery_target", {})
        target = _read_json(self._job_path(snapshot.get("id")), {})
        if (not (target.get("action") == "start" or
                 (target.get("action") == "recover" and target.get("recovery_phase") == "serving"))
                or target.get("state") not in ACTIVE_STATES
                or any(target.get(key) != snapshot.get(key) for key in ("id", "pid", "owner_token", "worker_entrypoint"))
                or not self._matching_job(target, job["config"])
                or _fingerprint(self.config) != _fingerprint(job["config"])
                or snapshot.get("config_fingerprint") != _fingerprint(job["config"])
                or snapshot.get("base_url") != self.base_url or not self._owns_listener(target)):
            raise ValueError("Cambió la propiedad o el listener del objetivo de recuperación; no se señaló ningún proceso.")
        os.killpg(target["pid"], signal.SIGTERM)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            listeners = self._listener_pids(timeout=min(3, max(0.01, deadline - time.monotonic())))
            if listeners is None:
                raise ValueError("No se puede comprobar que el listener anterior haya salido; la recuperación no iniciará otro reenvío.")
            if not listeners and time.monotonic() < deadline and not self._group_running(target["pid"], timeout=min(2, max(0.01, deadline - time.monotonic()))):
                return
            if listeners:
                try:
                    if any(os.getpgid(pid) != target["pid"] for pid in listeners):
                        raise ValueError("Otro servicio es ahora dueño del puerto; la recuperación lo conservó y se detuvo.")
                except ProcessLookupError:
                    pass
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        raise ValueError("El grupo o el listener propio de WebDriverAgent no salió en 10 segundos; la recuperación se detuvo sin matar otros procesos.")

    def _job_path(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("job_id debe ser el ID que devolvió un trabajo de setup.")
        return self.state_dir / "jobs" / (job_id + ".json")

    def _job_status(self, job):
        result = dict(job)
        if job.get("state") in ACTIVE_STATES and not (self._publishing_pid(job) or self._owned(job)):
            result["state"] = "interrupted"
            result["error"] = "El worker registrado ya no existe o no se puede verificar su propiedad. Inicia un trabajo nuevo; no se señaló ningún proceso ajeno."
        log = self.state_dir / "logs" / (job["id"] + ".log")
        try:
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size - 12000))
                tail = stream.read().decode("utf-8", "replace")
        except OSError:
            tail = ""
        result.pop("owner_token", None)
        result.pop("config", None)
        result.pop("recovery_target", None)
        result["log_path"] = str(log)
        result["log_tail"] = _redact("\n".join(tail.splitlines()[-35:]))
        result["next_steps"] = _diagnose(tail + " " + result.get("error", ""))
        return result

    def _jobs(self):
        for job_id, process in list(self._workers.items()):
            if process.poll() is not None:
                del self._workers[job_id]
        return sorted((job for path in (self.state_dir / "jobs").glob("*.json")
                       if (job := _read_json(path)) and isinstance(job, dict) and job.get("id")),
                      key=lambda job: str(job.get("created_at", "")))

    def _create_job(self, action, config, *, recovery_target=None):
        for job in self._jobs():
            if job.get("state") in ACTIVE_STATES and self._owned(job):
                if action == "recover" and recovery_target and job["id"] == recovery_target["id"]:
                    continue
                if action == "start" and job["action"] == "start":
                    return {"ok": True, "already_running": True, "job": self._job_status(job)}
                raise ValueError(f"Ya hay un trabajo {job['action']} propio en ejecución. Revisa status o detén ese trabajo antes de {action}.")
        job_id = uuid.uuid4().hex
        job = {"id": job_id, "action": action, "state": "queued", "created_at": _now(),
               "owner_token": uuid.uuid4().hex, "pid": None, "config": config,
               "worker_entrypoint": str(Path(__file__).resolve()), "base_url": self.base_url}
        if recovery_target is not None:
            job.update(recovery_of=recovery_target["id"], recovery_target=recovery_target, recovery_phase="queued")
        path = self._job_path(job_id)
        _write_json(path, job)
        log_path = self.state_dir / "logs" / (job_id + ".log")
        fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "DEVELOPER_DIR", "USER", "LOGNAME"}}
        try:
            with os.fdopen(fd, "wb") as log:
                process = subprocess.Popen([sys.executable, job["worker_entrypoint"], "--worker", str(self.state_dir), job_id, job["owner_token"], "--base-url", self.base_url],
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env, start_new_session=True, close_fds=True)
            job["pid"] = process.pid
            self._workers[job_id] = process
            _write_json(path, job)
        except OSError as error:
            job.update(state="failed", error=_redact(error), completed_at=_now())
            _write_json(path, job)
        return {"ok": job["state"] != "failed", "job_id": job_id, "job": self._job_status(job), "next_step": "Sondea el estado de setup con este job_id; no bloquees MCP esperando a Xcode."}

    def _build_command(self, config, action):
        return ["xcodebuild", "-project", str(Path(config["source_dir"]) / "WebDriverAgent.xcodeproj"),
                "-scheme", "WebDriverAgentRunner", "-configuration", "Debug", "-destination", "id=" + config["udid"],
                "-derivedDataPath", str(self.state_dir / "derived_data"), "-allowProvisioningUpdates",
                "DEVELOPMENT_TEAM=" + config["team_id"], "CODE_SIGN_STYLE=Automatic", "CODE_SIGN_IDENTITY=Apple Development",
                "PRODUCT_BUNDLE_IDENTIFIER=" + config["bundle_id"], "USE_PORT=" + str(config["device_port"]), action]

    def setup(self, action, **args):
        wait_seconds = args.pop("wait_seconds", 20 if action == "start" else 0)
        if (isinstance(wait_seconds, bool) or not isinstance(wait_seconds, (int, float))
                or not 0 <= wait_seconds <= 30):
            return {"ok": False, "error": "wait_seconds debe estar entre 0 y 30."}
        if wait_seconds and action not in ("start", "status"):
            return {"ok": False, "error": "wait_seconds solo se admite en start y status."}
        result = self._setup_once(action, **args)
        if not result.get("ok") or not wait_seconds:
            return result
        job_id = result.get("job_id") or (result.get("job") or {}).get("id") or args.get("job_id")
        if not job_id:
            return result
        # Wait outside the lifecycle lock: status/stop and the worker remain usable.
        deadline = time.monotonic() + wait_seconds
        while True:
            status = self._setup_once("status", job_id=job_id)
            if not status.get("ok"):
                return status
            job = status["jobs"][0]
            service = status["service"]
            if job.get("action") not in ("start", "recover"):
                return result
            serving = job.get("action") != "recover" or job.get("recovery_phase") == "serving"
            if job.get("state") not in ACTIVE_STATES:
                reason = "job_finished"
            elif service.get("ready") and serving:
                reason = "service_ready"
            elif time.monotonic() >= deadline:
                reason = "timeout"
            else:
                time.sleep(min(0.5, max(0, deadline - time.monotonic())))
                continue
            result.update(service=service, wait_reason=reason, retry_after_seconds=1 if reason == "timeout" else 0)
            if action == "start":
                result.update(job_id=job_id, job=job)
            else:
                result.update(jobs=status["jobs"])
            result["next_step"] = ("Ejecuta pua_ready para comprobar el canal completo del iPhone." if reason == "service_ready"
                                   else "Revisa el fallo y los registros de este trabajo." if reason == "job_finished"
                                   else "Consulta status con el mismo job_id y wait_seconds=20; no inicies otra vez.")
            return result

    def _setup_once(self, action, **args):
        allowed = {"discover", "fetch", "configure", "build", "start", "stop", "status"}
        if action not in allowed:
            return {"ok": False, "error": "Acción de setup no admitida.", "actions": sorted(allowed)}
        try:
            with self._lock():
                if action == "discover":
                    return self.discover()
                if action == "status":
                    job_id = args.get("job_id")
                    if job_id:
                        job = _read_json(self._job_path(job_id))
                        if not job:
                            raise ValueError("job_id desconocido.")
                        jobs = [job]
                    else:
                        jobs = self._jobs()[-6:]
                    return {"ok": True, "configured": bool(self.config), "config": self.config,
                            "jobs": [self._job_status(job) for job in jobs], "service": self._probe_status(),
                            "runtime": str(self.state_dir)}
                if action == "stop":
                    job_id = args.get("job_id")
                    jobs = [_read_json(self._job_path(job_id))] if job_id else self._jobs()
                    if job_id and not jobs[0]:
                        raise ValueError("job_id desconocido.")
                    stopped, unowned = [], []
                    for job in jobs:
                        if job.get("state") not in ACTIVE_STATES:
                            continue
                        if self._owned(job):
                            os.killpg(job["pid"], signal.SIGTERM)
                            stopped.append(job["id"])
                        else:
                            unowned.append(job["id"])
                    return {"ok": True, "stopped_jobs": stopped, "unverified_jobs_preserved": unowned,
                            "note": "Solo se señaló a los grupos de procesos de workers propios. No se desinstaló ninguna app."}
                if action == "configure":
                    if any(job.get("state") in ACTIVE_STATES and self._owned(job) for job in self._jobs()):
                        raise ValueError("Detén el trabajo propio antes de cambiar su configuración.")
                    allowed_args = {"udid", "team_id", "bundle_id", "source_dir", "local_port", "device_port"}
                    if set(args) - allowed_args:
                        raise ValueError("Argumentos de configure desconocidos: " + ", ".join(sorted(set(args) - allowed_args)))
                    config = {"udid": args.get("udid"), "team_id": args.get("team_id"), "bundle_id": args.get("bundle_id"),
                              "source_dir": str(Path(args.get("source_dir") or self.state_dir / "runtime/WebDriverAgent").expanduser().resolve()),
                              "local_port": args.get("local_port", self.port), "device_port": args.get("device_port", 8100)}
                    self._validate_config(config)
                    if args.get("source_dir"):
                        self._source(config)
                    _write_json(self.state_dir / "config.json", config)
                    return {"ok": True, "config": config, "next_step": "Ejecuta fetch si falta la fuente y luego build. Xcode firma con Apple usando tu cuenta actual."}
                if args:
                    raise ValueError(f"{action} no admite argumentos; usa configure antes.")
                config = self.config
                if action == "fetch":
                    # Fetch is also useful before device/signing configuration.
                    return self._create_job(action, config)
                self._validate_config(config)
                self._source(config)
                if sys.platform != "darwin" or not shutil.which("xcodebuild"):
                    raise ValueError("Compilar e iniciar WebDriverAgent exige macOS con el Xcode completo.")
                if action == "start":
                    healthy = self._probe_status()
                    if healthy["ready"]:
                        return {"ok": True, "already_ready": True, "service": healthy,
                                "note": "Se reutiliza un WebDriverAgent alcanzable. Este plugin no es dueño de ese servicio externo ni lo detiene."}
                    self._require_build(config)
                    if not shutil.which("node") or not shutil.which("npm"):
                        raise ValueError("Instala un Node.js y un npm admitidos para el reenvío USB.")
                    if not _node_supported(_run(["node", "--version"])["stdout"]):
                        raise ValueError("El reenvío USB exige Node.js 20.19+ / 22.12+ / 24+; actualiza Node.js antes de start.")
                    with socket.socket() as probe:
                        # Node listeners use address reuse. A recently stopped
                        # owned forward can leave connections in TIME_WAIT;
                        # match that reuse policy without permitting an active
                        # listener to be displaced or killed.
                        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        try:
                            probe.bind(("127.0.0.1", config["local_port"]))
                        except OSError:
                            raise ValueError("El puerto local de reenvío está ocupado y WebDriverAgent no está listo. No mates procesos ajenos; configura otra URL loopback de MCP o detén un trabajo propio.")
                return self._create_job(action, config)
        except (ValueError, OSError, KeyError) as error:
            return {"ok": False, "error": _redact(error), "next_steps": _diagnose(str(error))}


def _worker(state_dir, job_id, owner_token, base_url):
    os.umask(0o077)
    manager = SetupManager(Path(state_dir), base_url)
    path = manager._job_path(job_id)
    # Parent publishes PID after Popen; avoid concurrent writes before then.
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = _read_json(path, {})
        if job.get("pid") == os.getpid():
            break
        time.sleep(0.01)
    if job.get("owner_token") != owner_token or job.get("pid") != os.getpid():
        return 1
    children = []
    log_threads = []
    log_lock = threading.Lock()
    stopping = False

    def launch(argv, cwd=None):
        """Redact command output before it reaches the private on-disk log."""
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, errors="replace", bufsize=1)
        children.append(child)

        def relay():
            with child.stdout:
                for line in child.stdout:
                    with log_lock:
                        print(_redact(line.rstrip("\r\n")), flush=True)

        thread = threading.Thread(target=relay, name="wda-job-log", daemon=True)
        log_threads.append(thread)
        thread.start()
        return child

    def stop(signum, frame):
        nonlocal stopping
        stopping = True
        for child in children:
            if child.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    job.update(state="running", started_at=_now())
    _write_json(path, job)

    def run(argv, cwd=None):
        if stopping:
            raise InterruptedError("Detenido a petición del dueño.")
        print("Running:", _redact(" ".join(argv)), flush=True)
        child = launch(argv, cwd)
        code = child.wait()
        if stopping:
            raise InterruptedError("Detenido a petición del dueño.")
        if code:
            raise RuntimeError(f"{Path(argv[0]).name} salió con el código {code}; revisa el final redactado del registro.")

    try:
        action, config = job["action"], job["config"]
        if action == "fetch":
            source = manager.state_dir / "runtime/WebDriverAgent"
            if not source.exists():
                source.mkdir(mode=0o700)
                run(["git", "init", str(source)])
                run(["git", "-C", str(source), "remote", "add", "origin", WDA_REPOSITORY])
            try:
                manager._source({"source_dir": str(source)})
            except ValueError:
                # Resume an interrupted fetch in this plugin-owned checkout.
                # Never reset tracked modifications or touch a reused source_dir.
                dirty = _run(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"])
                origin = _run(["git", "-C", str(source), "remote", "get-url", "origin"])
                if not dirty["ok"] or dirty["stdout"].strip() or not origin["ok"] or origin["stdout"].strip() != WDA_REPOSITORY:
                    raise ValueError("El checkout de runtime propio está modificado o tiene otro origen. Consérvalo y elige un directorio de estado externo nuevo antes de volver a fetch.")
                run(["git", "-C", str(source), "fetch", "--depth", "1", "origin", WDA_COMMIT])
                run(["git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD"])
                manager._source({"source_dir": str(source)})
            job["source_dir"] = str(source)
        elif action in {"build", "start", "recover"}:
            manager._validate_config(config)
            source = manager._source(config)
            if action == "build":
                # A failed rebuild must not leave an old success marker usable.
                with contextlib.suppress(FileNotFoundError):
                    (manager.state_dir / "build.json").unlink()
                run(manager._build_command(config, "build-for-testing"), cwd=source)
                _write_json(manager.state_dir / "build.json", {"config_fingerprint": _fingerprint(config), "commit": WDA_COMMIT, "built_at": _now()})
            else:
                if action == "recover":
                    # /status.ready cannot verify XCTest authorization. This
                    # path deliberately never uses start's healthy shortcut.
                    manager._require_build(config)
                    job["recovery_phase"] = "stopping"
                    _write_json(path, job)
                    manager._stop_recovery_target(job)
                    job["recovery_phase"] = "starting"
                    _write_json(path, job)
                forward = manager.state_dir / "runtime/forward"
                forward.mkdir(exist_ok=True, mode=0o700)
                for name in ("package.json", "package-lock.json", "forward.mjs"):
                    shutil.copyfile(PLUGIN_ROOT / "tooling" / name, forward / name)
                    (forward / name).chmod(0o600)
                lock_hash = hashlib.sha256((forward / "package-lock.json").read_bytes()).hexdigest()
                if _read_json(forward / "installed.json", {}).get("lock_hash") != lock_hash or not (forward / "node_modules/appium-ios-device").is_dir():
                    run(["npm", "ci", "--ignore-scripts", "--omit=optional", "--no-audit", "--no-fund"], cwd=forward)
                    _write_json(forward / "installed.json", {"lock_hash": lock_hash})
                forward_child = launch(["node", str(forward / "forward.mjs"), config["udid"], str(config["local_port"]), str(config["device_port"])])
                time.sleep(0.15)
                if forward_child.poll() is not None:
                    raise RuntimeError("El reenvío USB no arrancó; revisa el final del registro.")
                xcode = launch(manager._build_command(config, "test-without-building"), source)
                next_status_probe = 0
                # Keep both children owned and watch either side fail.
                while not stopping and all(child.poll() is None for child in (forward_child, xcode)):
                    if action == "recover" and job.get("recovery_phase") == "starting" and time.monotonic() >= next_status_probe:
                        # The old listener/group exited before these children
                        # were launched. A ready status now belongs to the new
                        # service; READY still verifies current UI authority.
                        if manager._probe_status().get("ready"):
                            job.update(recovery_phase="serving", service_started_at=_now())
                            _write_json(path, job)
                        next_status_probe = time.monotonic() + 1
                    time.sleep(0.25)
                if stopping:
                    raise InterruptedError("Detenido a petición del dueño.")
                raise RuntimeError("El runner de WebDriverAgent o el reenvío USB salieron; revisa el final del registro e inicia otra vez.")
        else:
            raise ValueError("Acción de worker no admitida.")
        job.update(state="succeeded", completed_at=_now())
    except InterruptedError as error:
        job.update(state="stopped", completed_at=_now(), error=str(error))
    except Exception as error:
        job.update(state="failed", completed_at=_now(), error=_redact(error))
        print(_redact(error), file=sys.stderr, flush=True)
    finally:
        # All commands inherit this worker's group. Broadcast TERM to include
        # grandchildren, temporarily ignoring it in the leader while cleaning up.
        if os.getpgrp() == os.getpid():
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(os.getpid(), signal.SIGTERM)
        for child in children:
            if child.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        # A command may leave an orphan child that ignores TERM. Only target
        # processes still in this live worker's unique owned group; keep the
        # leader alive to write the final job state and exit normally.
        if os.getpgrp() == os.getpid():
            members = _run(["ps", "-ax", "-o", "pid=,pgid="], timeout=3)
            for line in members["stdout"].splitlines():
                try:
                    pid, group = map(int, line.split())
                    if pid != os.getpid() and group == os.getpid() and os.getpgid(pid) == os.getpid():
                        os.kill(pid, signal.SIGKILL)
                except (ValueError, ProcessLookupError, PermissionError):
                    pass
        for thread in log_threads:
            thread.join(timeout=1)
        _write_json(path, job)
    return 0 if job["state"] == "succeeded" else 1


def main():
    parser = argparse.ArgumentParser(description="Gestiona el WebDriverAgent fijado, sin comandos de shell arbitrarios.")
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:18100")
    parser.add_argument("--worker", nargs=3, metavar=("STATE_DIR", "JOB_ID", "OWNER_TOKEN"), help=argparse.SUPPRESS)
    parser.add_argument("action", nargs="?", choices=["doctor", "discover", "fetch", "configure", "build", "start", "stop", "status"], default="status")
    parser.add_argument("--udid")
    parser.add_argument("--team-id")
    parser.add_argument("--bundle-id")
    parser.add_argument("--source-dir")
    parser.add_argument("--local-port", type=int)
    parser.add_argument("--device-port", type=int)
    parser.add_argument("--job-id")
    args = parser.parse_args()
    if args.worker:
        return _worker(*args.worker, args.base_url)
    manager = SetupManager(args.state_dir, args.base_url)
    kwargs = {key: getattr(args, key) for key in ("udid", "team_id", "bundle_id", "source_dir", "local_port", "device_port", "job_id") if getattr(args, key) is not None}
    result = manager.doctor() if args.action == "doctor" else manager.setup(args.action, **kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
