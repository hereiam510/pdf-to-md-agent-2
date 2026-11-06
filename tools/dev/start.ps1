param([string]$Pnpm = 'pnpm', [string]$Workspace = '', [switch]$Packaged,
    [string]$CredentialFile = '', [switch]$NoCredentialFile)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location -LiteralPath $projectRoot
$previousData = $env:PDFMD_DATA
$previousCredentialFile = $env:PDFMD_CREDENTIAL_FILE
$previousSkipCredentialFile = $env:PDFMD_SKIP_CREDENTIAL_FILE
try {
    if ($CredentialFile -and $NoCredentialFile) { throw 'Choose -CredentialFile or -NoCredentialFile, not both.' }
    if ($Packaged -and ($CredentialFile -or $NoCredentialFile)) { throw 'Credential-file options apply only to development launches.' }
    if (-not $Workspace) { $Workspace = Join-Path $projectRoot 'workspaces/default' }
    $env:PDFMD_DATA = [System.IO.Path]::GetFullPath($Workspace)
    if ($CredentialFile) {
        $env:PDFMD_CREDENTIAL_FILE = (Resolve-Path -LiteralPath $CredentialFile -ErrorAction Stop).Path
        $env:PDFMD_SKIP_CREDENTIAL_FILE = '0'
    } elseif ($NoCredentialFile) { $env:PDFMD_SKIP_CREDENTIAL_FILE = '1' }
    if ($Packaged) {
        $desktopExe = Join-Path $projectRoot 'release/win-unpacked/PDF Markdown Workbench.exe'
        if (-not (Test-Path -LiteralPath $desktopExe)) { throw 'Run tools/build/build-windows.ps1 first.' }
        & $desktopExe
    } else {
        if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run tools/dev/setup.ps1 first.' }
        & $Pnpm run dev
        if ($LASTEXITCODE -ne 0) { throw 'The desktop app stopped with an error.' }
    }
} finally {
    $env:PDFMD_DATA = $previousData
    $env:PDFMD_CREDENTIAL_FILE = $previousCredentialFile
    $env:PDFMD_SKIP_CREDENTIAL_FILE = $previousSkipCredentialFile
    Pop-Location
}
