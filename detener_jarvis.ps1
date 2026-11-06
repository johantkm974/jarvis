# Detiene Jarvis (tambien sirve si arrancó oculto con Windows)
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*jarvis.py*" }
foreach ($p in $procs) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Detenido: pid $($p.ProcessId)"
}
$lock = Join-Path $PSScriptRoot "jarvis.lock"
if (Test-Path $lock) { Remove-Item $lock -Force }
if (-not $procs) { Write-Host "Jarvis no estaba corriendo." }
Write-Host "Listo. Para volver a arrancar: doble clic en 'Jarvis (voz)'."
