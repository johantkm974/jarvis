"""Palabra de activación (wake word) con openWakeWord.

Es ultraligero (~10 MB en RAM) y corre siempre en segundo plano.
OJO: en Windows no existe `tflite-runtime`, así que se usan los modelos ONNX.
"""
from __future__ import annotations

from pathlib import Path

import config

SAMPLES_PER_CHUNK = 1600   # 100 ms a 16 kHz
THRESHOLD = config.WAKE_THRESHOLD


def available() -> bool:
    try:
        import openwakeword  # noqa: F401
        import pyaudio  # noqa: F401
    except ImportError:
        return False
    return True


def _load_model():
    """Descarga (si falta) y devuelve el modelo ONNX de la wake word."""
    import openwakeword
    from openwakeword.model import Model
    from openwakeword.utils import download_models

    models_dir = Path(openwakeword.__file__).parent / "resources" / "models"
    onnx_path = models_dir / config.WAKE_MODEL
    if not onnx_path.is_file():
        download_models([Path(config.WAKE_MODEL).stem])
    if not onnx_path.is_file():
        raise RuntimeError(f"No pude descargar el modelo {config.WAKE_MODEL}.")
    return Model(wakeword_models=[str(onnx_path)], inference_framework="onnx")


def wait(cancel_check=None) -> bool:
    """Bloquea hasta escuchar la palabra de activación. Devuelve True."""
    import numpy as np

    try:
        import pyaudio
    except ImportError as exc:
        raise RuntimeError(
            "Falta pyaudio. Instala la voz: pip install -r requirements-voz.txt"
        ) from exc

    model = _load_model()

    import time as _time

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pa.get_format_from_width(2), channels=1,
                     rate=16000, input=True, frames_per_buffer=SAMPLES_PER_CHUNK)
    window_best = 0.0
    last_log = _time.time()
    try:
        while True:
            if cancel_check is not None and cancel_check():
                return False
            data = stream.read(SAMPLES_PER_CHUNK, exception_on_overflow=False)
            scores = model.predict(np.frombuffer(data, dtype=np.int16))
            best = max(scores.values()) if scores else 0
            window_best = max(window_best, best)
            if best >= THRESHOLD:
                print(f"[wake] detectado con score {best:.3f}", flush=True)
                return True
            now = _time.time()
            if now - last_log >= 10:
                print(f"[wake] escuchando... score máx {window_best:.3f} "
                      f"(umbral {THRESHOLD})", flush=True)
                window_best = 0.0
                last_log = now
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
