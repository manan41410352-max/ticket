"""Compatibility wrapper around the vendored Freeloader API server.

Run it locally:
    python chatgpt_openai_proxy.py --host 127.0.0.1 --port 11435

Then point compatible apps to:
    base_url = http://127.0.0.1:11435/v1
    api_key = anything
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _alias_env(source_name: str, target_name: str) -> None:
    source_value = os.environ.get(source_name, "").strip()
    if source_value and not os.environ.get(target_name):
        os.environ[target_name] = source_value


def _configure_compatibility_environment() -> None:
    alias_pairs = {
        "OPENAI_PROXY_HOST": "FREELOADER_HOST",
        "OPENAI_PROXY_PORT": "FREELOADER_PORT",
        "OPENAI_PROXY_MODEL": "FREELOADER_MODEL",
        "OPENAI_PROXY_TIMEOUT": "FREELOADER_TIMEOUT",
        "SCRAPER_TIMEOUT": "FREELOADER_TIMEOUT",
    }
    for legacy_name, canonical_name in alias_pairs.items():
        _alias_env(legacy_name, canonical_name)

    os.environ.setdefault("FREELOADER_MODEL", "freeloader")


_configure_compatibility_environment()

from freeloader import __version__
from freeloader.freeloader_runtime import DEFAULT_HOST, DEFAULT_PORT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a local OpenAI-compatible proxy backed by the vendored Freeloader browser integration."
        )
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to.")
    return parser.parse_args()


def main() -> int:
    from freeloader.freeloader_api import run_server

    args = parse_args()
    os.environ["FREELOADER_HOST"] = args.host
    os.environ["FREELOADER_PORT"] = str(args.port)
    return run_server(args.host, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
