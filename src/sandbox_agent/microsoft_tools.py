"""Microsoft Agent Framework adapters for Sandbox Agent tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from pydantic import Field

from .tools import capture_screenshot, save_html_document


def _tool(*args: object, **kwargs: object) -> Callable[[Callable[..., Any]], Any]:
    import importlib

    agent_framework = importlib.import_module("agent_framework")
    return agent_framework.tool(*args, **kwargs)


@_tool(approval_mode="never_require")
def save_html_document_tool(
    file_name: Annotated[str, Field(description="The file name to create.")],
    file_contents: Annotated[str, Field(description="The full HTML document.")],
) -> dict[str, bool | str]:
    """Save an HTML document into the sandbox web root."""
    return save_html_document(file_name, file_contents)


@_tool(approval_mode="never_require")
def capture_screenshot_tool(
    file_name: Annotated[str, Field(description="The HTML file name to capture.")],
) -> dict[str, bool | str]:
    """Capture a screenshot of a file served by the sandbox HTTP server."""
    return capture_screenshot(file_name)
