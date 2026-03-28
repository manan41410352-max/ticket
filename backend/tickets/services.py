import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {'billing', 'technical', 'account', 'general'}
VALID_PRIORITIES = {'low', 'medium', 'high', 'critical'}

SYSTEM_PROMPT = """
You are a support ticket classifier.

You must return ONLY valid JSON in this format:
{
  "category": "billing | technical | account | general",
  "priority": "low | medium | high | critical"
}

Rules:
- No explanations.
- No markdown.
- No extra text.
- Only JSON.
"""


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


def _ollama_base_url():
    return os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')


def _ollama_model():
    return os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')


def classify_ticket(description: str):
    try:
        payload = {
            'model': _ollama_model(),
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': description},
            ],
            'stream': False,
            'format': 'json',
            'options': {'temperature': 0},
        }
        request = Request(
            url=f'{_ollama_base_url()}/api/chat',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        with urlopen(request, timeout=60) as response:
            raw_response = json.loads(response.read().decode('utf-8'))

        content = (raw_response.get('message') or {}).get('content', '').strip()
        parsed = json.loads(content)

        return {
            'suggested_category': _normalize_choice(
                parsed.get('category'),
                VALID_CATEGORIES,
            ),
            'suggested_priority': _normalize_choice(
                parsed.get('priority'),
                VALID_PRIORITIES,
            ),
        }
    except (
        HTTPError,
        URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        logger.warning('Ollama classification failed: %s', exc)
        return _null_suggestions()
