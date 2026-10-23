param([string]$Pnpm = 'pnpm', [string]$Workspace = '', [switch]$Packaged)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not $Workspace) { $Workspace = Join-Path $projectRoot 'workspaces/default' }
    $previousData = $env:PDFMD_DATA
    $env:PDFMD_DATA = [System.IO.Path]::GetFullPath($Workspace)
    if ($Packaged) {
        $desktopExe = Join-Path $projectRoot 'release/win-unpacked/PDF Markdown Workbench.exe'
        if (-not (Test-Path -LiteralPath $desktopExe)) { throw 'Run tools/build-windows.ps1 first.' }
        & $desktopExe
    } else {
        if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run tools/setup.ps1 first.' }
        & $Pnpm run dev
        if ($LASTEXITCODE -ne 0) { throw 'The desktop app stopped with an error.' }
    }
} finally { $env:PDFMD_DATA = $previousData; Pop-Location }
