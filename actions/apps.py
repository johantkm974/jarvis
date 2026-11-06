"""Acciones sobre aplicaciones y navegación."""
from __future__ import annotations

import re
import shutil
import subprocess
import webbrowser

import config

# Palabras clave -> URL
URLS: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "chat gpt": "https://chatgpt.com",
    "openai": "https://platform.openai.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "spotify": "https://open.spotify.com",
    "wikipedia": "https://es.wikipedia.org",
    "stackoverflow": "https://stackoverflow.com",
}

# Nombre -> comando/programa (se resuelve con shutil.which o rutas conocidas)
APPS: dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "navegador": "msedge.exe",
    "code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "explorador": "explorer.exe",
    "explorer": "explorer.exe",
    "calculadora": "calc.exe",
    "calc": "calc.exe",
    "bloc de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "spotify": "spotify.exe",
    "terminal": "wt.exe",
    "wt": "wt.exe",
    "mysql workbench": "MySQLWorkbench.exe",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip('"')).lower().strip(" .,;:¿?¡!")


def _launch(target: str) -> None:
    """Lanza un programa: shutil.which -> os.startfile -> Popen."""
    path = shutil.which(target)
    if path:
        subprocess.Popen([path])
        return
    import os

    os.startfile(target)  # usa las asociaciones/registro de Windows


def open_target(raw: str) -> str:
    """Abre una URL o un programa según lo que se le pida."""
    target = raw.strip()
    low = _norm(target)
    if not low:
        return "Dime qué quieres abrir."

    # 1) Programas instalados
    if low in APPS:
        try:
            _launch(APPS[low])
            return f"Abriendo {target}..."
        except Exception as exc:  # noqa: BLE001
            return f"⚠️ No pude abrir {target}: {exc}"

    # 2) Palabras clave web
    for key, url in URLS.items():
        if key == low:
            webbrowser.open(url)
            return f"Abriendo {target} ({url})"

    # 3) Parece una URL
    if low.startswith(("http://", "https://", "www.")) or ("." in low and " " not in low):
        url = target if target.startswith(("http://", "https://")) else f"https://{target}"
        webbrowser.open(url)
        return f"Abriendo {url}"

    # 4) Último recurso: que lo intente el sistema
    try:
        _launch(target)
        return f"Abriendo {target}..."
    except Exception:  # noqa: BLE001
        conocidos = ", ".join(sorted(APPS) + sorted(URLS))
        return f"❌ No sé abrir «{target}». Prueba con: {conocidos}"


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
