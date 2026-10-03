param(
    [string]$BuildRoot = (Join-Path $env:LOCALAPPDATA 'anki-grip-build'),
    [string]$VenvPath = '',
    [string]$OutputPath = (Join-Path $PSScriptRoot 'release'),
    [switch]$SkipDependencyInstall
)
$ErrorActionPreference = 'Stop'
if (-not $VenvPath) { $VenvPath = Join-Path $BuildRoot 'venv' }
$pythonPath = Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not create build environment.' }
}
if ($SkipDependencyInstall) {
    # Offline builds may reuse a provisioned environment, but never silently
    # package a different Qt or PyInstaller version.
    & $pythonPath -c "from importlib.metadata import version; expected = {'PySide6-Essentials': '6.11.2', 'shiboken6': '6.11.2', 'pyinstaller': '6.22.3'}; actual = {name: version(name) for name in expected}; assert actual == expected, (actual, expected)"
    if ($LASTEXITCODE -ne 0) { throw 'Offline build dependencies do not match pinned versions.' }
}
else {
    & $pythonPath -m pip install -r (Join-Path $PSScriptRoot 'requirements-build.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies.' }
}
$env:PYTHONDONTWRITEBYTECODE = '1'
$originalBuildPath = $env:PATH
$originalPyInstallerCache = $env:PYINSTALLER_CONFIG_DIR
# Codex and other launchers can add native image-library directories to PATH.
# Their old UCRT DLLs must never be picked up as Windows runtime dependencies.
$pythonBase = & $pythonPath -c 'import sys; print(sys.base_prefix)'
$env:PATH = @((Join-Path $VenvPath 'Scripts'), $pythonBase, (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $BuildRoot 'pyinstaller-cache'
Push-Location $PSScriptRoot
try {
    & $pythonPath -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    & $pythonPath (Join-Path $PSScriptRoot 'freeze.py') --noconfirm --clean --onefile --windowed `
        --name anki-grip --distpath $OutputPath `
        --workpath (Join-Path $BuildRoot 'intermediate') `
        --specpath $BuildRoot `
        --add-data "$(Join-Path $PSScriptRoot 'addon');addon" `
        --add-data "$(Join-Path $PSScriptRoot 'assets');assets" `
        --icon (Join-Path $PSScriptRoot 'assets\app.ico') `
        --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick `
        --exclude-module PySide6.QtOpenGL --exclude-module PySide6.QtTest `
        main.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.md'), (Join-Path $PSScriptRoot 'README.zh-CN.md'), (Join-Path $PSScriptRoot 'CHANGELOG.md'), (Join-Path $PSScriptRoot 'LICENSE'), (Join-Path $PSScriptRoot 'THIRD_PARTY_NOTICES.md') -Destination $OutputPath -Force
    $licenseRoot = Join-Path $OutputPath 'licenses'
    New-Item -ItemType Directory -Path $licenseRoot -Force | Out-Null
    $packagesRoot = Join-Path $VenvPath 'Lib\site-packages'
    foreach ($package in @('pyside6_essentials-6.11.2.dist-info', 'shiboken6-6.11.2.dist-info', 'pyinstaller-6.22.3.dist-info')) {
        $sourceLicenses = Join-Path $packagesRoot "$package\licenses"
        if (Test-Path -LiteralPath $sourceLicenses) {
            Copy-Item -LiteralPath $sourceLicenses -Destination (Join-Path $licenseRoot $package) -Recurse -Force
        }
    }
    $pythonBase = & $pythonPath -c 'import sys; print(sys.base_prefix)'
    $pythonLicense = Join-Path $pythonBase 'LICENSE.txt'
    if (Test-Path -LiteralPath $pythonLicense) {
        Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $licenseRoot 'cpython-license.txt') -Force
    }
    & $pythonPath (Join-Path $PSScriptRoot 'tools\artifact_manifest.py') $OutputPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate runtime metadata and checksums.' }
}
finally {
    Pop-Location
    $env:PATH = $originalBuildPath
    if ($originalPyInstallerCache) { $env:PYINSTALLER_CONFIG_DIR = $originalPyInstallerCache }
    else { Remove-Item Env:\PYINSTALLER_CONFIG_DIR -ErrorAction SilentlyContinue }
}
