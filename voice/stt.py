"""Reconocimiento de voz (STT).

Orden híbrido:
  1. Groq `whisper-large-v3-turbo` (gratis, mucho más preciso en español)
  2. Si falla, whisper local `faster-whisper` (carga bajo demanda)
"""
from __future__ import annotations

import array
import time

import config

RATE = 16000
CHUNK = 1024          # ~64 ms por bloque
SILENCE_SEC = 0.9     # silencio que corta la frase
MAX_SECONDS = 12      # tope por frase
TIMEOUT_SECONDS = 10  # espera a que empieces a hablar

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_STT_MODEL = "whisper-large-v3-turbo"

# Sesgo de decodificación hacia los comandos de Jarvis (mejora la precisión)
INITIAL_PROMPT = (
    "Comandos: abre youtube, abre chrome, abre github, crea archivo notas, "
    "crea carpeta proyectos, levanta mysql, para mysql, que puertos, que procesos, "
    "escribe hola en archivo notas, lee archivo notas, lista archivos, que hora es."
)

_model = None


def _energy(data: bytes) -> int:
    samples = array.array("h", data)
    if not samples:
        return 0
    return max(max(samples), -min(samples))


def _record_phrase() -> bytes | None:
    """Graba hasta detectar silencio. Devuelve los bytes o None si no hubo voz."""
    import pyaudio

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pa.get_format_from_width(2), channels=1,
                     rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames: list[bytes] = []
    started = False
    silent = 0.0
    t0 = time.time()
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            now = time.time()
            if not started:
                if _energy(data) > config.ENERGY_THRESHOLD:
                    started = True
                    frames.append(data)
                elif now - t0 > TIMEOUT_SECONDS:
                    return None
                continue
            frames.append(data)
            if _energy(data) < config.ENERGY_THRESHOLD:
                silent += CHUNK / RATE
            else:
                silent = 0.0
            if silent > SILENCE_SEC or now - t0 > MAX_SECONDS:
                break
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
    return b"".join(frames) if started else None


def _wav_bytes(pcm: bytes) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def _transcribe_groq(pcm: bytes) -> str | None:
    """STT en la nube con Groq (gratis). None si no está configurado o falla."""
    if "groq" not in (config.OPENAI_BASE_URL or "").lower():
        return None
    if not config.OPENAI_API_KEY:
        return None
    try:
        import requests

        resp = requests.post(
            GROQ_STT_URL,
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            files={"file": ("jarvis.wav", _wav_bytes(pcm), "audio/wav")},
            data={"model": GROQ_STT_MODEL, "language": config.LANGUAGE,
                  "response_format": "json"},
            timeout=30,
        )
        if resp.ok:
            text = (resp.json().get("text") or "").strip()
            return text or None
        print(f"[stt] Groq {resp.status_code}: {resp.text[:160]}")
    except Exception as exc:  # noqa: BLE001
        print(f"[stt] Groq falló ({type(exc).__name__}), uso whisper local")
    return None


def _whisper():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def unload() -> None:
    """Libera la RAM del modelo de voz local."""
    global _model
    _model = None


def _transcribe_local(pcm: bytes) -> str | None:
    import numpy as np

    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    model = _whisper()
    segments, _info = model.transcribe(
        audio,
        language=config.LANGUAGE,
        beam_size=2,
        initial_prompt=INITIAL_PROMPT,
        condition_on_previous_text=False,
        vad_filter=True,
    )
    text = " ".join(seg.text for seg in segments).strip()
    return text or None


def listen() -> str | None:
    """Escucha una frase y la transcribe. None si no hubo voz."""
    pcm = _record_phrase()
    if not pcm:
        return None
    return _transcribe_groq(pcm) or _transcribe_local(pcm)
