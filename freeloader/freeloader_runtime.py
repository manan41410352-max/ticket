from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("NODE_NO_WARNINGS", "1")


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)).strip())
    except (AttributeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)).strip())
    except (AttributeError, ValueError):
        return default

BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "Freeloader"
APP_VERSION = "1.0.0"
DEFAULT_HOST = os.environ.get("FREELOADER_HOST", "127.0.0.1")
DEFAULT_PORT = env_int("FREELOADER_PORT", 11435)
DEFAULT_MODEL = os.environ.get("FREELOADER_MODEL", "freeloader")
DEFAULT_TIMEOUT = env_int("FREELOADER_TIMEOUT", 120)


class FreeloaderError(RuntimeError):
    """Raised when Freeloader cannot complete a request."""


@dataclass(slots=True)
class FreeloaderConfig:
    assistant_url: str
    browser_mode: str
    browser_path: Path | None
    profile_dir: Path
    log_file: Path
    log_level: str
    headless: bool
    cdp_endpoint: str
    type_delay_ms: int
    response_timeout_seconds: int
    response_poll_interval: float
    response_settle_cycles: int


def parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_path(raw_value: str | None, fallback: Path) -> Path:
    if raw_value:
        candidate = Path(raw_value).expanduser()
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        return candidate.resolve()
    return fallback.resolve()


def configure_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except ValueError:
            continue


def guess_browser_path() -> Path | None:
    candidates = [
        Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path.home() / "AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe",
        Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
        Path.home() / "AppData/Local/Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_config() -> FreeloaderConfig:
    browser_mode = os.environ.get("FREELOADER_BROWSER_MODE", "auto").strip().lower()
    if browser_mode not in {"auto", "cdp", "managed"}:
        browser_mode = "auto"

    browser_path_raw = os.environ.get("FREELOADER_BROWSER_PATH", "").strip()
    browser_path = resolve_path(browser_path_raw, BASE_DIR) if browser_path_raw else guess_browser_path()

    return FreeloaderConfig(
        assistant_url=os.environ.get("FREELOADER_ASSISTANT_URL", "https://chatgpt.com/").strip(),
        browser_mode=browser_mode,
        browser_path=browser_path,
        profile_dir=resolve_path(
            os.environ.get("FREELOADER_PROFILE_DIR"),
            BASE_DIR / "freeloader_profile",
        ),
        log_file=resolve_path(
            os.environ.get("FREELOADER_LOG_FILE"),
            BASE_DIR / "freeloader.log",
        ),
        log_level=os.environ.get("FREELOADER_LOG_LEVEL", "INFO"),
        headless=parse_bool(os.environ.get("FREELOADER_HEADLESS"), default=False),
        cdp_endpoint=os.environ.get("FREELOADER_CDP_ENDPOINT", "http://127.0.0.1:9222").strip(),
        type_delay_ms=env_int("FREELOADER_TYPE_DELAY_MS", 0),
        response_timeout_seconds=max(
            1,
            env_int("FREELOADER_RESPONSE_TIMEOUT", DEFAULT_TIMEOUT),
        ),
        response_poll_interval=max(0.05, env_float("FREELOADER_POLL_INTERVAL", 0.25)),
        response_settle_cycles=max(1, env_int("FREELOADER_SETTLE_CYCLES", 1)),
    )


def setup_logger(config: FreeloaderConfig) -> logging.Logger:
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("freeloader")
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if parse_bool(os.environ.get("FREELOADER_VERBOSE"), default=False):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


@lru_cache(maxsize=1)
def get_runtime() -> tuple[FreeloaderConfig, logging.Logger]:
    config = load_config()
    logger = setup_logger(config)
    return config, logger
