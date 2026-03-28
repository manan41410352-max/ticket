# Ticket Support System

## Local Runbook

This repo can run locally without Docker:

- Backend defaults to SQLite when `POSTGRES_*` environment variables are not set.
- Frontend can be served locally on port `3000` with a lightweight proxy that forwards `/api` to Django on port `8000`.

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd frontend
npm install --no-package-lock
npm run build
```

### Start locally

Backend:

```powershell
.\.venv\Scripts\python backend\manage.py migrate
.\.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
```

Frontend:

```powershell
cd frontend
npm run serve
```

Open `http://127.0.0.1:3000`.

AI classification uses your local Ollama server by default:

```powershell
ollama serve
```

The backend defaults to:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b
```

If Ollama is unavailable, ticket creation still works and the classifier returns null suggestions.

## Linux Docker Runbook

### Prerequisites
- Docker Engine is running.
- Your Linux user is in the `docker` group.

Check:

```bash
docker info
id
groups
```

If needed:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

### Environment Setup

Create a **root-level** `.env` file (same directory as `docker-compose.yml`):

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
```

`.env` is git-ignored and should never be committed.

`docker-compose.yml` injects this into backend with:

```yaml
env_file:
  - ./.env
environment:
  OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
  OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.1:8b}
```

After creating or updating `.env`, rebuild/restart containers:

```bash
docker compose down
docker compose up --build -d
```

### Start stack

```bash
docker compose up --build
```

Or detached:

```bash
docker compose up --build -d
```

### What changed for reliability
- Postgres now has a healthcheck (`pg_isready`).
- Backend now waits/retries for DB before migrations.
- Backend uses `restart: unless-stopped`.
- Backend depends on DB health (`service_healthy`) instead of start order only.

### Diagnostics

```bash
docker compose ps -a
docker compose logs --no-color backend db
docker compose config
```

### Smoke checks

```bash
curl -sS http://localhost:8000/api/health/ | jq .
curl -I http://localhost:3000/
```

## Design Decisions
- `Ollama` with `llama3.1:8b` for classification:
  local inference keeps ticket categorization on-device while still giving flexible category/priority suggestions from free-form text.
- Postgres healthchecks:
  `pg_isready` gates backend startup on database readiness instead of container start order.
- Backend entrypoint wait/retry:
  bounded retries prevent race-condition crashes on cold starts and improve Linux Docker reliability.
- DB-level stats aggregation:
  stats endpoint uses ORM aggregations (`Count`, `Avg`, `TruncDate`) for efficient summary queries.
- Classification fallback:
  when Ollama is unavailable or the model response is invalid, API returns null suggestions so ticket creation remains non-blocking.
