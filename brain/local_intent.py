"""Detección de intención LOCAL: reglas puras, sin API ni modelos.

Ventajas: 0 RAM extra, 0 costo, respuesta instantánea.
Cubre el 80% del uso diario: abrir apps, MySQL, puertos, archivos...

Convención de patrones:
  * Se escriben SIN acentos (la entrada se "desacentúa" antes de comparar).
  * Se extraen los grupos sobre el texto ORIGINAL para conservar
    mayúsculas y acentos ("escribe José en notas.txt" -> "José").
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Intent:
    name: str
    slots: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0


def _deaccent(text: str) -> tuple[str, list[int]]:
    """Quita acentos conservando el mapeo índice original por carácter."""
    out: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        for d in unicodedata.normalize("NFD", ch):
            if unicodedata.category(d) != "Mn":
                out.append(d)
                idx.append(i)
    return "".join(out), idx


# Orden importa: de más específico a más genérico.
_RULES: list[tuple[str, str]] = [
    ("exit", r"\b(salir|apagate|apagarse|adios|chao|terminar|cerrar jarvis)\b"),
    ("help", r"\b(ayuda|que puedes hacer|que sabes hacer|comandos|lista de comandos|help)\b"),
    ("mysql_start", r"\b(levanta|inicia|arranca|prende|inicializa|start|corre|ejecuta)\b[^.?!]{0,30}\b(mysql|xampp|base de datos)\b"
                    r"|\b(mysql|xampp|base de datos)\b[^.?!]{0,15}\b(levanta|inicia|arranca|prende|inicializa)\b"),
    ("mysql_stop", r"\b(detener|deten|parar|para|stop|cierra|apaga)\b[^.?!]{0,30}\b(mysql|xampp|base de datos)\b"),
    ("mysql_status", r"\b(estado|status|corriendo|arriba|responde|activo)\b[^.?!]{0,30}\b(mysql|xampp|base de datos)\b"
                     r"|\b(mysql|xampp|base de datos)\b[^.?!]{0,20}\b(estado|corriendo|arriba|responde)\b"),
    ("opencode", r"\b(open ?code|opencode)\b"),
    ("port_info", r"\b(?:puerto|puertos|proceso|quien usa|que usa)\b[^0-9]{0,20}(?P<port>\d{2,5})\b"),
    ("ports", r"\b(puertos|que puertos|puertos abiertos|netstat|lista[^.?!]{0,15}puertos)\b"),
    ("processes", r"\b(procesos|que procesos|tasklist|lista[^.?!]{0,15}procesos)\b"),
    ("sysinfo", r"\b(como estas|como va el sistema|estado del sistema|cuanta ram|memoria ram|"
                r"uso de cpu|uso de memoria|uso de la cpu|cpu)\b"),
    ("time", r"\b(que hora|hora es|dime la hora|la hora)\b"),
    ("date", r"\b(que dia|fecha de hoy|dime la fecha|fecha)\b"),
    ("create_folder", r"^(?:crea|crear|creame|hazme|haz)\s+(?:una\s+|el\s+)?(?:carpeta|directorio)\s+(?P<name>.+)$"),
    ("create_file", r"^(?:crea|crear|creame|hazme|haz)\s+(?:un\s+|el\s+)?(?:archivo|fichero|documento)\s+(?P<name>.+)$"),
    ("write", r"^(?:escribeme|escribir|escribe|dicta)\s*[:\-]?\s*(?P<text>.+?)\s+"
              r"(?:en|al|en el|al archivo|dentro de)\s+(?:el\s+|un\s+)?"
              r"(?:archivo|fichero|documento|nota)\s+(?:llamado\s+)?(?P<file>.+)$"),
    ("write", r"^(?:escribeme|escribir|escribe|dicta)\s*[:\-]?\s*(?P<text>.+?)\s+"
              r"(?:en|al)\s+(?P<file>[\w./\\-]+\.[A-Za-z0-9]{1,5})$"),
    ("write_default", r"^(?:escribe|escribeme|dicta)\s*[:\-]\s*(?P<text>.+)$"),
    ("read", r"^(?:lee|leer)\s+(?:el\s+|un\s+)?(?:archivo|fichero|documento)?\s*(?P<name>.+)$"),
    ("read", r"^(?:abre|abrir)\s+(?:el\s+|un\s+)?(?:archivo|fichero|documento)\s+(?P<name>.+)$"),
    ("list_files", r"^(?:lista|listar|muestra)\s+(?:el\s+|la\s+|los\s+|las\s+)?(?:contenido\s+)?"
                   r"(?:de\s+la\s+)?(?:carpeta|directorio|archivos?)?\s*(?P<path>.*)$"),
    ("list_files", r"^que hay\s*(?:en|de|adentro de)?\s*(?P<path>.*)$"),
    ("open", r"^(?:abre|abrir|ejecuta|ejecutar|inicia|iniciar|lanza|lanzar|corre|pon)\s+"
             r"(?:el\s+|la\s+|los\s+|las\s+|un\s+|una\s+)?(?P<target>.+)$"),
    ("greet", r"^(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|oye)\b"),
]

_COMPILED: dict[str, re.Pattern[str]] = {}


def _pattern(src: str) -> re.Pattern[str]:
    pat = _COMPILED.get(src)
    if pat is None:
        pat = re.compile(src, re.IGNORECASE)
        _COMPILED[src] = pat
    return pat


def _groups(m: re.Match[str], original: str, idx: list[int]) -> dict[str, str]:
    """Devuelve los grupos del match mapeados al texto ORIGINAL (con acentos)."""
    slots: dict[str, str] = {}
    for gname, gval in m.groupdict().items():
        if gval is None:
            continue
        start, end = m.span(gname)
        if start == end:
            slots[gname] = ""
            continue
        o_start = idx[start]
        o_end = idx[end - 1] + 1
        slots[gname] = original[o_start:o_end].strip()
    return slots


def parse(text: str) -> Intent | None:
    """Devuelve la intención detectada o None (=> irá al cerebro API)."""
    original = text.strip()
    if not original:
        return None
    deacc, idx = _deaccent(original)
    for name, src in _RULES:
        m = _pattern(src).search(deacc)
        if m:
            return Intent(name=name, slots=_groups(m, original, idx))
    return None


def help_text() -> str:
    return """Comandos que entiendo SIN api (instantáneos):
  • abre youtube / chatgpt / github / chrome / spotify / calculadora...
  • abre opencode            -> OpenCode en una terminal
  • levanta mysql | para mysql | estado de mysql
  • que puertos | que proceso usa el puerto 3300
  • que procesos | como estas
  • crea carpeta proyectos | crea archivo notas.txt
  • escribe Hola mundo en archivo notas.txt | escribe: mi dictado
  • lee archivo notas.txt | lista archivos | que hay en descargas
  • que hora | que dia | ayuda | salir
Lo demás va al cerebro API (si configuraste OPENAI_API_KEY)."""
