from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Iterable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

try:
    from .freeloader_runtime import FreeloaderConfig, FreeloaderError, get_runtime
except ImportError:  # pragma: no cover - supports direct script execution
    from freeloader_runtime import FreeloaderConfig, FreeloaderError, get_runtime

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except Exception as exc:  # pragma: no cover - depends on local install
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None
    PLAYWRIGHT_IMPORT_ERROR = exc
else:
    PLAYWRIGHT_IMPORT_ERROR = None


CHAT_INPUT_SELECTORS = [
    "#prompt-textarea",
    "textarea[placeholder*='Message']",
    "textarea[placeholder*='Ask anything']",
    "textarea",
    "[contenteditable='true'][role='textbox']",
    "div.ProseMirror[contenteditable='true']",
]
SEND_BUTTON_SELECTORS = [
    "button[data-testid='send-button']",
    "button[aria-label*='Send']",
    "button:has-text('Send')",
]
STOP_BUTTON_SELECTORS = [
    "button[data-testid='stop-button']",
    "button[aria-label*='Stop']",
    "button:has-text('Stop generating')",
    "button:has-text('Stop')",
]
ASSISTANT_TURN_SELECTORS = [
    "[data-testid='conversation-turn'] [data-message-author-role='assistant']",
    "[data-testid*='conversation-turn'] [data-message-author-role='assistant']",
    "[data-message-author-role='assistant']",
]
CONVERSATION_TURN_SELECTOR = "[data-testid='conversation-turn'], [data-testid*='conversation-turn']"
BROWSER_LOCK = Lock()


@dataclass(slots=True)
class BrowserSession:
    playwright: Any
    context: Any
    page: Any
    owns_context: bool
    owns_page: bool


def require_playwright() -> None:
    if sync_playwright is not None:
        return
    raise FreeloaderError(
        "Freeloader needs the `playwright` package. "
        "Run `python -m pip install -r requirements.txt` and then "
        "`python -m playwright install chromium`."
    ) from PLAYWRIGHT_IMPORT_ERROR


def cdp_endpoint_is_ready(cdp_endpoint: str, timeout_seconds: float = 2.0) -> bool:
    version_url = f"{cdp_endpoint.rstrip('/')}/json/version"
    try:
        with urlopen(version_url, timeout=timeout_seconds) as response:
            return response.status == 200
    except URLError:
        return False


def assistant_host(assistant_url: str) -> str:
    return urlparse(assistant_url).netloc.lower()


def open_assistant_page(
    context,
    assistant_url: str,
    logger: logging.Logger,
    *,
    reuse_existing: bool,
) -> tuple[Any, bool]:
    host = assistant_host(assistant_url)

    if reuse_existing:
        for page in context.pages:
            current_url = (page.url or "").lower()
            if host and host in current_url:
                logger.info("Reusing existing assistant tab: %s", page.url)
                return page, False

    logger.info("Opening a fresh assistant tab.")
    page = context.new_page()
    page.goto(assistant_url, wait_until="domcontentloaded", timeout=60000)
    return page, True


def launch_cdp_browser(config: FreeloaderConfig, logger: logging.Logger) -> BrowserSession:
    require_playwright()
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.connect_over_cdp(config.cdp_endpoint, timeout=15000)
        if not browser.contexts:
            raise FreeloaderError("Freeloader connected to the browser, but no context was exposed.")

        context = browser.contexts[0]
        context.set_default_timeout(15000)
        page, owns_page = open_assistant_page(
            context,
            config.assistant_url,
            logger,
            reuse_existing=True,
        )
        return BrowserSession(
            playwright=playwright,
            context=context,
            page=page,
            owns_context=False,
            owns_page=owns_page,
        )
    except Exception:
        playwright.stop()
        raise


