# Vendored Freeloader

This folder contains the slimmed-down Freeloader runtime that the ticket project
uses for local browser-driven AI calls.

Included here:

- the Python package code
- the runtime dependency list in `requirements.txt`
- the upstream `LICENSE`

Typical local setup from the repo root:

```powershell
.\.venv\Scripts\python -m pip install -r freeloader\requirements.txt
.\.venv\Scripts\python -m playwright install chromium
```

Typical local usage:

```powershell
.\.venv\Scripts\python -m freeloader serve --host 127.0.0.1 --port 11435
.\.venv\Scripts\python -m freeloader ask "Return valid JSON only."
```

Environment variables:

- `FREELOADER_BROWSER_MODE`
- `FREELOADER_CDP_ENDPOINT`
- `FREELOADER_ASSISTANT_URL`
- `FREELOADER_TIMEOUT`
- `FREELOADER_HOST`
- `FREELOADER_PORT`
- `FREELOADER_MODEL`
- `FREELOADER_PROFILE_DIR`
- `FREELOADER_BROWSER_PATH`
- `FREELOADER_LOG_FILE`
- `FREELOADER_HEADLESS`

The package is intended for local use and binds to `127.0.0.1` by default.
