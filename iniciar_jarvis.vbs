' Jarvis - arranque OCULTO con Windows (modo voz, sin ventanas)
' Si Jarvis se cae, se relanza solo (bucle watchdog).
' Para pararlo: "Detener Jarvis" (crea jarvis.stop) o el acceso directo.
Option Explicit
Dim shell, fso, dir, cmd, stopFile, logFile, f
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = dir

stopFile = dir & "\jarvis.stop"
logFile  = dir & "\log.txt"

' Quitar la bandera de parada de una sesión anterior
If fso.FileExists(stopFile) Then fso.DeleteFile stopFile, True

' Rota el log si creció demasiado (lo apendamos para no perder el historial)
If fso.FileExists(logFile) Then
  If fso.GetFile(logFile).Size > 500000 Then fso.DeleteFile logFile, True
End If

cmd = "cmd /c cd /d """ & dir & """ && python -u jarvis.py --voz >> log.txt 2>&1"

Do
  ' Marca cada arranque/reinicio en el log
  Set f = fso.OpenTextFile(logFile, 8, True)   ' 8 = ForAppending
  f.WriteLine "---- (re)arranque de Jarvis ----"
  f.Close
  shell.Run cmd, 0, True                        ' espera a que termine
  If fso.FileExists(stopFile) Then Exit Do      ' parada manual: no relanzar
  WScript.Sleep 3000                            ' se cayó -> en 3 s vuelve
Loop
