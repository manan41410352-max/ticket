import json
import logging
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {'billing', 'technical', 'account', 'general'}
VALID_PRIORITIES = {'low', 'medium', 'high', 'critical'}
FREELOADER_MODULE_NAME = 'freeloader'
FREELOADER_PACKAGE_MARKER = '__main__.py'
CLASSIFICATION_TIMEOUT_SECONDS = 45


def _discover_project_root():
    current = Path(__file__).resolve().parent
    for candidate in (current, *current.parents):
        if (candidate / FREELOADER_MODULE_NAME / FREELOADER_PACKAGE_MARKER).is_file():
            return candidate
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = _discover_project_root()
FREELOADER_DIR = Path(
    os.environ.get('FREELOADER_DIR', str(PROJECT_ROOT / FREELOADER_MODULE_NAME))
).expanduser()


@lru_cache(maxsize=1)
def _resolve_freeloader_python():
    configured = (
        os.environ.get('FREELOADER_PYTHON', '').strip()
        or os.environ.get('SCRAPER_PYTHON', '').strip()
    )
    if configured:
        return configured

    candidates = [
        PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe',
        PROJECT_ROOT / '.venv' / 'bin' / 'python',
        FREELOADER_DIR.parent / '.venv' / 'Scripts' / 'python.exe',
        FREELOADER_DIR.parent / '.venv' / 'bin' / 'python',
        FREELOADER_DIR / '.venv' / 'Scripts' / 'python.exe',
        FREELOADER_DIR / '.venv' / 'bin' / 'python',
        sys.executable,
    ]

    for candidate in candidates:
        if Path(candidate).is_file():
            return str(candidate)

    return sys.executable


@lru_cache(maxsize=1)
def _resolve_freeloader_command_prefix():
    package_marker = FREELOADER_DIR / FREELOADER_PACKAGE_MARKER
    if not package_marker.is_file():
        raise FileNotFoundError(f'Freeloader package marker not found at {package_marker}')
    return [_resolve_freeloader_python(), '-m', FREELOADER_MODULE_NAME]


def _null_suggestions():
    return {
        'suggested_category': None,
        'suggested_priority': None,
    }


def _normalize_choice(value: str | None, allowed_values: set[str]):
    if not value:
        return None

    normalized = value.strip().lower()
    if normalized in allowed_values:
        return normalized
    return None


def _build_classification_prompt(title: str, description: str):
    return (
        "Classify this support ticket. Return ONLY valid JSON, nothing else.\n"
        "{\n"
        '  "category": "billing" | "technical" | "account" | "general",\n'
        '  "priority": "low" | "medium" | "high" | "critical"\n'
        "}\n\n"
        f"Title: {title}\n"
        f"Description: {description}"
    )


def _normalize_payload(parsed: dict):
    return {
        'suggested_category': _normalize_choice(
            parsed.get('suggested_category') or parsed.get('category'),
            VALID_CATEGORIES,
        ),
        'suggested_priority': _normalize_choice(
            parsed.get('suggested_priority') or parsed.get('priority'),
            VALID_PRIORITIES,
        ),
    }


def _parse_first_json_object(raw_text: str):
    cleaned = (raw_text or '').strip()
    if not cleaned:
        raise json.JSONDecodeError('No JSON content', cleaned, 0)

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != '{':
            continue

        try:
            parsed, _end = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    raise json.JSONDecodeError('No JSON object found in text', cleaned, 0)


def _freeloader_api_base_url():
    return os.environ.get('FREELOADER_API_BASE_URL', '').strip()


def _freeloader_api_model():
    return os.environ.get('FREELOADER_API_MODEL', 'freeloader').strip()


def _classify_with_freeloader_api(title: str, description: str):
    prompt = _build_classification_prompt(title, description)
    request = Request(
        url=urljoin(f"{_freeloader_api_base_url().rstrip('/')}/", 'chat/completions'),
        data=json.dumps(
            {
                'model': _freeloader_api_model(),
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
                'stream': False,
            }
        ).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {os.environ.get('FREELOADER_API_KEY', 'dummy')}",
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    with urlopen(request, timeout=60) as response:
        parsed = json.loads(response.read().decode('utf-8'))

    message = (
        parsed.get('choices', [{}])[0]
        .get('message', {})
        .get('content', '')
    )
    return _normalize_payload(_parse_first_json_object(message))


def _classify_with_freeloader_subprocess(title: str, description: str):
    try:
        prompt = _build_classification_prompt(title.strip(), description.strip())
        command_prefix = _resolve_freeloader_command_prefix()
        env = os.environ.copy()
        env.setdefault('PYTHONIOENCODING', 'utf-8')
        env.setdefault('PYTHONUTF8', '1')

        result = subprocess.run(
            [
                *command_prefix,
                'ask',
                prompt,
                '--timeout',
                str(CLASSIFICATION_TIMEOUT_SECONDS),
            ],
            cwd=str(FREELOADER_DIR.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=CLASSIFICATION_TIMEOUT_SECONDS + 15,
            check=False,
        )

        if result.returncode != 0:
            logger.warning(
                'Freeloader classification failed with code %s: %s',
                result.returncode,
                (result.stderr or '').strip(),
            )
            return _null_suggestions()

        parsed = _parse_first_json_object(result.stdout or '')
        return _normalize_payload(parsed)
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        logger.warning('Freeloader classification failed: %s', exc)
        return _null_suggestions()


def classify_ticket(description: str, title: str = '', allow_freeloader_api: bool = True):
    description = description.strip()
    title = title.strip()

    if allow_freeloader_api and _freeloader_api_base_url():
        try:
            return _classify_with_freeloader_api(title, description)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
        ) as exc:
            logger.warning('Freeloader API classification failed: %s', exc)
            return _null_suggestions()

    return _classify_with_freeloader_subprocess(title, description)
