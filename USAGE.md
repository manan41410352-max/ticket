# Usage Guide

## What The Project Does

This project provides:

- a React user interface for creating support tickets
- a Django REST API for ticket CRUD, analytics, and AI classification
- an optional local AI classification bridge backed by the vendored `freeloader` runtime

## Standard Local Workflow

1. Start the Django backend on `127.0.0.1:8000`.
2. Start the Freeloader-backed OpenAI-compatible proxy on `127.0.0.1:11435`.
3. Start the frontend server on `127.0.0.1:3000`.
4. Open `http://127.0.0.1:3000`.
5. Create a ticket from the user page or manage tickets from the admin page.

## AI Classification Modes

### Managed browser mode

This is the easiest first-run mode:

```powershell
$env:FREELOADER_BROWSER_MODE="managed"
.\.venv\Scripts\python chatgpt_openai_proxy.py --host 127.0.0.1 --port 11435
```

On first use, a browser window may open and ask you to sign in to ChatGPT.

### CDP mode

If you already run Chrome, Edge, or Brave with remote debugging:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
$env:FREELOADER_BROWSER_MODE="cdp"
.\.venv\Scripts\python chatgpt_openai_proxy.py --host 127.0.0.1 --port 11435
```

## API Endpoints

Base backend URL: `http://127.0.0.1:8000/api`

- `GET /health/`
- `GET /tickets/`
- `POST /tickets/`
- `PATCH /tickets/{id}/`
- `GET /tickets/stats/`
- `POST /tickets/classify/`

Base local AI URL: `http://127.0.0.1:11435/v1`

- `GET /models`
- `POST /chat/completions`
- `POST /responses`

## Troubleshooting

### "AI suggestion unavailable"

Check these first:

```powershell
Invoke-WebRequest http://127.0.0.1:11435/health | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:8000/api/health/ | Select-Object -ExpandProperty Content
```

Common causes:

- the proxy is not running
- Playwright is not installed in the local virtual environment
- Chromium has not been installed for Playwright
- the browser session is not signed in to ChatGPT
- the local AI call failed and the backend returned null suggestions by design
