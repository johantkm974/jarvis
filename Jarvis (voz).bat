@echo off
title Jarvis - modo voz
cd /d "%~dp0"
python jarvis.py --voz
if errorlevel 1 (
  echo.
  echo [Aviso] Jarvis no arranco: puede que ya este corriendo en segundo plano.
  echo         Mira "log.txt" o ejecuta "Detener Jarvis.bat" y vuelve a intentarlo.
  pause
)
