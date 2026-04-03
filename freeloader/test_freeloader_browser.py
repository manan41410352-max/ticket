from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from freeloader.freeloader_browser import clear_prompt_box, enter_prompt
from freeloader.freeloader_browser import _prompt_box_contains_text


def make_test_logger() -> logging.Logger:
    logger = logging.getLogger("freeloader-test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class FakeKeyboard:
    def __init__(self, page):
        self.page = page
        self.inserted_texts: list[str] = []
        self.pressed_keys: list[str] = []
        self.typed_characters: list[str] = []
        self.selection_active = False

    def press(self, key: str) -> None:
        self.pressed_keys.append(key)
        if key == "Control+A":
            self.selection_active = True
            return

        if key == "Backspace" and self.selection_active and self.page.active_locator is not None:
            self.page.active_locator.text = ""
            self.selection_active = False
            return

        if key == "Shift+Enter" and self.page.active_locator is not None:
            self.page.active_locator.text += "\n"

    def type(self, text: str, delay: int = 0) -> None:
        del delay
        self.typed_characters.append(text)
        if self.page.active_locator is not None:
            self.page.active_locator.text += text

    def insert_text(self, text: str) -> None:
        self.inserted_texts.append(text)
        if self.page.active_locator is not None:
            self.page.active_locator.text += text


class FakePage:
    def __init__(self):
        self.active_locator = None
        self.keyboard = FakeKeyboard(self)


class FakeLocator:
    def __init__(self, page: FakePage):
        self.page = page
        self.text = ""
        self.reads: list[str] = []
        self.fill_raises = False
        self.direct_set_supported = True
        self.clear_fill_raises = False
        self.dom_clear_supported = True

    def click(self) -> None:
        self.page.active_locator = self

    def fill(self, value: str) -> None:
        if value == "" and self.clear_fill_raises:
            raise RuntimeError("clear via fill failed")
        if value != "" and self.fill_raises:
            raise RuntimeError("fill failed")
        self.text = value

    def input_value(self, timeout: int = 500) -> str:
        del timeout
        if self.reads:
            return self.reads.pop(0)
        return self.text

    def text_content(self, timeout: int = 500) -> str:
        del timeout
        return self.text

    def inner_text(self, timeout: int = 500) -> str:
        del timeout
        return self.text

    def evaluate(self, script: str, arg=None):
        if "element.value = ''" in script or "element.textContent = ''" in script:
            if not self.dom_clear_supported:
                raise RuntimeError("dom clear failed")
            self.text = ""
            return True

        if "element.value = text" in script or "element.textContent = text" in script:
            if not self.direct_set_supported:
                raise RuntimeError("direct set failed")
            self.text = arg or ""
            return True

        raise RuntimeError(f"Unexpected script: {script!r}")


class FreeloaderBrowserTests(unittest.TestCase):
    def test_prompt_match_tolerates_editor_whitespace_reformatting(self) -> None:
        page = FakePage()
        locator = FakeLocator(page)
        locator.text = "Only answer this latest request and ignore older tab context:how are you"

        self.assertTrue(
            _prompt_box_contains_text(
                locator,
                "Only answer this latest request and ignore older tab context:\nhow are you",
            )
        )

    @patch("freeloader.freeloader_browser.time.sleep", return_value=None)
    def test_enter_prompt_waits_for_fill_to_settle(self, _sleep) -> None:
        page = FakePage()
        locator = FakeLocator(page)
        locator.reads = ["", "hello world"]

        enter_prompt(page, locator, "hello world", make_test_logger(), delay_ms=0)

        self.assertEqual(locator.text, "hello world")
        self.assertEqual(page.keyboard.inserted_texts, [])
        self.assertEqual(page.keyboard.typed_characters, [])

    @patch("freeloader.freeloader_browser.time.sleep", return_value=None)
    def test_enter_prompt_uses_direct_set_before_keyboard_fallback(self, _sleep) -> None:
        page = FakePage()
        locator = FakeLocator(page)
        locator.text = "partial prompt"

        enter_prompt(page, locator, "fixed prompt", make_test_logger(), delay_ms=0)

        self.assertEqual(locator.text, "fixed prompt")
        self.assertEqual(page.keyboard.inserted_texts, [])
        self.assertEqual(page.keyboard.typed_characters, [])

    @patch("freeloader.freeloader_browser.time.sleep", return_value=None)
    def test_clear_prompt_box_falls_back_to_dom_clear(self, _sleep) -> None:
        page = FakePage()
        locator = FakeLocator(page)
        locator.text = "duplicate text"
        locator.clear_fill_raises = True

        clear_prompt_box(page, locator, make_test_logger())

        self.assertEqual(locator.text, "")
        self.assertNotIn("Backspace", page.keyboard.pressed_keys)


if __name__ == "__main__":
    unittest.main()
