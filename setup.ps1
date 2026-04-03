[CmdletBinding()]
param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-SystemPython {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @('py', '-3')
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return @('python')
    }

    throw 'Python 3.11 or newer is required but was not found on PATH.'
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $repoRoot 'frontend'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'npm is required but was not found on PATH.'
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $venvPython)) {
        $systemPython = Get-SystemPython
        Write-Step 'Creating virtual environment'
        if ($systemPython.Length -gt 1) {
            & $systemPython[0] $systemPython[1] -m venv .venv
        }
        else {
            & $systemPython[0] -m venv .venv
        }
    }

    Write-Step 'Upgrading pip'
    & $venvPython -m pip install --upgrade pip

    Write-Step 'Installing backend dependencies'
    & $venvPython -m pip install -r backend\requirements.txt

    Write-Step 'Installing Freeloader dependencies'
    & $venvPython -m pip install -r freeloader\requirements.txt

    Write-Step 'Installing Playwright Chromium'
    & $venvPython -m playwright install chromium

    Push-Location $frontendDir
    try {
        Write-Step 'Installing frontend dependencies'
        & npm install --no-package-lock

        if (-not $SkipFrontendBuild) {
            Write-Step 'Building frontend'
            & npm run build
        }
    }
    finally {
        Pop-Location
    }

    Write-Host ''
    Write-Host 'Setup complete.' -ForegroundColor Green
    Write-Host 'Run .\run.cmd to start the app.' -ForegroundColor Green
}
finally {
    Pop-Location
}
