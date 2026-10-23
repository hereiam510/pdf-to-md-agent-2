param([string]$Uv = 'uv', [string]$Pnpm = 'pnpm')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    & $Uv sync --frozen --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency setup failed.' }
    & $Pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Desktop dependency setup failed.' }
    Write-Host 'Ready. Run pnpm dev, or tools/build-windows.ps1 to create the Windows app.'
} finally { Pop-Location }
