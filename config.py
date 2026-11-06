"""Configuración central de Jarvis.

Todo lo ajustable vive aquí o en el archivo `.env` (sin dependencias externas).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "workspace"   # donde se crean archivos/carpetas por defecto


def _load_env() -> None:
    """Carga el archivo .env si existe (parser propio, cero dependencias)."""
    env_file = BASE_DIR / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

# --- Cerebro (API) ----------------------------------------------------------
# Si no hay clave, Jarvis funciona igual con las reglas locales (0 costo).
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "") or None   # compatible Groq/etc.
MODEL = os.getenv("JARVIS_MODEL", "gpt-4o-mini")

# --- Sistema ----------------------------------------------------------------
XAMPP_DIR = Path(os.getenv("XAMPP_DIR", r"C:\xampp"))
TERMINAL = os.getenv("JARVIS_TERMINAL", "auto")   # auto | wt | cmd | powershell
MYSQL_PORT = int(os.getenv("JARVIS_MYSQL_PORT", "3306"))
APACHE_PORT = int(os.getenv("JARVIS_APACHE_PORT", "80"))

# --- Voz --------------------------------------------------------------------
WAKE_WORD = os.getenv("JARVIS_WAKE", "hey jarvis")
# Umbral de detección de la wake word (baja a 0.30 si no te detecta)
WAKE_THRESHOLD = float(os.getenv("JARVIS_WAKE_THRESHOLD", "0.35"))
# Segundos de conversación libre tras decir "hey jarvis" (sin repetir la frase)
SESSION_SECONDS = float(os.getenv("JARVIS_SESION", "90"))
# 1 = ESCUCHA PERMANENTE: te oye siempre, sin decir "hey jarvis"
# 0 = modo clásico: esperas la palabra de activación
ALWAYS = os.getenv("JARVIS_SIEMPRE", "0").strip().lower() in ("1", "true", "si", "sí", "yes")
# 1 = FILTRO DE RUIDO: en escucha permanente solo reacciona a órdenes y
# preguntas (evita contestar a la tele o a un vídeo de YouTube).
# 0 = responde a cualquier frase que transcriba (sin filtrar).
FILTRO = os.getenv("JARVIS_FILTRO", "1").strip().lower() in ("1", "true", "si", "sí", "yes")
# Modelo ONNX de la palabra de activación (sin tflite: no existe en Windows)
WAKE_MODEL = os.getenv("JARVIS_WAKE_MODEL", "hey_jarvis_v0.1.onnx")
LANGUAGE = os.getenv("JARVIS_LANG", "es")
WHISPER_MODEL = os.getenv("JARVIS_WHISPER", "base")   # tiny|base|small...
ENERGY_THRESHOLD = int(os.getenv("JARVIS_ENERGY", "400"))  # sensibilidad del mic

WORKSPACE.mkdir(exist_ok=True)
