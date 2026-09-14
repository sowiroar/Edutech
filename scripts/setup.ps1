# Configuración inicial para Windows/PowerShell, una sola vez por clon.
# Equivale a scripts/setup.sh y usa el sh que trae Git for Windows.
$ErrorActionPreference = 'Stop'

Set-Location (git rev-parse --show-toplevel)

$gitRoot = Split-Path (Split-Path (Get-Command git).Source)
$sh = Join-Path $gitRoot 'bin\sh.exe'
if (-not (Test-Path $sh)) {
    throw "No se encontró sh.exe de Git for Windows en $sh"
}

& $sh scripts/setup.sh
