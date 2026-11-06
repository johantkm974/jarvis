"""Registro de acciones: mapea nombre de intención -> función que la ejecuta."""
from __future__ import annotations

from . import apps, files, system


def _help(slots: dict) -> str:
    from brain.local_intent import help_text

    return help_text()


def _exit(slots: dict) -> str:
    return "__EXIT__"


HANDLERS = {
    "help": _help,
    "exit": _exit,
    "greet": lambda s: "Hola. Estoy listo, dime qué necesitas.",
    "open": lambda s: apps.open_target(s.get("target", "")),
    "close": lambda s: apps.close_target(s.get("target", "")),
    "opencode": lambda s: apps.open_opencode(),
    "mysql_start": lambda s: system.mysql_start(),
    "mysql_stop": lambda s: system.mysql_stop(),
    "mysql_status": lambda s: system.mysql_status(),
    "ports": lambda s: system.list_ports(),
    "port_info": lambda s: system.port_info(s),
    "processes": lambda s: system.list_processes(),
    "sysinfo": lambda s: system.sysinfo(),
    "time": lambda s: system.now_time(),
    "date": lambda s: system.now_date(),
    "create_folder": lambda s: files.create_folder(s),
    "create_file": lambda s: files.create_file(s),
    "write": lambda s: files.write_text(s),
    "write_default": lambda s: files.write_text(s),
    "read": lambda s: files.read_file(s),
    "list_files": lambda s: files.list_files(s),
}


def run(intent) -> str:
    handler = HANDLERS.get(intent.name)
    if handler is None:
        return f"⚠️ No tengo acción para «{intent.name}»."
    try:
        return handler(intent.slots)
    except Exception as exc:  # noqa: BLE001 - el error se muestra al usuario
        return f"⚠️ Error ejecutando {intent.name} ({type(exc).__name__}): {exc}"
