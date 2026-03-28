# Ticket Support System

An open-source support ticket application with a React frontend, a Django REST backend, and an optional local AI classification bridge powered by the vendored `freeloader` runtime.

## Highlights

- create, list, filter, search, and update support tickets
- view ticket statistics from the admin dashboard
- classify tickets into category and priority using a local OpenAI-compatible proxy
- run locally without Docker or with a Docker Compose stack
- keep AI classification non-blocking when the local browser-based AI layer is unavailable

## Tech Stack

- Frontend: React + esbuild
- Backend: Django + Django REST Framework
- Database: SQLite for local development, PostgreSQL in Docker
- AI bridge: local OpenAI-compatible proxy backed by vendored `freeloader`

## Repository Structure

```text
backend/      Django API and data model
frontend/     React application and static server
freeloader/   Vendored local browser-driven AI runtime
```

## Quick Start

### Local

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

Start the backend:

```powershell
.\.venv\Scripts\python backend\manage.py migrate
.\.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
```

Start the local AI proxy in another terminal:

```powershell
$env:FREELOADER_BROWSER_MODE="managed"
.\.venv\Scripts\python chatgpt_openai_proxy.py --host 127.0.0.1 --port 11435
```

Start the frontend in a third terminal:

```powershell
cd frontend
npm run serve
```

Open `http://127.0.0.1:3000`.

### Docker

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Run the local AI proxy on the host:

```powershell
$env:FREELOADER_BROWSER_MODE="managed"
.\.venv\Scripts\python chatgpt_openai_proxy.py --host 127.0.0.1 --port 11435
```

Then start the stack:

```powershell
docker compose up --build
```

## Documentation

- [Install Guide](INSTALL.md)
- [Usage Guide](USAGE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

## API Overview

Backend base URL: `http://127.0.0.1:8000/api`

- `GET /health/`
- `GET /tickets/`
- `POST /tickets/`
- `PATCH /tickets/{id}/`
- `GET /tickets/stats/`
- `POST /tickets/classify/`

AI proxy base URL: `http://127.0.0.1:11435/v1`

- `GET /models`
- `POST /chat/completions`
- `POST /responses`

## Open-Source Notes

- The repository includes a vendored copy of `freeloader` under `freeloader/`.
- Keep vendored notices and license files intact when redistributing the project.
- The local AI integration depends on a browser session and may require signing in to ChatGPT.

## Validation

Backend tests:

```powershell
.\.venv\Scripts\python backend\manage.py test tickets
```

Frontend build:

```powershell
cd frontend
npm run build
```

Proxy sanity:

```powershell
.\.venv\Scripts\python chatgpt_openai_proxy.py --version
.\.venv\Scripts\python -m freeloader --version
```

## License

This repository is released under the [MIT License](LICENSE).
