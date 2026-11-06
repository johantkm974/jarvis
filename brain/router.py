"""Enrutador: decide si el comando se resuelve en local o con la API."""
from __future__ import annotations

import re

import actions
from brain import api_client, local_intent

ACCION_RE = re.compile(r"\[\[ACCION:(.+?)\]\]", re.S)


def _try_action(reply: str) -> str | None:
    """Convierte la respuesta de la API en una acción real del PC (si aplica)."""
    m = ACCION_RE.search(reply)
    if m:
        inner = m.group(1).strip()
        intent = local_intent.parse(inner) or local_intent.Intent(
            name="open", slots={"target": inner}
        )
        return actions.run(intent)

    # Fallback: si la API respondió un comando corto y directo, también lo ejecutamos
    inner = reply.strip().strip("*`# ")
    if 0 < len(inner) <= 70 and not inner.endswith("?"):
        intent = local_intent.parse(inner)
        if intent is not None:
            return actions.run(intent)
    return None


def route(text: str) -> tuple[str, str]:
    """Devuelve (respuesta, fuente). fuente = nombre del intent | 'api' | 'accion'."""
    text = (text or "").strip()
    if not text:
        return "No te escuché (entrada vacía).", "vacio"

    intent = local_intent.parse(text)
    if intent is not None:
        return actions.run(intent), intent.name

    if not api_client.available():
        return api_client.ask(text), "reglas"

    reply = api_client.ask(text)
    accion = _try_action(reply)
    if accion is not None:
        return accion, "accion"
    return reply, "api"