def launch_managed_browser(config: FreeloaderConfig, logger: logging.Logger) -> BrowserSession:
    require_playwright()
    config.profile_dir.mkdir(parents=True, exist_ok=True)
    playwright = sync_playwright().start()
    try:
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(config.profile_dir),
            "headless": config.headless,
        }
        if config.browser_path is not None:
            launch_kwargs["executable_path"] = str(config.browser_path)

        context = playwright.chromium.launch_persistent_context(**launch_kwargs)
        context.set_default_timeout(15000)
        page, owns_page = open_assistant_page(
            context,
            config.assistant_url,
            logger,
            reuse_existing=True,
        )
        return BrowserSession(
            playwright=playwright,
            context=context,
            page=page,
            owns_context=True,
            owns_page=owns_page,
        )
    except Exception as exc:
        playwright.stop()
        message = str(exc)
        if "Executable doesn't exist" in message or "browserType.launchPersistentContext" in message:
            raise FreeloaderError(
                "Freeloader could not start a local browser. "
                "Run `python -m playwright install chromium`."
            ) from exc
        raise


def launch_browser(config: FreeloaderConfig, logger: logging.Logger) -> BrowserSession:
    if config.browser_mode in {"auto", "cdp"} and config.cdp_endpoint:
        if cdp_endpoint_is_ready(config.cdp_endpoint):
            try:
                logger.info("Attaching to an existing browser over CDP.")
                return launch_cdp_browser(config, logger)
            except Exception as exc:
                if config.browser_mode == "cdp":
                    raise FreeloaderError(f"Freeloader could not attach over CDP: {exc}") from exc
                logger.warning("CDP attach failed, falling back to managed browser.", exc_info=True)
        elif config.browser_mode == "cdp":
            raise FreeloaderError(
                f"Freeloader could not find a browser at {config.cdp_endpoint}. "
                "Start one with remote debugging enabled or use managed mode."
            )

    logger.info("Launching a managed browser profile.")
    return launch_managed_browser(config, logger)


def close_browser(session: BrowserSession, logger: logging.Logger) -> None:
    try:
        if session.owns_page and not session.owns_context:
            try:
                session.page.close()
            except Exception:
                logger.warning("Freeloader could not close its temporary tab.", exc_info=True)
        if session.owns_context:
            try:
                session.context.close()
            except Exception:
                logger.warning("Freeloader could not close its managed browser context.", exc_info=True)
    finally:
        session.playwright.stop()


def first_visible_locator(page, selectors: Iterable[str], timeout_ms: int = 3000):
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except PlaywrightTimeoutError:
            continue
    return None


def wait_for_input(page, logger: logging.Logger, timeout_seconds: int = 60):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        input_locator = first_visible_locator(page, CHAT_INPUT_SELECTORS, timeout_ms=2000)
        if input_locator is not None:
            logger.info("Freeloader found the message box.")
            return input_locator

        logger.info("Waiting for the assistant page to become ready.")
        time.sleep(1.0)

    raise FreeloaderError(
        "Freeloader could not find the message box. "
        "If this is your first run, sign in in the opened browser window and try again."
    )


def _normalize_prompt_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u200b", "")
        .replace("\xa0", " ")
        .strip()
    )


def _canonicalize_prompt_text(value: str | None) -> str:
    return "".join(_normalize_prompt_text(value).split())


def _read_prompt_box_text(input_locator) -> str:
    readers = (
        lambda: input_locator.input_value(timeout=500),
        lambda: input_locator.text_content(timeout=500),
        lambda: input_locator.inner_text(timeout=500),
    )

    for reader in readers:
        try:
            value = reader()
        except Exception:
            continue

        normalized = _normalize_prompt_text(value)
        if normalized:
            return normalized

    return ""


def _prompt_box_contains_text(input_locator, prompt: str) -> bool:
    return _canonicalize_prompt_text(_read_prompt_box_text(input_locator)) == _canonicalize_prompt_text(prompt)


def _wait_for_prompt_box_text(input_locator, prompt: str, timeout_ms: int = 1500) -> bool:
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        if _prompt_box_contains_text(input_locator, prompt):
            return True
        time.sleep(0.05)

    return _prompt_box_contains_text(input_locator, prompt)


