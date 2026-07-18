"""CrewAI adapters for Sandbox Agent tools."""

from __future__ import annotations

import importlib
import json
from typing import Any

from .tools import capture_screenshot, save_html_document


def create_crewai_tools() -> list[Any]:
    """Create CrewAI tool instances for the neutral sandbox tools."""
    crewai_tools_module = importlib.import_module("crewai.tools")
    base_tool = crewai_tools_module.BaseTool

    class SaveHtmlDocumentTool(base_tool):  # type: ignore[valid-type, misc]
        name: str = "save_html_document"
        description: str = "Save an HTML document into the sandbox web root."

        def _run(self, file_name: str, file_contents: str) -> str:
            result = save_html_document(file_name, file_contents)
            return json.dumps(result)

    class CaptureScreenshotTool(base_tool):  # type: ignore[valid-type, misc]
        name: str = "capture_screenshot"
        description: str = (
            "Capture a screenshot of a file served by the sandbox HTTP server."
        )

        def _run(self, file_name: str) -> str:
            result = capture_screenshot(file_name)
            return json.dumps(result)

    return [
        SaveHtmlDocumentTool(),
        CaptureScreenshotTool(),
    ]
