"""Acciones sobre aplicaciones, webs y procesos.

Orden al abrir un objetivo:
  1. ejecutable/atajo escrito a mano (firefots.exe)
  2. programa de la lista APPS (si falla, no abrimos su web en su lugar)
  3. palabra clave web exacta (URLS) o URL a pelo
  4. palabra clave contenida ("abre la calculadora de ciencia")
  5. acceso directo en Menú Inicio o Escritorio (cualquier app instalada)
  6. biblioteca de Steam (cualquier juego, por nombre)
  7. búsqueda en Google
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import unicodedata
import webbrowser
from urllib.parse import quote_plus

import config

APP_EXTS = (".exe", ".bat", ".cmd", ".lnk", ".msc")

# Transcripciones típicas del micrófono -> nombre bueno
_ALIAS: dict[str, str] = {
    "bravo": "brave",
    "breve": "brave",
    "brabre": "brave",
    "geminis": "gemini",
    "gemine": "gemini",
    "firefots": "firefox",
    "firefoz": "firefox",
    "firefos": "firefox",
    "mozila": "firefox",
    "chagepete": "chatgpt",
    "chatete": "chatgpt",
}

# Palabras clave -> URL
URLS: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "chat gpt": "https://chatgpt.com",
    "openai": "https://platform.openai.com",
    "gemini": "https://gemini.google.com",
    "google gemini": "https://gemini.google.com",
    "claude": "https://claude.ai",
    "grok": "https://grok.com",
    "copilot": "https://copilot.microsoft.com",
    "deepseek": "https://chat.deepseek.com",
    "perplexity": "https://www.perplexity.ai",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "correo": "https://mail.google.com",
    "spotify": "https://open.spotify.com",
    "steam": "https://store.steampowered.com",
    "netflix": "https://www.netflix.com",
    "whatsapp": "https://web.whatsapp.com",
    "wikipedia": "https://es.wikipedia.org",
    "stackoverflow": "https://stackoverflow.com",
    "office": "https://www.office.com",
    "word online": "https://www.office.com/word",
    "drive": "https://drive.google.com",
    "maps": "https://maps.google.com",
    "traductor": "https://translate.google.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com",
    "twitch": "https://www.twitch.tv",
}

# Nombre -> comando/programa (se resuelve con shutil.which o menú inicio)
APPS: dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "brave": "brave.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "navegador": "msedge.exe",
    "code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "word": "winword.exe",
    "microsoft word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "explorador": "explorer.exe",
    "explorer": "explorer.exe",
    "calculadora": "calc.exe",
    "calc": "calc.exe",
    "bloc de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "spotify": "spotify.exe",
    "steam": "steam.exe",
    "discord": "discord.exe",
    "teams": "teams.exe",
    "outlook": "outlook.exe",
    "terminal": "wt.exe",
    "wt": "wt.exe",
    "mysql workbench": "MySQLWorkbench.exe",
}

# "cierra X" -> nombres de proceso que hay que terminar
CIERRES: dict[str, list[str]] = {
    "navegadores": ["chrome", "msedge", "firefox", "brave", "opera"],
    "todo el navegador": ["chrome", "msedge", "firefox", "brave", "opera"],
    "chrome": ["chrome"],
    "google chrome": ["chrome"],
    "brave": ["brave"],
    "bravo": ["brave"],
    "breve": ["brave"],
    "firefox": ["firefox"],
    "edge": ["msedge"],
    "word": ["winword"],
    "microsoft word": ["winword"],
    "excel": ["excel"],
    "powerpoint": ["powerpnt"],
    "visual studio code": ["code"],
    "vscode": ["code"],
    "code": ["code"],
    "spotify": ["spotify"],
    "steam": ["steam"],
    "discord": ["discord"],
    "teams": ["teams"],
    "outlook": ["outlook"],
    "bloc de notas": ["notepad"],
    "notepad": ["notepad"],
    "paint": ["mspaint"],
}

# Nunca se tocan: nuestro propio proceso, OpenCode, el shell ni servicios
_PROTEGIDOS = ("python", "opencode", "explorer", "svchost", "services")

_STOPWORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "y", "en",
              "app", "aplicacion", "aplicación", "juego", "el"}


def _norm(text: str) -> str:
    """minúsculas, sin acentos, sin comillas/puntuación sobrante."""
    text = re.sub(r"\s+", " ", text.strip().strip('"')).lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text.strip(" .,;:¿?¡!")


def _canon(low: str) -> str:
    """Quita extensión y aplica alias: 'firefots.exe' -> 'firefox'."""
    stem = low.rsplit(".", 1)[0] if low.endswith(APP_EXTS) else low
    return _ALIAS.get(stem, low)


def _launch(target: str) -> None:
    """Lanza un programa: PATH -> App Paths del registro -> ShellExecute."""
    path = shutil.which(target)
    if path:
        subprocess.Popen([path])
        return
    # App Paths: donde Windows guarda la ruta de chrome.exe, brave.exe, etc.
    if target.lower().endswith(".exe"):
        try:
            import winreg

            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for sub in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
                            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"):
                    try:
                        with winreg.OpenKey(root, sub + "\\" + target) as key:
                            valor, _tipo = winreg.QueryValueEx(key, None)
                            if valor:
                                os.startfile(valor)
                                return
                    except OSError:
                        continue
        except ImportError:
            pass
    os.startfile(target)   # atajos del menú inicio, registro, asociaciones


def _shortcut_roots() -> list[str]:
    raices: list[str] = []
    for env in ("APPDATA", "ProgramData"):
        base = os.environ.get(env)
        if base:
            raices.append(os.path.join(base, "Microsoft", "Windows",
                                       "Start Menu", "Programs"))
    posibles = []
    home = os.path.expanduser("~")
    posibles.append(os.path.join(home, "Desktop"))
    posibles.append(os.path.join(home, "OneDrive", "Desktop"))
    public = os.environ.get("PUBLIC")
    if public:
        posibles.append(os.path.join(public, "Desktop"))
    for d in posibles:
        if os.path.isdir(d):
            raices.append(d)
    return raices


def _find_shortcut(nombre: str) -> str | None:
    """Busca un .lnk/.url en Menú Inicio o Escritorio.

    Prioridad: contiene el nombre completo > contiene TODAS las palabras >
    el nombre está contenido en lo pedido.
    """
    consulta = _norm(nombre)
    if not consulta:
        return None
    palabras = [w for w in re.split(r"\W+", consulta) if w and w not in _STOPWORDS]
    mejor: str | None = None
    mejor_punto = 0
    for raiz in _shortcut_roots():
        for dirpath, _dirs, files in os.walk(raiz):
            for f in files:
                if not f.lower().endswith((".lnk", ".url")):
                    continue
                nombre_atajo = _norm(os.path.splitext(f)[0])
                if not nombre_atajo:
                    continue
                punto = 0
                if consulta in nombre_atajo:
                    punto = 3
                elif palabras and all(p in nombre_atajo for p in palabras):
                    punto = 2
                elif nombre_atajo in consulta and len(nombre_atajo) >= 4:
                    punto = 1
                if punto > mejor_punto:
                    mejor_punto = punto
                    mejor = os.path.join(dirpath, f)
    return mejor


# --- Biblioteca de Steam ------------------------------------------------------
def _steam_dir() -> str | None:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            valor, _tipo = winreg.QueryValueEx(key, "SteamPath")
            if valor and os.path.isdir(valor):
                return valor.replace("/", os.sep)
    except Exception:  # noqa: BLE001 - sin Steam en el registro
        pass
    for cand in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam",
                 r"D:\Steam", r"C:\Steam"):
        if os.path.isdir(cand):
            return cand
    return None


def _steam_libraries() -> list[str]:
    base = _steam_dir()
    if not base:
        return []
    libs = [base]
    vdf = os.path.join(base, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, encoding="utf-8", errors="ignore") as fh:
            texto = fh.read()
        for m in re.finditer(r'"path"\s*"([^"]+)"', texto):
            ruta = m.group(1).replace("\\\\", "\\").replace("/", os.sep)
            if ruta not in libs:
                libs.append(ruta)
    except OSError:
        pass
    return libs


def _steam_appid(nombre: str) -> str | None:
    """appID de un juego por su nombre (appmanifest_*.acf de la biblioteca)."""
    consulta = _norm(nombre)
    if not consulta:
        return None
    qwords = {w for w in re.split(r"\W+", consulta) if len(w) > 1}
    for lib in _steam_libraries():
        folder = os.path.join(lib, "steamapps")
        if not os.path.isdir(folder):
            continue
        try:
            acfs = os.listdir(folder)
        except OSError:
            continue
        for f in acfs:
            if not (f.startswith("appmanifest_") and f.endswith(".acf")):
                continue
            try:
                with open(os.path.join(folder, f), encoding="utf-8",
                          errors="ignore") as fh:
                    txt = fh.read(4000)   # appid y name están al principio
            except OSError:
                continue
            m_name = re.search(r'"name"\s*"([^"]+)"', txt)
            m_app = re.search(r'"appid"\s*"(\d+)"', txt)
            if not (m_name and m_app):
                continue
            nombre_app = _norm(m_name.group(1))
            if nombre_app == consulta:
                return m_app.group(1)
            if qwords and qwords <= {w for w in re.split(r"\W+", nombre_app)
                                     if len(w) > 1}:
                return m_app.group(1)
    return None


def _clave_contenida(low: str) -> str | None:
    """'la calculadora de ciencia' -> 'calculadora' (palabra clave completa)."""
    claves = sorted(set(list(APPS) + list(URLS)), key=len, reverse=True)
    for k in claves:
        if len(k) >= 4 and re.search(rf"\b{re.escape(k)}\b", low):
            return k
    return None


def open_target(raw: str) -> str:
    """Abre una URL, un programa instalado, un juego de Steam o busca."""
    target = re.split(r"[.!?]\s+", raw.strip().strip('"'))[0].strip()
    target = target or raw.strip()
    low = _norm(target)
    if not low:
        return "Dime qué quieres abrir."
    canon = _canon(low)
    web_ok = True

    # 1) ejecutable/atajo escrito a mano ("abre firefots.exe")
    if low.endswith(APP_EXTS):
        try:
            _launch(target)
            return f"Abriendo {target}..."
        except Exception:  # noqa: BLE001
            if canon != low:
                try:
                    _launch(APPS.get(canon, canon))
                    return f"Abriendo {target}..."
                except Exception:  # noqa: BLE001
                    pass
            web_ok = False   # no convertir "firefots.exe" en https://firefots.exe

    # 2) programas de la lista (si fallan, seguimos buscando el atajo)
    if canon in APPS:
        try:
            _launch(APPS[canon])
            return f"Abriendo {target}..."
        except Exception:  # noqa: BLE001
            web_ok = False

    if web_ok:
        # 3) palabras clave web exactas
        for key, url in URLS.items():
            if key == canon or key == low:
                webbrowser.open(url)
                return f"Abriendo {target} ({url})"

        # 4) parece una URL
        if low.startswith(("http://", "https://", "www.")) or (
                "." in low and " " not in low):
            url = target if target.startswith(("http://", "https://")) \
                else f"https://{target}"
            webbrowser.open(url)
            return f"Abriendo {url}"

        # 5) palabra clave contenida: "abre la calculadora de ciencia"
        clave = _clave_contenida(canon)
        if clave:
            if clave in APPS:
                try:
                    _launch(APPS[clave])
                    return f"Abriendo {target}..."
                except Exception:  # noqa: BLE001
                    pass
            url = URLS[clave]
            webbrowser.open(url)
            return f"Abriendo {target} ({url})"

    # 6) cualquier app instalada: Menú Inicio o Escritorio
    lnk = _find_shortcut(canon) or _find_shortcut(low)
    if lnk:
        try:
            os.startfile(lnk)
            base = os.path.splitext(os.path.basename(lnk))[0]
            return f"Abriendo {base}..."
        except Exception:  # noqa: BLE001
            pass

    # 7) juegos de Steam por nombre
    appid = _steam_appid(canon)
    if appid:
        try:
            os.startfile(f"steam://rungameid/{appid}")
            return f"🚀 Lanzando por Steam: {target}"
        except Exception as exc:  # noqa: BLE001
            return f"⚠️ Steam no pudo lanzar «{target}»: {exc}"

    # 8) nada encontrado -> búsqueda en Google
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(target)}")
    return (f"❌ No encontré «{target}» instalado. "
            f"Te abrí una búsqueda en Google por si acaso.")


def close_target(raw: str) -> str:
    """Cierra aplicaciones por nombre de proceso (con protecciones)."""
    low = _canon(_norm(raw))
    if not low:
        return "Dime qué quieres cerrar."
    if low in ("todo", "todos", "todo el sistema", "el sistema", "la computadora",
               "el pc", "todo el pc", "toda la pc", "todo lo demas"):
        return ("❌ No cierro todo: dime una app concreta, por ejemplo "
                "«cierra chrome», «cierra word» o «cierra todos los navegadores».")

    keywords: list[str] | None = None
    for key, procs in CIERRES.items():
        if key == low or key in low:
            keywords = procs
            break
    if keywords is None:
        keywords = [re.sub(r"[^a-z0-9]", "", low)]

    import psutil

    cerrados: list[str] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            pid = proc.info.get("pid") or 0
            if pid == os.getpid() or any(p in name for p in _PROTEGIDOS):
                continue
            if any(k in name for k in keywords):
                proc.terminate()
                cerrados.append(proc.info.get("name") or name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if cerrados:
        return f"🛑 Cerré: {', '.join(sorted(set(cerrados)))}"
    return f"❌ No encontré «{raw}» abierto. (¿Está en ejecución?)"


def open_opencode() -> str:
    """Inicia OpenCode en una terminal nueva, en el directorio actual."""
    cwd = config.BASE_DIR
    term = (config.TERMINAL or "auto").lower()

    def _wt() -> bool:
        if term not in ("auto", "wt"):
            return False
        wt = shutil.which("wt.exe")
        if not wt:
            return False
        subprocess.Popen([wt, "-d", str(cwd), "cmd", "/k", "opencode"], cwd=str(cwd))
        return True

    def _powershell() -> bool:
        if term not in ("auto", "powershell"):
            return False
        ps = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not ps:
            return False
        subprocess.Popen([ps, "-NoExit", "-Command", "opencode"], cwd=str(cwd))
        return True

    def _cmd() -> bool:
        if term not in ("auto", "cmd"):
            return False
        cmd = shutil.which("cmd.exe")
        if not cmd:
            return False
        subprocess.Popen([cmd, "/k", "opencode"], cwd=str(cwd))
        return True

    for opener in (_wt, _powershell, _cmd):
        try:
            if opener():
                return f"🚀 OpenCode iniciado en {cwd}"
        except Exception:  # noqa: BLE001
            continue
    return "⚠️ No encontré una terminal compatible (wt/powershell/cmd)."
