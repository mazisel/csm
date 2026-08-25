# Windows PowerShell Installer for csm
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Installing csm for Windows (Codex)   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/ or Windows Store." -ForegroundColor Yellow
    exit 1
}

$InstallDir = "$HOME\.local\bin"
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$BaseUrl = "https://raw.githubusercontent.com/mazisel/csm/main"

Write-Host "⬇️  Downloading csm files from GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "$BaseUrl/csm.py" -OutFile "$InstallDir\csm.py"
Invoke-WebRequest -Uri "$BaseUrl/csm.cmd" -OutFile "$InstallDir\csm.cmd"
Invoke-WebRequest -Uri "$BaseUrl/csm.ps1" -OutFile "$InstallDir\csm.ps1"

# Check and update PATH in user environment
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = if ($UserPath.EndsWith(";")) { "$UserPath$InstallDir" } else { "$UserPath;$InstallDir" }
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "ℹ️  Added $InstallDir to your User PATH." -ForegroundColor Yellow
}

# Update current session PATH as well
if ($env:Path -notlike "*$InstallDir*") {
    $env:Path = "$InstallDir;$env:Path"
}

Write-Host ""
Write-Host "✅ csm successfully installed to $InstallDir!" -ForegroundColor Green
Write-Host ""
Write-Host "Try it out by running:" -ForegroundColor Cyan
Write-Host "   csm help" -ForegroundColor White
Write-Host "   csm add <account-name>" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