def clear_prompt_box(page, input_locator, logger: logging.Logger | None = None) -> None:
    input_locator.click()

    strategies = (
        ("fast fill clear", lambda: input_locator.fill("")),
        (
            "direct DOM clear",
            lambda: input_locator.evaluate(
                """
                (element) => {
                    const dispatch = () => {
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    };

                    element.focus();

                    if ('value' in element) {
                        element.value = '';
                        dispatch();
                        return true;
                    }

                    if (element.isContentEditable) {
                        element.textContent = '';
                        dispatch();
                        return true;
                    }

                    return false;
                }
                """
            ),
        ),
        (
            "keyboard clear",
            lambda: (
                page.keyboard.press("Control+A"),
                page.keyboard.press("Backspace"),
            ),
        ),
    )

    for strategy_name, strategy in strategies:
        try:
            strategy()
        except Exception:
            if logger is not None:
                logger.warning("Prompt clear strategy failed: %s", strategy_name, exc_info=True)
            continue

        if _wait_for_prompt_box_text(input_locator, "", timeout_ms=500):
            return

    if logger is not None:
        logger.warning(
            "Prompt box still contains text after clear attempts: %r",
            _read_prompt_box_text(input_locator),
        )


def _set_prompt_box_text_direct(input_locator, prompt: str) -> bool:
    try:
        return bool(
            input_locator.evaluate(
                """
                (element, text) => {
                    const dispatch = () => {
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    };

                    element.focus();

                    if ('value' in element) {
                        element.value = text;
                        dispatch();
                        return true;
                    }

                    if (element.isContentEditable) {
                        element.textContent = text;
                        dispatch();
                        return true;
                    }

                    return false;
                }
                """,
                prompt,
            )
        )
    except Exception:
        return False


def enter_prompt(page, input_locator, prompt: str, logger: logging.Logger, delay_ms: int) -> None:
    logger.info("Entering the prompt.")
    try:
        input_locator.fill(prompt)
        if _wait_for_prompt_box_text(input_locator, prompt):
            logger.info("Prompt inserted with fast fill.")
            return
    except Exception:
        logger.warning("Fast fill failed, trying alternate input methods.", exc_info=True)

    logger.info("Fast fill did not stick, trying direct DOM insertion.")
    if _set_prompt_box_text_direct(input_locator, prompt) and _wait_for_prompt_box_text(
        input_locator,
        prompt,
    ):
        logger.info("Prompt inserted with direct DOM set.")
        return

    logger.info("Falling back to keyboard typing.")
    clear_prompt_box(page, input_locator, logger)
    input_locator.click()
    try:
        page.keyboard.insert_text(prompt)
        if _wait_for_prompt_box_text(input_locator, prompt):
            logger.info("Prompt inserted with keyboard insert_text.")
            return
    except Exception:
        logger.warning("Keyboard insert_text failed, falling back to sequential typing.", exc_info=True)

    clear_prompt_box(page, input_locator, logger)
    input_locator.click()
    for character in prompt:
        if character == "\n":
            page.keyboard.press("Shift+Enter")
        else:
            page.keyboard.type(character, delay=delay_ms)

    if not _wait_for_prompt_box_text(input_locator, prompt):
        raise FreeloaderError("Freeloader could not populate the message box.")


def submit_prompt(page, logger: logging.Logger) -> None:
    send_button = first_visible_locator(page, SEND_BUTTON_SELECTORS, timeout_ms=1500)
    if send_button is not None:
        try:
            send_button.click()
            logger.info("Submitted with the send button.")
            return
        except Exception:
            logger.warning("Send button click failed, falling back to Enter.", exc_info=True)

    page.keyboard.press("Enter")
    logger.info("Submitted with Enter.")


def extract_locator_text(locator) -> str:
    try:
        return "\n".join(line.rstrip() for line in locator.inner_text(timeout=1000).splitlines()).strip()
    except PlaywrightTimeoutError:
        return ""


def assistant_turn_locator(page):
    fallback = page.locator(ASSISTANT_TURN_SELECTORS[0])
    for selector in ASSISTANT_TURN_SELECTORS:
        locator = page.locator(selector)
        if locator.count() > 0:
            return locator
    return fallback


def generation_in_progress(page) -> bool:
    for selector in STOP_BUTTON_SELECTORS:
        locator = page.locator(selector).first
        try:
            if locator.is_visible():
                return True
        except Exception:
            continue
    return False


