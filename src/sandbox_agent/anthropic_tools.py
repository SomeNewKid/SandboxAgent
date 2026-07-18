"""Anthropic Python SDK adapters for Sandbox Agent tools."""

from __future__ import annotations

from typing import Any

from .tools import capture_screenshot, save_html_document

save_html_document_tool: dict[str, Any] = {
    "name": "save_html_document",
    "description": "Save an HTML document into the sandbox web root.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "The file name to create, such as index.html.",
            },
            "file_contents": {
                "type": "string",
                "description": "The full HTML document contents to write.",
            },
        },
        "required": ["file_name", "file_contents"],
    },
}
capture_screenshot_tool: dict[str, Any] = {
    "name": "capture_screenshot",
    "description": "Capture a screenshot of a file served by the sandbox HTTP server.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "The HTML file name to capture, such as index.html.",
            },
        },
        "required": ["file_name"],
    },
}


def run_anthropic_tool(name: str, tool_input: dict[str, Any]) -> dict[str, bool | str]:
    """Run a Sandbox Agent tool requested by the Anthropic Python SDK."""
    if name == "save_html_document":
        return save_html_document(
            file_name=str(tool_input.get("file_name", "")),
            file_contents=str(tool_input.get("file_contents", "")),
        )

    if name == "capture_screenshot":
        return capture_screenshot(file_name=str(tool_input.get("file_name", "")))

    return {
        "success": False,
        "message": f"Unknown tool: {name}",
    }
