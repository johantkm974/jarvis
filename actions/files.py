"""Acciones sobre archivos y carpetas.

Todo se resuelve dentro de config.WORKSPACE salvo que des una ruta absoluta.
"""
from __future__ import annotations

from pathlib import Path

import config

DEFAULT_NOTE = "dictado.txt"
MAX_READ = 4000  # caracteres máximos al leer


def _resolve(name: str) -> Path:
    raw = (name or "").strip().strip('"').strip(" .")
    if not raw:
        raw = DEFAULT_NOTE
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = config.WORKSPACE / p
    if not p.suffix and p.suffix != ".":   # sin extensión -> .txt
        p = p.with_suffix(".txt")
    return p


def create_folder(slots: dict) -> str:
    p = _resolve(slots.get("name", ""))
    # una carpeta no lleva .txt
    if p.suffix == ".txt" and "." not in Path(slots.get("name", "")).name:
        p = p.with_suffix("")
    p.mkdir(parents=True, exist_ok=True)
    return f"📁 Carpeta creada: {p}"


def create_file(slots: dict) -> str:
    p = _resolve(slots.get("name", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        return f"ℹ️ El archivo ya existía: {p}"
    p.write_text("", encoding="utf-8")
    return f"📄 Archivo creado: {p}"


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
    p = _resolve(slots.get("name", ""))
    if not p.is_file():
        return f"❌ No existe {p}"
    content = p.read_text(encoding="utf-8", errors="replace")
    if len(content) > MAX_READ:
        content = content[:MAX_READ] + "\n… (cortado)"
    return f"📖 {p.name}:\n{content}" if content.strip() else f"📖 {p.name} está vacío."


def list_files(slots: dict) -> str:
    raw = (slots.get("path") or "").strip()
    p = Path(raw).expanduser() if raw else config.WORKSPACE
    if not p.is_absolute():
        p = config.WORKSPACE / p if raw else config.WORKSPACE
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
