"""Acciones sobre archivos y carpetas.

Todo se resuelve dentro de config.WORKSPACE salvo que des una ruta absoluta
o especifiques un destino: "escritorio", "desktop", "workspace",
"documentos", "descargas".
"""
from __future__ import annotations

import re
from pathlib import Path

import config

DEFAULT_NOTE = "dictado.txt"
MAX_READ = 4000  # caracteres máximos al leer

# "en el escritorio" / "en desktop" / "en mi escritorio" / "en workspace"...
_DEST_RE = re.compile(
    r"\s+(?:en|a|al|para|dentro de|en el directorio de|en la carpeta de|de)\s+"
    r"(?:el\s+|la\s+|mi\s+|los\s+|las\s+)?"
    r"(escritorio|desktop|workspace|carpeta de trabajo|documentos|mis documentos|"
    r"documents|descargas|downloads)\s*$",
    re.IGNORECASE,
)


def _desktop_dir() -> Path:
    """Escritorio real (respeta el redireccionamiento de OneDrive)."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            valor, _tipo = winreg.QueryValueEx(key, "Desktop")
            import os as _os

            ruta = Path(_os.path.expandvars(valor)).expanduser()
            if ruta.is_dir():
                return ruta
    except Exception:  # noqa: BLE001 - sin registro: ruta clásica
        pass
    return Path.home() / "Desktop"


def _destino_base(clave: str) -> Path:
    key = clave.lower()
    if key in ("escritorio", "desktop"):
        return _desktop_dir()
    if key in ("documentos", "mis documentos", "documents"):
        return Path.home() / "Documents"
    if key in ("descargas", "downloads"):
        return Path.home() / "Downloads"
    return config.WORKSPACE   # workspace / carpeta de trabajo


def split_destino(raw: str) -> tuple[str, Path | None]:
    """Separla «nombre en escritorio» -> ('nombre', C:\\...\\Desktop)."""
    texto = (raw or "").strip()
    m = _DEST_RE.search(texto)
    if not m:
        return texto, None
    nombre = texto[: m.start()].strip()
    return (nombre or texto), _destino_base(m.group(1))


def _resolve(name: str) -> Path:
    nombre, base = split_destino(name)
    raw = nombre.strip().strip('"').strip(" .")
    if not raw:
        raw = DEFAULT_NOTE
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (base or config.WORKSPACE) / p
    if not p.suffix:                      # sin extensión -> .txt
        p = p.with_suffix(".txt")
    return p


def create_folder(slots: dict) -> str:
    nombre, base = split_destino(slots.get("name", ""))
    p = Path(nombre.strip().strip('"').strip(" .")).expanduser()
    if not p.is_absolute():
        p = (base or config.WORKSPACE) / p
    if p.suffix == ".txt" and "." not in p.name[:-4]:
        p = p.with_suffix("")             # una carpeta no lleva .txt
    p.mkdir(parents=True, exist_ok=True)
    donde = "Escritorio" if str(p).startswith(str(_desktop_dir())) else str(p)
    return f"📁 Carpeta creada en {donde}: {p.name}"


def create_file(slots: dict) -> str:
    p = _resolve(slots.get("name", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        return f"ℹ️ El archivo ya existía: {p}"
    p.write_text("", encoding="utf-8")
    donde = "Escritorio" if str(p).startswith(str(_desktop_dir())) else str(p)
    return f"📄 Archivo creado en {donde}"


def write_text(slots: dict) -> str:
    text = slots.get("text", "").strip()
    if not text:
        return "No me diste texto para escribir."
    p = _resolve(slots.get("file") or DEFAULT_NOTE)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return f"✍️ Añadido a {p.name}: «{text}»"


def read_file(slots: dict) -> str:
    nombre, base = split_destino(slots.get("name", ""))
    raw = nombre.strip().strip('"').strip(" .")
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (base or config.WORKSPACE) / p
    if not p.suffix and p.exists() is False:
        p = p.with_suffix(".txt")
    if not p.is_file():
        return f"❌ No existe {p}"
    content = p.read_text(encoding="utf-8", errors="replace")
    if len(content) > MAX_READ:
        content = content[:MAX_READ] + "\n… (cortado)"
    return f"📖 {p.name}:\n{content}" if content.strip() else f"📖 {p.name} está vacío."


def list_files(slots: dict) -> str:
    raw, base = split_destino(slots.get("path") or "")
    raw = raw.strip()
    if not raw:
        p = config.WORKSPACE
    else:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (base or config.WORKSPACE) / p
    if not p.exists():
        return f"❌ No existe {p}"
    if p.is_file():
        return read_file({"name": str(p)})

    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    if not entries:
        return f"📁 {p} está vacía."
    lines = [f"📁 {p} ({len(entries)} elementos):"]
    for e in entries[:40]:
        lines.append(f"  {'/' if e.is_dir() else ' '}{e.name}")
    if len(entries) > 40:
        lines.append(f"  … y {len(entries) - 40} más")
    return "\n".join(lines)
