"""Síntesis de voz (TTS). Carga pyttsx3 solo cuando se necesita."""
from __future__ import annotations

import config

_engine = None


def _init():
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 185)
    # Intenta elegir una voz en español
    try:
        for voice in engine.getProperty("voices") or []:
            vid = (voice.id or "").lower()
            name = (voice.name or "").lower()
            if "es_" in vid or "spanish" in name or "español" in name or "microsoft" in name and "helena" in name:
                engine.setProperty("voice", voice.id)
                break
    except Exception:  # noqa: BLE001 - la voz por defecto también sirve
        pass
    return engine


def say(text: str) -> None:
    """Habla el texto; si falla, no rompe el programa (solo imprime)."""
    global _engine
    if not text or text == "__EXIT__":
        return
    try:
        if _engine is None:
            _engine = _init()
        _engine.say(text)
        _engine.runAndWait()
    except Exception:  # noqa: BLE001 - pyttsx3 a veces se colga; se reinicia
        _engine = None
        try:
            _engine = _init()
            _engine.say(text)
            _engine.runAndWait()
        except Exception:  # noqa: BLE001
            _engine = None
