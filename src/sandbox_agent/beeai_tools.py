"""BeeAI Framework adapters for Sandbox Agent tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .tools import capture_screenshot, save_html_document

if TYPE_CHECKING:
    from beeai_framework.tools import AnyTool


def _json_tool_result(result: dict[str, bool | str]) -> str:
    return json.dumps(result, separators=(",", ":"))


def _build_save_html_document_tool() -> AnyTool:
    from beeai_framework.tools import tool

    @tool(
        name="save_html_document",
        description=(
            "Save an HTML document to the web root. Arguments are file_name and "
            "file_contents."
        ),
    )
    def beeai_save_html_document(file_name: str, file_contents: str) -> str:
        return _json_tool_result(save_html_document(file_name, file_contents))

    return beeai_save_html_document


def _build_capture_screenshot_tool() -> AnyTool:
    from beeai_framework.tools import tool

    @tool(
        name="capture_screenshot",
        description=(
            "Capture a screenshot of a named HTML file from the local HTTP server. "
            "Argument is file_name."
        ),
    )
    def beeai_capture_screenshot(file_name: str) -> str:
        return _json_tool_result(capture_screenshot(file_name))

    return beeai_capture_screenshot


save_html_document_tool = _build_save_html_document_tool()
capture_screenshot_tool = _build_capture_screenshot_tool()
