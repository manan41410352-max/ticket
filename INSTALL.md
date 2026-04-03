# Install Guide

This document covers the supported ways to install and run the project.

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Docker Desktop, if you want the containerized workflow
- A ChatGPT-capable browser session for the local AI integration

## Short Commands

The simplest local workflow from the repository root is:

```powershell
.\run.cmd
```

On the first run, `run.cmd` will set up missing local dependencies, apply migrations, build the frontend, and open the app in your default browser. If Brave is installed, the local AI worker prefers Brave over Edge.

To keep the local AI browser worker in the background, use:

```powershell
.\run.cmd -HeadlessAI
```

If you prefer to keep install and run separate, use:

```powershell
.\setup.cmd
.\run.cmd
```

## Local Development Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m pip install -r freeloader\requirements.txt
.\.venv\Scripts\python -m playwright install chromium
cd frontend
npm install --no-package-lock
npm run build
cd ..
```

## Local Runtime

The helper command above is the recommended path:

```powershell
.\run.cmd
```

To keep the AI helper browser in the background:

```powershell
.\run.cmd -HeadlessAI
```

If you want to start each process manually, use the commands below.

Start the backend:

```powershell
.\.venv\Scripts\python backend\manage.py migrate
.\.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
```

Start the Freeloader service in a second terminal:

```powershell
$env:FREELOADER_BROWSER_MODE="auto"
.\.venv\Scripts\python -m freeloader serve --host 127.0.0.1 --port 11435
```

Start the frontend in a third terminal:

```powershell
cd frontend
npm run serve
```

The UI will be available at `http://127.0.0.1:3000`.

## Docker Setup

Copy the root environment template:

```powershell
Copy-Item .env.example .env
```

Start the Freeloader service on the host:

```powershell
$env:FREELOADER_BROWSER_MODE="auto"
.\.venv\Scripts\python -m freeloader serve --host 127.0.0.1 --port 11435
```

Then start the app stack:

```powershell
docker compose up --build
```

## Verification

Backend health:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health/ | Select-Object -ExpandProperty Content
```

Freeloader health:

```powershell
Invoke-WebRequest http://127.0.0.1:11435/health | Select-Object -ExpandProperty Content
```
