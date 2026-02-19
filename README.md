# Ticket Support System

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
OPENAI_API_KEY=sk-your-real-key-here
```

`.env` is git-ignored and should never be committed.

`docker-compose.yml` injects this into backend with:

```yaml
env_file:
  - ./.env
environment:
  OPENAI_API_KEY: ${OPENAI_API_KEY:-}
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
- `OpenAI` for classification:
  LLM-based classification gives flexible category/priority suggestions from free-form ticket text.
- Postgres healthchecks:
  `pg_isready` gates backend startup on database readiness instead of container start order.
- Backend entrypoint wait/retry:
  bounded retries prevent race-condition crashes on cold starts and improve Linux Docker reliability.
- DB-level stats aggregation:
  stats endpoint uses ORM aggregations (`Count`, `Avg`, `TruncDate`) for efficient summary queries.
- Classification fallback:
  when `OPENAI_API_KEY` is missing or the provider fails, API returns null suggestions so ticket creation remains non-blocking.
