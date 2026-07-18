"""LangGraph adapters for Sandbox Agent tools."""

from __future__ import annotations

from langchain_core.tools import tool  # type: ignore[reportMissingImports]

from .tools import capture_screenshot, save_html_document


@tool
def save_html_document_tool(
    file_name: str,
    file_contents: str,
) -> dict[str, bool | str]:
    """Save an HTML document into the sandbox web root."""
    return save_html_document(file_name, file_contents)


@tool
def capture_screenshot_tool(file_name: str) -> dict[str, bool | str]:
    """Capture a screenshot of a file served by the sandbox HTTP server."""
    return capture_screenshot(file_name)
