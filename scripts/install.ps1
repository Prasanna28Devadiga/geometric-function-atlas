$ErrorActionPreference = "Stop"

$ReleaseWheel = "https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/download/v0.2.1/geometric_function_atlas-0.2.1-py3-none-any.whl"
$PackageSpec = if ($env:GFA_PACKAGE_SPEC) { $env:GFA_PACKAGE_SPEC } else { $ReleaseWheel }
$PythonVersion = if ($env:GFA_PYTHON_VERSION) { $env:GFA_PYTHON_VERSION } else { "3.12" }
$UvInstallDir = if ($env:UV_INSTALL_DIR) { $env:UV_INSTALL_DIR } else { Join-Path $HOME ".local\bin" }

Write-Host "   ____  _____   _" -ForegroundColor Cyan
Write-Host "  / ___||  ___| / \" -ForegroundColor Cyan
Write-Host " | |  _ | |_   / _ \" -ForegroundColor Cyan
Write-Host " | |_| ||  _| / ___ \" -ForegroundColor Cyan
Write-Host "  \____||_|  /_/   \_\" -ForegroundColor Cyan
Write-Host "Geometric Function Atlas installer`n" -ForegroundColor DarkGray

function Write-Step([int]$Number, [string]$Message) {
    Write-Host "[$Number/4] " -NoNewline -ForegroundColor White
    Write-Host $Message
}

Write-Step 1 "Install uv"
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCommand) {
    $UvPath = $UvCommand.Source
    Write-Host "  ok uv is already installed" -ForegroundColor Green
} else {
    $Installer = Join-Path $env:TEMP "gfa-uv-$([guid]::NewGuid()).ps1"
    try {
        Invoke-WebRequest -UseBasicParsing "https://astral.sh/uv/install.ps1" -OutFile $Installer
        $env:UV_INSTALL_DIR = $UvInstallDir
        $env:UV_NO_MODIFY_PATH = "1"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Installer
        if ($LASTEXITCODE -ne 0) { throw "uv bootstrap failed with exit code $LASTEXITCODE" }
    } finally {
        Remove-Item $Installer -Force -ErrorAction SilentlyContinue
    }
    $UvPath = Join-Path $UvInstallDir "uv.exe"
}

if (-not (Test-Path $UvPath)) { throw "uv was installed but could not be found." }

Write-Step 2 "Install managed Python $PythonVersion"
& $UvPath python install $PythonVersion
if ($LASTEXITCODE -ne 0) { throw "Python installation failed with exit code $LASTEXITCODE" }

Write-Step 3 "Install GFA CLI"
& $UvPath tool install --managed-python --python $PythonVersion --force $PackageSpec
if ($LASTEXITCODE -ne 0) { throw "GFA installation failed with exit code $LASTEXITCODE" }
& $UvPath tool update-shell
if ($LASTEXITCODE -ne 0) { Write-Warning "PATH could not be updated automatically; open a new terminal after installation." }

Write-Step 4 "Verify"
$ToolBin = (& $UvPath tool dir --bin).Trim()
$GfaPath = Join-Path $ToolBin "gfa.exe"
if (-not (Test-Path $GfaPath)) { throw "gfa was installed but its executable was not found." }
& $GfaPath --version
if ($LASTEXITCODE -ne 0) { throw "Installed gfa command failed its version check" }

Write-Host "`nGFA is ready." -ForegroundColor Green
Write-Host "Try: gfa walkthrough"
Write-Host "Open a new terminal if gfa is not found in this one."
