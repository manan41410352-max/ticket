from __future__ import annotations

import json
import secrets
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    from .freeloader_runtime import (
        APP_VERSION,
        DEFAULT_HOST,
        DEFAULT_MODEL,
        DEFAULT_PORT,
        DEFAULT_TIMEOUT,
        FreeloaderError,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from freeloader_runtime import (
        APP_VERSION,
        DEFAULT_HOST,
        DEFAULT_MODEL,
        DEFAULT_PORT,
        DEFAULT_TIMEOUT,
        FreeloaderError,
    )


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


@lru_cache(maxsize=1)
def resolve_assistant_runner():
    try:
        from .freeloader_browser import run_assistant_prompt
    except ImportError:  # pragma: no cover - supports direct script execution
        from freeloader_browser import run_assistant_prompt
    return run_assistant_prompt


def resolve_timeout(raw_timeout, default: int = DEFAULT_TIMEOUT) -> int:
    try:
        value = int(raw_timeout)
    except (TypeError, ValueError):
        return default
    return max(1, value)


def extract_text_from_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"].strip()
        if isinstance(content.get("content"), str):
            return content["content"].strip()
        return ""
    if isinstance(content, list):
        parts = []
        for item in content:
            text = extract_text_from_content(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    return ""


def messages_to_prompt(messages: list[dict]) -> str:
    compact_messages = []

    for message in messages:
        role = (message.get("role") or "user").strip().upper()
        text = extract_text_from_content(message.get("content"))
        if not text:
            continue
        compact_messages.append((role, text))

    if not compact_messages:
        raise FreeloaderError("At least one message with text content is required.")

    if len(compact_messages) == 1 and compact_messages[0][0] == "USER":
        return compact_messages[0][1]

    if len(compact_messages) == 2 and compact_messages[0][0] == "SYSTEM" and compact_messages[1][0] == "USER":
        system_text = compact_messages[0][1]
        user_text = compact_messages[1][1]
        return f"Follow these instructions:\n{system_text}\n\nUser request:\n{user_text}"

    sections = ["Reply as the assistant to the latest message."]
    for role, text in compact_messages:
        sections.append(f"{role}:\n{text}")
    return "\n\n".join(sections)


def messages_from_responses_input(body: dict) -> list[dict]:
    messages = []
    instructions = (body.get("instructions") or "").strip()
    if instructions:
        messages.append({"role": "system", "content": instructions})

    input_value = body.get("input")
    if isinstance(input_value, str):
        messages.append({"role": "user", "content": input_value})
        return messages

    if isinstance(input_value, list):
        for item in input_value:
            if isinstance(item, str):
                messages.append({"role": "user", "content": item})
                continue

            if not isinstance(item, dict):
                continue

            if item.get("type") == "message" or "role" in item or "content" in item:
                messages.append(
                    {
                        "role": item.get("role") or "user",
                        "content": item.get("content"),
                    }
                )
                continue

            messages.append({"role": "user", "content": [item]})

    return messages


def answer_messages(messages: list[dict], timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    prompt = messages_to_prompt(messages)
    answer = resolve_assistant_runner()(prompt, timeout=resolve_timeout(timeout))
    return prompt, answer


def standalone_user_prompt(user_text: str) -> str:
    cleaned = (user_text or "").strip()
    if not cleaned:
        raise FreeloaderError("Prompt cannot be empty.")

    return f"Only answer this latest request and ignore older tab context:\n{cleaned}"


def approx_token_count(text: str) -> int:
    text = (text or "").strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


def completion_payload(model: str, prompt: str, answer: str) -> dict:
    created = int(time.time())
    completion_id = f"chatcmpl-{secrets.token_hex(12)}"
    prompt_tokens = approx_token_count(prompt)
    completion_tokens = approx_token_count(answer)
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def responses_payload(model: str, prompt: str, answer: str) -> dict:
    created = int(time.time())
    response_id = f"resp_{secrets.token_hex(12)}"
    output_id = f"msg_{secrets.token_hex(10)}"
    prompt_tokens = approx_token_count(prompt)
    completion_tokens = approx_token_count(answer)
    return {
        "id": response_id,
        "object": "response",
        "created_at": created,
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": output_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": answer,
                        "annotations": [],
                    }
                ],
            }
        ],
        "output_text": answer,
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def ask(
    prompt: str,
    *,
    history: list[dict] | None = None,
    system: str = "",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    messages = []
    cleaned_system = system.strip()
    cleaned_prompt = (prompt or "").strip()
    if not cleaned_prompt:
        raise FreeloaderError("Prompt cannot be empty.")

    if not history and not cleaned_system:
        return run_assistant_prompt(standalone_user_prompt(cleaned_prompt), timeout=timeout)

    if cleaned_system:
        messages.append({"role": "system", "content": cleaned_system})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": cleaned_prompt})
    _, answer = answer_messages(messages, timeout=timeout)
    return answer


def create_chat_completion(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    prompt, answer = answer_messages(messages, timeout=timeout)
    return completion_payload(model, prompt, answer)


def create_response(
    input_value,
    *,
    instructions: str = "",
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    body = {"instructions": instructions, "input": input_value}
    messages = messages_from_responses_input(body)
    prompt, answer = answer_messages(messages, timeout=timeout)
    return responses_payload(model, prompt, answer)


class FreeloaderHandler(BaseHTTPRequestHandler):
    server_version = f"Freeloader/{APP_VERSION}"

    @staticmethod
    def _normalized_path(raw_path: str) -> str:
        return urlparse(raw_path).path.rstrip("/") or "/"

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(
        self,
        status_code: int,
        message: str,
        error_type: str = "invalid_request_error",
    ) -> None:
        self._send_json(
            status_code,
            {
                "error": {
                    "message": message,
                    "type": error_type,
                    "param": None,
                    "code": None,
                }
            },
        )

    def _send_sse(self, payload: dict | str) -> None:
        if isinstance(payload, str):
            chunk = f"data: {payload}\n\n".encode("utf-8")
        else:
            chunk = f"data: {json.dumps(payload)}\n\n".encode("utf-8")
        self.wfile.write(chunk)
        self.wfile.flush()

    def _read_json_body(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise FreeloaderError("Invalid Content-Length header.") from exc

        try:
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            return json.loads(raw_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FreeloaderError("Request body must be valid JSON.") from exc

    def _write_streaming_completion(self, model: str, answer: str) -> None:
        created = int(time.time())
        completion_id = f"chatcmpl-{secrets.token_hex(12)}"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

        self._send_sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }
                ],
            }
        )
        if answer:
            self._send_sse(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": answer},
                            "finish_reason": None,
                        }
                    ],
                }
            )
        self._send_sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
        )
        self._send_sse("[DONE]")

    def _handle_chat_completions(self) -> None:
        body = self._read_json_body()
        messages = body.get("messages")
        if not isinstance(messages, list):
            raise FreeloaderError("`messages` must be a list for /v1/chat/completions.")

        model = (body.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
        prompt, answer = answer_messages(messages, timeout=body.get("timeout", DEFAULT_TIMEOUT))

        if body.get("stream"):
            self._write_streaming_completion(model, answer)
            return

        self._send_json(200, completion_payload(model, prompt, answer))

    def _handle_responses(self) -> None:
        body = self._read_json_body()
        messages = messages_from_responses_input(body)
        model = (body.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
        prompt, answer = answer_messages(messages, timeout=body.get("timeout", DEFAULT_TIMEOUT))
        self._send_json(200, responses_payload(model, prompt, answer))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        path = self._normalized_path(self.path)
        if path in {"/", "/health", "/v1", "/v1/health"}:
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "freeloader",
                    "version": APP_VERSION,
                    "base_url": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}/v1",
                    "model": DEFAULT_MODEL,
                },
            )
            return

        if path == "/v1/models":
            now = int(time.time())
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": DEFAULT_MODEL,
                            "object": "model",
                            "created": now,
                            "owned_by": "freeloader",
                        }
                    ],
                },
            )
            return

        self._send_error(404, "Not found.", error_type="not_found_error")

    def do_POST(self) -> None:
        path = self._normalized_path(self.path)
        try:
            if path in {"/v1/chat/completions", "/chat/completions"}:
                self._handle_chat_completions()
                return
            if path in {"/v1/responses", "/responses"}:
                self._handle_responses()
                return
            self._send_error(404, "Not found.", error_type="not_found_error")
        except FreeloaderError as exc:
            self._send_error(400, str(exc))
        except BrokenPipeError:
            return
        except Exception as exc:  # pragma: no cover - final safety net
            self._send_error(500, f"Internal Freeloader error: {exc}", error_type="server_error")

    def log_message(self, format, *args) -> None:
        return


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    server = ReusableThreadingHTTPServer((host, port), FreeloaderHandler)
    print(f"Freeloader API listening on http://{host}:{port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Freeloader API.", flush=True)
    finally:
        server.server_close()
    return 0
