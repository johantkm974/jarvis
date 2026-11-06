"""Acciones sobre aplicaciones, webs y procesos."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import webbrowser
from urllib.parse import quote_plus

import config

APP_EXTS = (".exe", ".bat", ".cmd", ".lnk", ".msc")

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

# Nombre -> comando/programa (se resuelve con shutil.which, menú inicio o registro)
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


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip('"')).lower().strip(" .,;:¿?¡!")


def _launch(target: str) -> None:
    """Lanza un programa: shutil.which -> os.startfile."""
    path = shutil.which(target)
    if path:
        subprocess.Popen([path])
        return
    os.startfile(target)   # atajos del menú inicio, registro, asociaciones


def _find_in_start_menu(nombre: str) -> str | None:
    """Busca un acceso directo en el Menú Inicio que contenga el nombre."""
    needle = _norm(nombre)
    if not needle:
        return None
    raices = []
    for env in ("APPDATA", "ProgramData"):
        base = os.environ.get(env)
        if base:
            raices.append(os.path.join(base, "Microsoft", "Windows",
                                       "Start Menu", "Programs"))
    for raiz in raices:
        if not os.path.isdir(raiz):
            continue
        for dirpath, _dirs, files in os.walk(raiz):
            for f in files:
                if f.lower().endswith(".lnk") and needle in _norm(os.path.splitext(f)[0]):
                    return os.path.join(dirpath, f)
    return None


def open_target(raw: str) -> str:
    """Abre una URL, un programa instalado o busca en el Menú Inicio."""
    target = raw.strip().strip('"')
    low = _norm(target)
    if not low:
        return "Dime qué quieres abrir."

    # 1) Parece un ejecutable/atajo -> intentar lanzarlo directo
    if low.endswith(APP_EXTS):
        try:
            _launch(target)
            return f"Abriendo {target}..."
        except Exception:  # noqa: BLE001 - no está; seguimos buscando
            pass

    # 2) Programas de la lista
    if low in APPS:
        try:
            _launch(APPS[low])
            return f"Abriendo {target}..."
        except Exception as exc:  # noqa: BLE001
            return f"⚠️ No pude abrir {target}: {exc}"

    # 3) Palabras clave web
    for key, url in URLS.items():
        if key == low:
            webbrowser.open(url)
            return f"Abriendo {target} ({url})"

    # 4) Parece una URL
    if low.startswith(("http://", "https://", "www.")) or ("." in low and " " not in low):
        url = target if target.startswith(("http://", "https://")) else f"https://{target}"
        webbrowser.open(url)
        return f"Abriendo {url}"

    # 5) En el Menú Inicio (cualquier app instalada)
    lnk = _find_in_start_menu(low)
    if lnk:
        try:
            os.startfile(lnk)
            return f"Abriendo {os.path.splitext(os.path.basename(lnk))[0]}..."
        except Exception:  # noqa: BLE001
            pass

    # 6) Nada encontrado -> búsqueda en Google
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(target)}")
    return (f"❌ No encontré «{target}» instalado. "
            f"Te abrí una búsqueda en Google por si acaso.")


def close_target(raw: str) -> str:
    """Cierra aplicaciones por nombre de proceso (con protecciones)."""
    low = _norm(raw)
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
