# Proba AutoStaklaBetter-a sa demo podacima. Koristi ZASEBNU bazu u demo_root\ – prava baza se ne dira.
#   powershell -ExecutionPolicy Bypass -File tools\probaj_better.ps1         (prvi put napravi demo bazu, pa pokrene)
#   powershell -ExecutionPolicy Bypass -File tools\probaj_better.ps1 -Novo   (nova demo baza od nule)
param([switch]$Novo)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"
$env:AUTOSTAKLA_ROOT = Join-Path $root "demo_root"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = Join-Path $root "src"   # da se paket autostakla nađe bez obzira odakle se skript pokreće

if ($Novo -and (Test-Path $env:AUTOSTAKLA_ROOT)) { Remove-Item -Recurse -Force $env:AUTOSTAKLA_ROOT }
if (-not (Test-Path (Join-Path $env:AUTOSTAKLA_ROOT "data\stakla.db"))) {
    Write-Host "Pravim demo bazu (traje desetak sekundi)..." -ForegroundColor Cyan
    & $py (Join-Path $root "tools\demo_better.py")
}
& $py (Join-Path $root "src\autostakla\main.py")
