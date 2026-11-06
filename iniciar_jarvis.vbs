' Jarvis - arranque OCULTO con Windows (modo voz, sin ventanas)
' Uso doble: también lo puede lanzar el acceso directo del escritorio.
Option Explicit
Dim shell, fso, dir, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = dir
' La salida queda en log.txt por si hay que depurar algo
cmd = "cmd /c cd /d """ & dir & """ && python -u jarvis.py --voz > log.txt 2>&1"
shell.Run cmd, 0, False
