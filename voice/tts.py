"""Síntesis de voz (TTS). Carga pyttsx3 solo cuando se necesita.

Estrategia (JARVIS_TTS en .env):
  auto      -> pyttsx3; si falla, respaldo con System.Speech de Windows
  pyttsx3   -> solo pyttsx3
  sapi      -> solo el respaldo de PowerShell (más lento, muy fiable)
  off       -> sin voz

Cada fallo y la primera llamada buena quedan impresos en log.txt,
y se avisa si la llamada fue tan rápida que probablemente NO habló.
"""
from __future__ import annotations

import os
import time

import config  # noqa: F401 - asegura que .env esté cargado

_engine = None
_primera_vez = False


def _init():
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 185)
    # Intenta elegir una voz en español
    try:
        for voice in engine.getProperty("voices") or []:
            vid = (voice.id or "").lower()
            name = (voice.name or "").lower()
            if ("es_" in vid or "spanish" in name or "español" in name
                    or ("microsoft" in name and "helena" in name)):
                engine.setProperty("voice", voice.id)
                break
    except Exception:  # noqa: BLE001 - la voz por defecto también sirve
        pass
    return engine


def _aviso_duracion(dt: float, texto: str) -> None:
    """Si terminó sospechosamente rápido, casi seguro no llegó a hablar."""
    global _primera_vez
    minimo = len(texto) / 40          # hablar cuesta ~40 caracteres como mínimo
    if dt < minimo:
        print(f"(tts) ⚠️ sospechoso: {len(texto)} caracteres en {dt:.2f}s "
              f"(¿no llegó a salir el audio?)")
    else:
        print(f"(tts) ✅ voz emitida en {dt:.1f}s")
        _primera_vez = True


def _hablar_sapi(texto: str) -> None:
    """Respaldo: SpeechSynthesizer de Windows en un proceso PowerShell aparte."""
    global _primera_vez
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$v = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and "
        "$_.VoiceInfo.Culture.Name -like 'es*' } | Select-Object -First 1; "
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
        "$s.Speak([Console]::In.ReadToEnd())"
    )
    import subprocess

    t0 = time.monotonic()
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        input=texto, capture_output=True, text=True, encoding="utf-8", timeout=90,
    )
    dt = time.monotonic() - t0
    _primera_vez = True
    _aviso_duracion(dt, texto)


def say(text: str) -> None:
    """Habla el texto; nunca rompe el programa (solo imprime el problema)."""
    global _engine, _primera_vez
    if not text or text == "__EXIT__":
        return
    modo = os.getenv("JARVIS_TTS", "auto").strip().lower()
    if modo in ("off", "ninguno", "no"):
        return
    if modo == "sapi":
        try:
            _hablar_sapi(text)
        except Exception as exc:  # noqa: BLE001
            print(f"(tts) respaldo SAPI falló ({type(exc).__name__}: {exc})")
        return

    t0 = time.monotonic()
    try:
        if _engine is None:
            _engine = _init()
        _engine.say(text)
        _engine.runAndWait()
        dt = time.monotonic() - t0
        if not _primera_vez:
            print(f"(tts) pyttsx3 listo (primera llamada, {dt:.1f}s)")
            _primera_vez = True
        _aviso_duracion(dt, text)
        return
    except Exception as exc:  # noqa: BLE001 - pyttsx3 a veces se rompe
        print(f"(tts) ❌ pyttsx3 falló ({type(exc).__name__}: {exc}); "
              f"uso el respaldo de Windows")
        _engine = None
    try:
        _hablar_sapi(text)
    except Exception as exc:  # noqa: BLE001
        print(f"(tts) ❌ respaldo SAPI también falló ({type(exc).__name__}: {exc})")
