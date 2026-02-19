import json
import os

from openai import OpenAI


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


def _build_client():
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def classify_ticket(description: str):
    try:
        client = _build_client()
        if client is None:
            return {
                'suggested_category': None,
                'suggested_priority': None,
            }

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': description},
            ],
            temperature=0,
        )

        content = (response.choices[0].message.content or '').strip()
        parsed = json.loads(content)

        return {
            'suggested_category': parsed.get('category'),
            'suggested_priority': parsed.get('priority'),
        }
    except Exception:
        return {
            'suggested_category': None,
            'suggested_priority': None,
        }
