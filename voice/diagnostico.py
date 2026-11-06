"""Diagnóstico del micrófono en vivo.

Mide dos cosas a la vez mientras tú hablas:
  1. Energía del audio (¿está captando tu voz el micrófono?)
  2. Puntuación de la wake word (¿le llega el "hey jarvis" al modelo?)

Uso:  python jarvis.py --test-mic
"""
from __future__ import annotations

import array
import time

import config


def run(seconds: int = 60) -> int:
    import numpy as np
    import pyaudio

    from voice import wake as wake_mod

    print("=" * 62)
    print("  DIAGNÓSTICO DEL MICRÓFONO")
    print(f"  Duración: {seconds} s")
    print("=" * 62)
    print("INSTRUCCIONES:")
    print("  1) Ahora di fuerte y claro:  \"HEY JARVIS\"   (2 o 3 veces)")
    print("  2) Después di cualquier cosa como si me dieras una orden")
    print("  3) Al final verás el veredicto. No cierres esta ventana.")
    print("-" * 62, flush=True)

    try:
        model = wake_mod._load_model()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ No pude cargar el modelo de wake word: {exc}")
        return 1

    pa = pyaudio.PyAudio()
    try:
        idx = pa.get_default_input_device_info()["index"]
        name = pa.get_default_input_device_info().get("name")
        stream = pa.open(format=pa.get_format_from_width(2), channels=1, rate=16000,
                         input=True, input_device_index=idx, frames_per_buffer=1600)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ No pude abrir el micrófono: {exc}")
        pa.terminate()
        return 1

    print(f"Dispositivo: {name}\n")
    energies: list[int] = []
    scores: list[float] = []
    t0 = time.time()
    last_print = t0
    try:
        while time.time() - t0 < seconds:
            data = stream.read(1600, exception_on_overflow=False)
            samples = array.array("h", data)
            energy = max(max(samples), -min(samples)) if samples else 0
            raw = model.predict(np.frombuffer(data, dtype=np.int16))
            score = float(max(raw.values())) if raw else 0.0
            energies.append(energy)
            scores.append(score)

            now = time.time()
            if now - last_print >= 5:
                window_e = energies[-80:]
                window_s = scores[-80:]
                print(f"  t={int(now - t0):3d}s | energía máx {max(window_e):6d} "
                      f"| wake score máx {max(window_s):.3f}", flush=True)
                last_print = now
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    e_max, e_avg = max(energies), sum(energies) // max(1, len(energies))
    s_max = max(scores)
    thr = wake_mod.THRESHOLD

    print("\n" + "=" * 62)
    print(f"  RESULTADO:  energía máx {e_max} (media {e_avg})  |  wake score máx {s_max:.3f} (umbral {thr})")
    print("=" * 62)

    ok = True
    if e_max < 500:
        ok = False
        print("🔴 EL MICRÓFONO CASI NO CAPTA VOZ (pico < 500).")
        print("   Solución: Windows → Sonido → Grabación → Micrófono →")
        print("   Propiedades → Niveles → sube el Volumen a 80-100 y el 'Micro Boost' a +10 dB.")
    elif e_max < 2000:
        print("🟡 Volumen bajo pero usable. Sube un poco el micrófono (Niveles → 80).")
    else:
        print("🟢 El micrófono capta tu voz bien.")

    if s_max >= thr:
        print(f"🟢 La wake word se detectó (score {s_max:.3f} ≥ {thr}). Debería responderte ya.")
    elif s_max >= 0.30:
        print(f"🟡 Cerca del umbral ({s_max:.3f}). Bajaré el umbral a 0.35 y probamos.")
    else:
        ok = False
        print(f"🔴 La wake word NO se detectó (score {s_max:.3f} < {thr}).")
        print("   Causas típicas: di exactamente «HEY JARVIS» (no solo 'jarvis'),")
        print("   o el mic está muy bajo (arriba), o hay mucho ruido de fondo.")

    print("\nSi el resultado fue malo, vuelve a lanzarlo y habla más cerca del mic:")
    print("   python jarvis.py --test-mic 90")
    return 0 if ok else 2
