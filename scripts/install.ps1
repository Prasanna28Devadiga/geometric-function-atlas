$ErrorActionPreference = "Stop"

$PackageSpec = if ($env:GFA_PACKAGE_SPEC) { $env:GFA_PACKAGE_SPEC } else { "geometric-function-atlas" }
$PythonVersion = if ($env:GFA_PYTHON_VERSION) { $env:GFA_PYTHON_VERSION } else { "3.12" }
$UvInstallDir = if ($env:UV_INSTALL_DIR) { $env:UV_INSTALL_DIR } else { Join-Path $HOME ".local\bin" }
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue

if ($UvCommand) {
    $UvPath = $UvCommand.Source
} else {
    $InstallerScript = (Invoke-WebRequest "https://astral.sh/uv/install.ps1").Content
    $env:UV_INSTALL_DIR = $UvInstallDir
    $env:UV_NO_MODIFY_PATH = "1"
    & ([scriptblock]::Create($InstallerScript))
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "uv installer failed with exit code $LASTEXITCODE"
    }
    $UvPath = Join-Path $UvInstallDir "uv.exe"
}

& $UvPath tool install --managed-python --python $PythonVersion --force $PackageSpec
if ($LASTEXITCODE -ne 0) { throw "Geometric Function Atlas installation failed with exit code $LASTEXITCODE" }
& $UvPath tool update-shell
if ($LASTEXITCODE -ne 0) { Write-Warning "Could not update PATH automatically; restart PowerShell after installation." }
$ToolBin = (& $UvPath tool dir --bin).Trim()
$GfaPath = Join-Path $ToolBin "gfa.exe"
& $GfaPath --version
if ($LASTEXITCODE -ne 0) { throw "Installed gfa command failed its version check" }
Write-Host "Installation complete. Restart PowerShell, then run: gfa --help"
