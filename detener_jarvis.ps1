# Detiene Jarvis (tambien sirve si arrancó oculto con Windows)
# Primero crea la bandera para que el watchdog del VBS NO lo relance.
$lock = Join-Path $PSScriptRoot "jarvis.lock"
$stop = Join-Path $PSScriptRoot "jarvis.stop"
New-Item -ItemType File -Path $stop -Force | Out-Null

$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*jarvis.py*" }
foreach ($p in $procs) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Detenido: pid $($p.ProcessId)"
}
if (Test-Path $lock) { Remove-Item $lock -Force }
if (-not $procs) { Write-Host "Jarvis no estaba corriendo." }
Write-Host "Parado. Para volver a arrancar: doble clic en 'Jarvis (voz)'."
