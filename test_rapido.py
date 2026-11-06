"""Prueba rápida del STT de Groq y del protocolo de acciones de la API."""
import time

import requests

import config
from brain import router

# --- 1) Generar un WAV con la voz de Windows -------------------------------
import pyttsx3

wav = "test_voz.wav"
engine = pyttsx3.init()
engine.save_to_file("Hola Jarvis, abre youtube y crea archivo notas de prueba", wav)
engine.runAndWait()
time.sleep(1)

# --- 2) Transcribirlo con Groq (whisper-large-v3-turbo) --------------------
with open(wav, "rb") as fh:
    resp = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
        files={"file": ("test_voz.wav", fh.read(), "audio/wav")},
        data={"model": "whisper-large-v3-turbo", "language": "es",
              "response_format": "json"},
        timeout=60,
    )
print("GROQ status:", resp.status_code)
print("GROQ texto :", resp.json().get("text") if resp.ok else resp.text[:300])

# --- 3) Protocolo de acciones: la API manda [[ACCION:...]] y se ejecuta -----
for reply in ("[[ACCION:crea archivo desde_api]]",
              "Listo, ya lo hice.",
              "¿En qué puedo ayudarte hoy?"):
    accion = router._try_action(reply)
    print(f"reply={reply!r:45} -> acción={accion!r}")
