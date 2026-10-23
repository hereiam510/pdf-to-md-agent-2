@echo off
setlocal
set "PDFMD_DATA=%~dp0workspaces\default"
if not exist "%~dp0release\win-unpacked\PDF Markdown Workbench.exe" (
    echo The Windows build is missing. Run tools\build-windows.ps1 first.
    pause
    exit /b 1
)
start "" "%~dp0release\win-unpacked\PDF Markdown Workbench.exe"
