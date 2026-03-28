"""Freeloader entrypoint.

Install once:
    python -m pip install -r requirements.txt
    python -m playwright install chromium

Run interactive terminal chat:
    python -m freeloader

Ask once:
    python -m freeloader ask "Explain sockets in one paragraph"

Run the local API:
    python -m freeloader serve --host 127.0.0.1 --port 11435
"""

from __future__ import annotations

import argparse
import sys

try:
    from .freeloader_api import ask, create_chat_completion, create_response, run_server
    from .freeloader_runtime import (
        APP_VERSION,
        DEFAULT_HOST,
        DEFAULT_PORT,
        DEFAULT_TIMEOUT,
        FreeloaderError,
        configure_stdio,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from freeloader_api import ask, create_chat_completion, create_response, run_server
    from freeloader_runtime import (
        APP_VERSION,
        DEFAULT_HOST,
        DEFAULT_PORT,
        DEFAULT_TIMEOUT,
        FreeloaderError,
        configure_stdio,
    )

__all__ = ["ask", "create_chat_completion", "create_response", "run_server"]


def parse_args() -> argparse.Namespace:
    raw_argv = list(sys.argv[1:])
    modes = {"chat", "ask", "serve"}
    if raw_argv and raw_argv[0] not in modes and not raw_argv[0].startswith("-"):
        raw_argv.insert(0, "ask")

    parser = argparse.ArgumentParser(
        prog="freeloader",
        description="Use Freeloader from the terminal or expose it as a local Freeloader API."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=sorted(modes),
        default="chat",
        help="`chat` opens an interactive terminal chat, `ask` sends one prompt, and `serve` starts the Freeloader API.",
    )
    parser.add_argument("prompt", nargs="*", help="Prompt text for `ask` mode.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to in `serve` mode.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to in `serve` mode.")
    parser.add_argument("--system", default="", help="Optional system prompt for `chat` or `ask` mode.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Browser timeout in seconds for `chat` or `ask` mode.",
    )
    return parser.parse_args(raw_argv)


def print_chat_help() -> None:
    print("Commands:", flush=True)
    print("  /help   Show available commands.", flush=True)
    print("  /clear  Reset the terminal session.", flush=True)
    print("  /exit   Quit Freeloader.", flush=True)


def run_terminal_chat(system_prompt: str = "", timeout: int = DEFAULT_TIMEOUT) -> int:
    print("Freeloader terminal chat is ready.", flush=True)
    print("Each terminal question is sent independently.", flush=True)
    print("Type /help for commands, /clear to reset, /exit to quit.", flush=True)

    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nClosing Freeloader.", flush=True)
            return 0

        if not user_text:
            continue

        command = user_text.lower()
        if command in {"/exit", "/quit"}:
            print("Closing Freeloader.", flush=True)
            return 0
        if command == "/help":
            print_chat_help()
            continue
        if command == "/clear":
            print("Terminal session reset.", flush=True)
            continue

        try:
            answer = ask(user_text, system=system_prompt, timeout=timeout)
        except FreeloaderError as exc:
            print(f"Error: {exc}", file=sys.stderr, flush=True)
            continue

        print(f"\nAssistant:\n{answer}", flush=True)


def main() -> int:
    configure_stdio()
    args = parse_args()

    if args.mode == "serve":
        return run_server(args.host, args.port)

    if args.mode == "ask":
        prompt = " ".join(args.prompt).strip()
        if not prompt:
            print("Prompt cannot be empty in `ask` mode.", file=sys.stderr, flush=True)
            return 1
        try:
            print(ask(prompt, system=args.system, timeout=args.timeout), flush=True)
        except FreeloaderError as exc:
            print(f"Error: {exc}", file=sys.stderr, flush=True)
            return 1
        return 0

    if args.prompt:
        print("Prompt text is only used in `ask` mode.", file=sys.stderr, flush=True)
        return 1

    try:
        return run_terminal_chat(system_prompt=args.system, timeout=args.timeout)
    except FreeloaderError as exc:
        print(f"Error: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
