$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create Python environment.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --onefile --windowed --name QuickColor --hidden-import pystray._win32 quick_color.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
Write-Host 'Built: dist\QuickColor.exe'
