# Contributing

Thanks for your interest in improving this project.

## Development Setup

Use the steps in [INSTALL.md](INSTALL.md) to set up Python, frontend dependencies, and the local AI runtime.

## Development Workflow

1. Create a branch for your work.
2. Keep changes scoped and focused.
3. Update documentation when behavior changes.
4. Add or update tests when backend behavior changes.
5. Run the relevant validation commands before opening a pull request.

## Validation Commands

Backend tests:

```powershell
.\.venv\Scripts\python backend\manage.py test tickets
```

Frontend build:

```powershell
cd frontend
npm run build
```

Proxy sanity checks:

```powershell
.\.venv\Scripts\python chatgpt_openai_proxy.py --version
.\.venv\Scripts\python -m freeloader --version
```

## Project Conventions

- Do not commit secrets, local `.env` files, or browser profiles.
- Keep the vendored `freeloader` folder self-contained.
- Preserve third-party license files when updating vendored code.
- Prefer small pull requests with a clear purpose.

## Pull Requests

Please include:

- a short summary of the change
- the motivation for the change
- any manual or automated validation you ran
- screenshots for UI changes, when relevant
