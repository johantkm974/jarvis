"""Cerebro por API (OpenAI o cualquier servidor compatible: Groq, LM Studio...).

Solo se usa cuando las reglas locales NO reconocieron el comando.
Se carga el cliente bajo demanda y nunca se mezcla con modelos locales,
así la RAM queda libre cuando toca API y viceversa.
"""
from __future__ import annotations

import config

SYSTEM_PROMPT = (
    "Eres Jarvis, un asistente personal que corre en el PC de un desarrollador. "
    "Responde en español, de forma breve y directa (máximo 5 líneas), sin relleno. "
    "Si te piden código, entrégalo completo y listo para copiar.\n"
    "PROTOCOLO DE ACCIONES: cuando el usuario pida algo que SÍ se puede ejecutar en el PC "
    "(abrir una app o página web, levantar o parar MySQL, ver puertos o procesos, "
    "crear/leer/escribir archivos y carpetas, abrir OpenCode, hora o fecha), responde "
    "EXCLUSIVAMENTE con [[ACCION:comando]] y nada más. Ejemplos válidos: "
    "[[ACCION:abre youtube]] · [[ACCION:abre chrome]] · [[ACCION:crea archivo notas]] · "
    "[[ACCION:crea carpeta proyectos]] · [[ACCION:levanta mysql]] · [[ACCION:para mysql]] · "
    "[[ACCION:que puertos]] · [[ACCION:escribe hola en archivo notas]] · [[ACCION:lee archivo notas]] · "
    "[[ACCION:que hora]]. Usa esos mismos verbos en español. "
    "Si no es una acción ejecutable, responde normal en español y breve."
)

# Historial corto de la conversación (se recorta solo).
HISTORY: list[dict[str, str]] = []
_MAX_TURNS = 10


def available() -> bool:
    return bool(config.OPENAI_API_KEY)


def ask(text: str) -> str:
    if not available():
        return (
            "🧠 No tengo API configurada, así que solo respondo por reglas locales.\n"
            "Para activar el cerebro copia '.env.example' a '.env' y pon tu "
            "OPENAI_API_KEY (o la URL de Groq/LM Studio en OPENAI_BASE_URL).\n\n"
            + help_short()
        )
    try:
        from openai import OpenAI
    except ImportError:
        return "⚠️ Falta la librería 'openai'. Ejecuta: pip install -r requirements.txt"

    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += HISTORY
        messages.append({"role": "user", "content": text})

        resp = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=800,
        )
        reply = (resp.choices[0].message.content or "").strip()
        if not reply:
            return "⚠️ La API devolvió una respuesta vacía."

        HISTORY.append({"role": "user", "content": text})
        HISTORY.append({"role": "assistant", "content": reply})
        del HISTORY[: max(0, len(HISTORY) - _MAX_TURNS * 2)]
        return reply
    except Exception as exc:  # noqa: BLE001 - queremos devolver el error al usuario
        return f"⚠️ Error consultando la API ({type(exc).__name__}): {exc}"


def help_short() -> str:
    return (
        "Mientras tanto puedes pedirme: abrir apps, levantar mysql, "
        "ver puertos/procesos, crear carpetas y archivos, o dictar texto."
    )
