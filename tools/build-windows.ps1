param([string]$Pnpm = 'pnpm', [switch]$Installer)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $engineData = @()
    $engineData += @('--add-data', 'src/pdfmd/data;pdfmd/data')
    # Some managed Python distributions ship an SSL distrust resource beside ssl.py.
    # Preserve that resource when freezing; never bypass certificate verification.
    $sslResource = & '.venv/Scripts/python.exe' -c "import pathlib, ssl; print(pathlib.Path(ssl.__file__).with_name('codex-rejected-cas.pem'))"
    if (Test-Path -LiteralPath $sslResource) { $engineData += @('--add-data', "${sslResource};.") }
    & '.venv/Scripts/python.exe' -m PyInstaller --noconfirm --name pdf-md-engine --onedir --console --distpath build/engine --workpath build/pyinstaller --specpath build --paths src --collect-submodules langgraph --collect-submodules langgraph.checkpoint.sqlite --collect-data pymupdf --copy-metadata langgraph --copy-metadata langchain-core --copy-metadata langgraph-checkpoint --copy-metadata langgraph-checkpoint-sqlite --hidden-import csv --hidden-import statistics --hidden-import xml.etree.ElementTree --hidden-import decimal --hidden-import fractions @engineData tools/engine-entry.py
    if ($LASTEXITCODE -ne 0) { throw 'The Python engine build failed.' }
    & 'build/engine/pdf-md-engine/pdf-md-engine.exe' --help
    if ($LASTEXITCODE -ne 0) { throw 'The frozen engine failed its startup check.' }
    & 'build/engine/pdf-md-engine/pdf-md-engine.exe' --task-script 'tools/check-frozen-engine.py'
    if ($LASTEXITCODE -ne 0) { throw 'The frozen engine failed its TLS and trusted-script check.' }
    & $Pnpm run build
    if ($LASTEXITCODE -ne 0) { throw 'The desktop build failed.' }
    if ($Installer) { & $Pnpm exec electron-builder --win nsis }
    else { & $Pnpm exec electron-builder --win --dir }
    if ($LASTEXITCODE -ne 0) { throw 'Windows packaging failed.' }
} finally { Pop-Location }
