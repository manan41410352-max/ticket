[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoBrowser,
    [switch]$HeadlessAI
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Quote-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-PreferredBrowserPath {
    $candidates = @(
        "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe",
        'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
        'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe',
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe",
        'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    return $null
}

function Test-PortListening {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $titleLiteral = Quote-PowerShellLiteral $Title
    $workingDirectoryLiteral = Quote-PowerShellLiteral $WorkingDirectory
    $wrappedCommand = "`$host.UI.RawUI.WindowTitle = $titleLiteral; Set-Location $workingDirectoryLiteral; $Command"

    if ($DryRun) {
        Write-Host "[dry-run] powershell -NoExit -ExecutionPolicy Bypass -Command $wrappedCommand"
        return
    }

    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
        $wrappedCommand
    ) | Out-Null
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$setupScript = Join-Path $repoRoot 'setup.ps1'
$frontendDir = Join-Path $repoRoot 'frontend'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$frontendBuild = Join-Path $frontendDir 'build\index.html'
$frontendNodeModules = Join-Path $frontendDir 'node_modules'
$backendManage = Join-Path $repoRoot 'backend\manage.py'
$preferredBrowserPath = Get-PreferredBrowserPath
$pythonLiteral = Quote-PowerShellLiteral $venvPython
$backendManageLiteral = Quote-PowerShellLiteral $backendManage
$preferredBrowserLiteral = if ($preferredBrowserPath) { Quote-PowerShellLiteral $preferredBrowserPath } else { $null }

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'npm is required but was not found on PATH.'
}

Push-Location $repoRoot
try {
    if ($preferredBrowserPath) {
        Write-Step "Using AI browser engine: $preferredBrowserPath"
    }
    else {
        Write-Host 'No Brave/Chrome/Edge executable was detected explicitly for the AI worker, so it will fall back to the system default browser.' -ForegroundColor Yellow
    }

    $needsSetup = -not (Test-Path $venvPython) -or -not (Test-Path $frontendNodeModules)
    if ($needsSetup) {
        Write-Step 'Initial setup is missing, running setup.ps1'
        if ($DryRun) {
            Write-Host "[dry-run] powershell -ExecutionPolicy Bypass -File $(Quote-PowerShellLiteral $setupScript) -SkipFrontendBuild"
        }
        else {
            & $setupScript -SkipFrontendBuild
        }
    }

    Write-Step 'Applying database migrations'
    if ($DryRun) {
        Write-Host "[dry-run] & $pythonLiteral $backendManageLiteral migrate"
    }
    else {
        & $venvPython $backendManage migrate
    }

    Write-Step 'Building frontend'
    Push-Location $frontendDir
    try {
        if ($DryRun) {
            Write-Host '[dry-run] npm run build'
        }
        else {
            & npm run build
        }
    }
    finally {
        Pop-Location
    }

    if (-not $DryRun -and -not (Test-Path $frontendBuild)) {
        throw 'Frontend build did not produce frontend\build\index.html.'
    }

    if (Test-PortListening 11435) {
        Write-Host 'Port 11435 is already in use, skipping Freeloader launch.' -ForegroundColor Yellow
    }
    else {
        Write-Step 'Starting Freeloader service'
        $freeloaderCommandParts = @(
            '$env:FREELOADER_BROWSER_MODE = ''auto'''
            '$env:FREELOADER_HEADLESS = ''0'''
        )
        if ($HeadlessAI) {
            $freeloaderCommandParts[1] = '$env:FREELOADER_HEADLESS = ''1'''
        }
        if ($preferredBrowserLiteral) {
            $freeloaderCommandParts += '$env:FREELOADER_BROWSER_PATH = ' + $preferredBrowserLiteral
        }
        $freeloaderCommandParts += "& $pythonLiteral -m freeloader serve --host 127.0.0.1 --port 11435"
        $freeloaderCommand = $freeloaderCommandParts -join '; '
        Start-ServiceWindow -Title 'ticket-freeloader' -WorkingDirectory $repoRoot -Command $freeloaderCommand
    }

    if (Test-PortListening 8000) {
        Write-Host 'Port 8000 is already in use, skipping backend launch.' -ForegroundColor Yellow
    }
    else {
        Write-Step 'Starting backend'
        $backendCommand = @(
            '$env:FREELOADER_API_BASE_URL = ''http://127.0.0.1:11435/v1'''
            '$env:FREELOADER_API_MODEL = ''freeloader'''
            "& $pythonLiteral $backendManageLiteral runserver 127.0.0.1:8000"
        ) -join '; '
        Start-ServiceWindow -Title 'ticket-backend' -WorkingDirectory $repoRoot -Command $backendCommand
    }

    if (Test-PortListening 3000) {
        Write-Host 'Port 3000 is already in use, skipping frontend launch.' -ForegroundColor Yellow
    }
    else {
        Write-Step 'Starting frontend'
        Start-ServiceWindow -Title 'ticket-frontend' -WorkingDirectory $frontendDir -Command '& npm run serve'
    }

    Write-Host ''
    Write-Host 'App URLs:' -ForegroundColor Green
    Write-Host '  Frontend: http://127.0.0.1:3000'
    Write-Host '  Backend:  http://127.0.0.1:8000/api/health/'
    Write-Host '  Freeloader: http://127.0.0.1:11435/health'
    Write-Host '  App UI:   opens in your default browser'
    if ($HeadlessAI) {
        Write-Host '  AI mode:  background browser enabled'
    }

    if (-not $NoBrowser -and -not $DryRun) {
        Start-Process 'http://127.0.0.1:3000' | Out-Null
    }
}
finally {
    Pop-Location
}
