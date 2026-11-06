#!/usr/bin/env python3
"""Jarvis - asistente personal para tu PC.

Modos:
  python jarvis.py              # texto en consola (sin dependencias de voz)
  python jarvis.py --ptt        # pulsas Enter y hablas
  python jarvis.py --voz        # palabra de activación "hey jarvis"
  python jarvis.py --cmd "..."  # ejecuta un solo comando (para pruebas)
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from brain import router
from brain.local_intent import help_text


def _fix_console() -> None:
    """Evita UnicodeEncodeError con emojis/acentos en la consola de Windows."""
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:  # noqa: BLE001
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


# --- Control de instancia (un solo Jarvis escuchando a la vez) ---------------
LOCK_FILE = __import__("pathlib").Path(__file__).resolve().parent / "jarvis.lock"


def _pid_alive(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        import psutil

        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except Exception:  # noqa: BLE001
        return False


def _acquire_lock() -> bool:
    """True si este proceso puede arrancar (no hay otra instancia viva)."""
    if LOCK_FILE.is_file():
        try:
            pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pid = 0
        if _pid_alive(pid):
            return False
        # Cadáver de un corte anterior -> lo tomamos
    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        pass
    return True


def _release_lock() -> None:
    try:
        if LOCK_FILE.is_file() and LOCK_FILE.read_text(encoding="utf-8").strip() == str(os.getpid()):
            LOCK_FILE.unlink()
    except OSError:
        pass

BANNER = """
╔══════════════════════════════════════════════════════════╗
║  J A R V I S   ·   asistente personal                   ║
║  Escribe 'ayuda' para ver comandos, 'salir' para salir.  ║
╚══════════════════════════════════════════════════════════╝"""


def _say(mode: str, no_tts: bool, text: str) -> None:
    if mode == "texto" or no_tts:
        return
    spoken = _clean_for_speech(text)   # el TTS no debe leer ``` ni ** ni emoji
    if not spoken:
        return
    try:
        from voice import tts

        tts.say(spoken)
    except Exception as exc:  # noqa: BLE001
        print(f"   (tts no disponible: {exc})")


def _input_text() -> str | None:
    try:
        return input("\nTú> ")
    except EOFError:
        return None


def _input_ptt() -> str | None:
    try:
        input("\n[Enter para hablar] ")
    except (EOFError, KeyboardInterrupt):
        return None
    from voice import stt

    print("Escuchando...")
    text = stt.listen()
    print(f"Escuchado> {text or '(nada)'}")
    return text


def _strip_wakeword(text: str) -> str:
    """Quita 'hey jarvis' / 'jarvis' del principio de lo que transcribe."""
    import re

    return re.sub(r"^(hey\s+)?jarvis[\s,.:;-]*", "", text, flags=re.IGNORECASE).strip()


# --- Filtro de ruido (tele, vídeos, conversaciones de fondo) -----------------
# En modo escucha permanente el micrófono también capta la tele. Para no
# reaccionar a "Gracias por ver el video" o "La Hora de la Cámara",
# solo pasamos frases que parecen una orden o una pregunta.
# Desactivable con JARVIS_FILTRO=0 en .env
_Q_START = {
    "que", "qué", "cual", "cuál", "cuales", "cuáles", "cuanto", "cuánto",
    "cuanta", "cuánta", "cuando", "cuándo", "donde", "dónde", "como", "cómo",
    "por", "quien", "quién", "quienes", "cuantos", "cuántos",
}
_SOCIAL_START = {
    "hola", "buenas", "buenos", "hey", "oye", "gracias", "chao",
    "adios", "adiós", "perdón", "perdon", "saludos", "jarvis",
}
_VERBS = re.compile(
    r"\b(abre|abrir|crea|crear|creame|haz|hazme|levanta|inicia|arranca|prende|"
    r"deten|detén|cierra|apaga|apagame|escribe|dicta|lee|leer|lista|muestra|"
    r"busca|dime|cuentame|cuéntame|explica|explicame|reproduce|salir|ayuda|"
    r"enciende|reinicia|borra|elimina|descarga|instala|actualiza)\b",
    re.IGNORECASE,
)
_PHRASE = re.compile(
    r"(que\s+hora|hora\s+es\b|dime\s+la\s+hora|que\s+d[ií]a|fecha\s+de\s+hoy|"
    r"que\s+puertos|que\s+procesos|cu[aá]nta\s+ram|memoria\s+ram|"
    r"para\s+(mysql|xampp|apache|base de datos))",
    re.IGNORECASE,
)


def vale_la_pena(text: str) -> bool:
    """True si la frase parece una orden/pregunta (no ruido de fondo)."""
    low = text.strip().lower()
    if len(low) < 3:
        return False
    if "?" in text:
        return True
    words = re.findall(r"[\wáéíóúüñ]+", low)
    if not words:
        return False
    if words[0] in _Q_START:
        return True
    if _VERBS.search(low) or _PHRASE.search(low):
        return True
    # Saludo/cortesía corto: "hola", "gracias"... pero NO
    # "Gracias por ver el video" (5 palabras: eso es la tele)
    if words[0] in _SOCIAL_START and len(words) <= 4:
        return True
    return False


_EMOJI = re.compile(
    r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D"
    r"\u2190-\u21FF\u2500-\u257F]+"
)


def _clean_for_speech(text: str) -> str:
    """Deja la respuesta lista para el TTS: sin markdown, sin código, sin emoji."""
    if not text or text == "__EXIT__":
        return ""
    out = re.sub(r"```.*?```", " . Te muestro el código en pantalla. ",
                      text, flags=re.S)
    out = re.sub(r"^\s*---+\s*$", "", out, flags=re.M)      # separadores
    out = re.sub(r"\[\[ACCION:.*?\]\]", "", out)
    out = re.sub(r"`[^`\n]*`", "", out)                          # código inline
    out = re.sub(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+", "", out, flags=re.M)  # listas
    out = re.sub(r"^\s{0,3}#{1,6}\s*", "", out, flags=re.M)  # encabezados
    out = re.sub(r"[*_~]{1,3}", "", out)                         # negritas
    out = _EMOJI.sub("", out)
    out = re.sub(r"\s+", " ", out).strip(" -–—:;,.")
    return out[:700]


_session_until = 0.0


def _input_voz() -> str | None:
    """Escucha permanente (si ALWAYS) o palabra de activación + sesión libre."""
    global _session_until
    import time

    import config
    from voice import stt, wake

    # --- Modo escucha permanente: sin frase de activación -----------------
    if config.ALWAYS:
        text = stt.listen()
        if not text:
            return ""
        text = _strip_wakeword(text)
        if len(text) < 3:      # ruido o solo "jarvis": lo ignoramos
            return ""
        if config.FILTRO and not vale_la_pena(text):
            print(f"Escuchado> {text}   (ignorado por ruido)")
            return ""
        print(f"Escuchado> {text}")
        return text

    # --- Sesión abierta: sigue hablando directamente ----------------------
    if time.time() < _session_until:
        print("\n🎙️  Sesión activa: dame tu orden sin repetir «hey jarvis»...")
        while time.time() < _session_until:
            text = stt.listen()
            if text:
                print(f"Escuchado> {text}")
                _session_until = time.time() + config.SESSION_SECONDS
                return _strip_wakeword(text)
            print("   (no te oí... sigo en la sesión)")
        _session_until = 0.0
        print("🕐 Sesión cerrada. Di «hey jarvis» cuando me necesites.")
        return ""

    # --- Espera: solo la palabra de activación ----------------------------
    print(f"\nEscuchando «{config.WAKE_WORD}»... (Ctrl+C para salir)")
    wake.wait()
    print("🎤 Te escucho...")
    text = stt.listen()
    if not text:
        print("Escuchado> (nada)")
        return ""
    print(f"Escuchado> {text}")
    _session_until = time.time() + config.SESSION_SECONDS
    return _strip_wakeword(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jarvis - asistente personal")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--texto", action="store_true", help="entrada por texto (por defecto)")
    modo.add_argument("--ptt", action="store_true", help="pulsas Enter y hablas")
    modo.add_argument("--voz", action="store_true", help="palabra de activación")
    parser.add_argument("--sin-tts", action="store_true", help="no hablar en voz alta")
    parser.add_argument("--cmd", help="ejecuta un único comando y sale")
    parser.add_argument("--test-mic", nargs="?", const=60, type=int, default=0, metavar="SEG",
                        help="mide micrófono y wake word en vivo (60 s por defecto)")
    parser.add_argument("--siempre", action="store_true",
                        help="escucha permanente: sin decir 'hey jarvis'")
    args = parser.parse_args(argv)
    _fix_console()

    if args.siempre:
        import config as _cfg

        _cfg.ALWAYS = True

    if args.test_mic:
        from voice import diagnostico

        return diagnostico.run(args.test_mic)

    mode = "voz" if args.voz else "ptt" if args.ptt else "texto"

    # Si falta la voz, cae a texto con aviso (el programa siempre funciona)
    if mode in ("voz", "ptt"):
        try:
            import pyaudio  # noqa: F401
            from voice import stt  # noqa: F401
        except ImportError as exc:
            print(f"⚠️ Voz no disponible ({exc}); paso a modo texto.")
            mode = "texto"

    if args.cmd:
        reply, source = router.route(args.cmd)
        print(f"Jarvis [{source}]:\n{reply}")
        return 0

    import atexit

    if not _acquire_lock():
        print("⚠️ Jarvis YA está corriendo en segundo plano (di «hey jarvis» "
              "o mira log.txt). No abro una segunda instancia.")
        return 1
    atexit.register(_release_lock)

    import config as _cfg

    print(BANNER)
    if _cfg.ALWAYS:
        print("🎙️  MODO ESCUCHA PERMANENTE: háblale directamente, "
              "sin decir «hey jarvis».")
    print(help_text())

    while True:
        try:
            if mode == "voz":
                user = _input_voz()
            elif mode == "ptt":
                user = _input_ptt()
            else:
                user = _input_text()
        except KeyboardInterrupt:
            print("\n\nHasta luego. 👋")
            return 0
        except Exception as exc:  # noqa: BLE001 - un fallo de mic no mata el programa
            print(f"⚠️ Error de entrada ({type(exc).__name__}): {exc}")
            mode = "texto"
            continue

        if user is None:
            print("\nHasta luego. 👋")
            return 0
        if not user.strip():
            continue

        try:
            reply, source = router.route(user)
        except Exception as exc:  # noqa: BLE001
            reply, source = f"⚠️ Error interno ({type(exc).__name__}): {exc}", "error"

        print(f"\nJarvis [{source}]> {reply}")
        if reply == "__EXIT__":
            print("Hasta luego. 👋")
            _say(mode, args.sin_tts, "Hasta luego.")
            return 0
        _say(mode, args.sin_tts, reply)


if __name__ == "__main__":
    sys.exit(main())
