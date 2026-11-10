# Build + isporuka. Rezultat u release\<verzija>\:
#   AutoStakla_<ver>_PRVA_INSTALACIJA.zip  - Setup + uputstvo + prezentacija + OBAVEZNO_PROCITAJ.txt
#   AutoStakla_update_<ver>.zip            - za Alati > Azuriraj iz fajla (+ uputstvo + OBAVEZNO_PROCITAJ.txt)
#   AutoStakla_Setup_<ver>.exe             - sam Setup (za probu)
# Lokalno se pri svakom build-u osvezava JEDNA dokumentacija u dokumentacija\.
#
# Upotreba:  powershell -ExecutionPolicy Bypass -File build.ps1   [-SkipTests]
# Pre build-a: podici VERSION u src\autostakla\version.py i upisati izmene u IZMENE.md.
param([switch]$SkipTests)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py   = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "C:\Program Files (x86)\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 nije instaliran (winget install JRSoftware.InnoSetup)" }

function Step($text) { Write-Host "`n--- $text" -ForegroundColor Cyan }
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what nije uspeo (kod $LASTEXITCODE)" } }

$info = & $py -c "import sys; sys.path.insert(0,'src'); from autostakla import version as v; print(v.VERSION, v.EDITION, v.APP_NAME)"
$ver, $edition, $appName = $info.Split(" ")
Write-Host "=== $appName $ver ($edition) ===" -ForegroundColor Cyan

$isp = Join-Path $PSScriptRoot "build\isporuka"
Remove-Item $isp -Recurse -Force -ErrorAction SilentlyContinue

Step "OBAVEZNO_PROCITAJ.txt iz IZMENE.md"
& $py tools\isporuka.py tekstovi $isp; Check "IZMENE.md (nema izmena za $ver?)"

if (-not $SkipTests) {
    Step "Testovi"
    & $py -m pytest -q; Check "Testovi"
}

Step "Dokumentacija (snimci, uputstva, prezentacija)"
& $py tools\docs\snimci.py | Out-Null;      Check "Snimci ekrana"
& $py tools\docs\korisnicko.py | Out-Null;  Check "Korisnicko uputstvo"
& $py tools\docs\tehnicko.py | Out-Null;    Check "Tehnicko uputstvo"
& $py tools\docs\prezentacija.py | Out-Null; Check "Prezentacija"

$uputstvo = Join-Path $PSScriptRoot "dokumentacija\AutoStakla_Korisnicko_uputstvo.pdf"
$appDocs = Join-Path $isp "app_docs"
New-Item -ItemType Directory -Force $appDocs | Out-Null
Copy-Item $uputstvo $appDocs
Copy-Item (Join-Path $isp "update\OBAVEZNO_PROCITAJ.txt") $appDocs

Step "Program (PyInstaller)"
& $py tools\make_icon.py | Out-Null
$src  = Join-Path $PSScriptRoot "src"
$pkg  = Join-Path $src "autostakla"
$icon = Join-Path $pkg "resources\icon.ico"
$dist = Join-Path $PSScriptRoot "build\dist"
$work = Join-Path $PSScriptRoot "build\work"
$spec = Join-Path $PSScriptRoot "build\spec"

& $py -m PyInstaller --noconfirm --clean --windowed --log-level WARN --name AutoStakla `
    --icon $icon --paths $src `
    --add-data "$pkg\migrations;migrations" --add-data "$pkg\resources;resources" `
    --add-data "$appDocs;docs" `
    --distpath $dist --workpath $work --specpath $spec `
    (Join-Path $pkg "main.py")
Check "PyInstaller (program)"

& $py -m PyInstaller --noconfirm --clean --windowed --onefile --log-level WARN --name Updater `
    --icon $icon --distpath "$dist\_updater" --workpath $work --specpath $spec `
    (Join-Path $PSScriptRoot "updater\updater.py")
Check "PyInstaller (updater)"
Copy-Item "$dist\_updater\Updater.exe" "$dist\AutoStakla\Updater.exe" -Force

$rel = Join-Path $PSScriptRoot "release\$ver"
Remove-Item $rel -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $rel | Out-Null

Step "Update paket"
& $py tools\make_update_zip.py "$dist\AutoStakla" "$rel\${appName}_update_$ver.zip" `
    (Join-Path $isp "update\OBAVEZNO_PROCITAJ.txt") $uputstvo | Out-Null
Check "Update zip"

Step "Setup"
& $iscc /Q "/DAppVersion=$ver" "/DAppName=$appName" "/DSourceDir=$dist\AutoStakla" `
    "/DIconFile=$icon" "/DOutDir=$rel" installer\AutoStakla.iss
Check "Inno Setup"

Step "Paket za prvu instalaciju"
& $py tools\isporuka.py prva "$rel\${appName}_Setup_$ver.exe" "$rel\${appName}_${ver}_PRVA_INSTALACIJA.zip" `
    (Join-Path $isp "prva\OBAVEZNO_PROCITAJ.txt") | Out-Null
Check "Paket za prvu instalaciju"

Write-Host "`nGotovo: $rel" -ForegroundColor Green
Get-ChildItem $rel | ForEach-Object { "  {0}  ({1:N1} MB)" -f $_.Name, ($_.Length / 1MB) }