def assistant_turn_count(page) -> int:
    return assistant_turn_locator(page).count()


def conversation_turn_count(page) -> int:
    return page.locator(CONVERSATION_TURN_SELECTOR).count()


def wait_for_new_assistant_turn(
    page,
    *,
    previous_turn_count: int,
    previous_assistant_count: int,
    timeout_seconds: int,
):
    page.wait_for_function(
        """
        ({ turnSelector, assistantSelectors, previousTurnCount, previousAssistantCount }) => {
            const turnCount = document.querySelectorAll(turnSelector).length;
            let assistantCount = 0;

            for (const selector of assistantSelectors) {
                const count = document.querySelectorAll(selector).length;
                if (count > 0) {
                    assistantCount = count;
                    break;
                }
            }

            return (
                turnCount > previousTurnCount ||
                assistantCount > previousAssistantCount
            );
        }
        """,
        arg={
            "turnSelector": CONVERSATION_TURN_SELECTOR,
            "assistantSelectors": ASSISTANT_TURN_SELECTORS,
            "previousTurnCount": previous_turn_count,
            "previousAssistantCount": previous_assistant_count,
        },
        timeout=timeout_seconds * 1000,
    )

    page.wait_for_function(
        """
        ({ assistantSelectors, previousAssistantCount }) => {
            let assistantCount = 0;

            for (const selector of assistantSelectors) {
                const count = document.querySelectorAll(selector).length;
                if (count > 0) {
                    assistantCount = count;
                    break;
                }
            }

            return assistantCount > previousAssistantCount;
        }
        """,
        arg={
            "assistantSelectors": ASSISTANT_TURN_SELECTORS,
            "previousAssistantCount": previous_assistant_count,
        },
        timeout=timeout_seconds * 1000,
    )

    assistant_turns = assistant_turn_locator(page)
    assistant_turn = assistant_turns.nth(previous_assistant_count)
    assistant_turn.wait_for(state="attached", timeout=5000)
    return assistant_turn


def wait_for_completed_response_text(
    page,
    assistant_turn,
    *,
    timeout_seconds: int,
    poll_interval: float,
    settle_cycles: int,
) -> str:
    deadline = time.time() + timeout_seconds
    latest_text = ""
    stable_cycles = 0
    saw_any_text = False

    while time.time() < deadline:
        current_text = extract_locator_text(assistant_turn)
        generating = generation_in_progress(page)

        if current_text:
            saw_any_text = True
            if current_text != latest_text:
                latest_text = current_text
                stable_cycles = 0
            else:
                stable_cycles += 1

        if saw_any_text and not generating and stable_cycles >= settle_cycles:
            return latest_text

        time.sleep(poll_interval)

    if latest_text:
        return latest_text

    raise FreeloaderError("Freeloader timed out while waiting for a response.")


def run_assistant_prompt(prompt: str, timeout: int) -> str:
    config, logger = get_runtime()
    session = None

    with BROWSER_LOCK:
        try:
            logger.info("Starting a Freeloader request.")
            session = launch_browser(config, logger)
            page = session.page
            page.bring_to_front()

            input_locator = wait_for_input(page, logger)
            previous_turns = conversation_turn_count(page)
            previous_assistant_turns = assistant_turn_count(page)

            clear_prompt_box(page, input_locator, logger)
            enter_prompt(page, input_locator, prompt, logger, config.type_delay_ms)
            submit_prompt(page, logger)

            assistant_turn = wait_for_new_assistant_turn(
                page,
                previous_turn_count=previous_turns,
                previous_assistant_count=previous_assistant_turns,
                timeout_seconds=max(1, int(timeout)),
            )
            return wait_for_completed_response_text(
                page,
                assistant_turn,
                timeout_seconds=max(1, int(timeout)),
                poll_interval=config.response_poll_interval,
                settle_cycles=config.response_settle_cycles,
            )
        except FreeloaderError:
            raise
        except Exception as exc:
            logger.exception("Freeloader request failed.")
            raise FreeloaderError(f"Freeloader request failed: {exc}") from exc
        finally:
            if session is not None:
                close_browser(session, logger)
