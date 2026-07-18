"""Anthropic Claude Agent SDK adapters for Sandbox Agent tools."""

from __future__ import annotations

import importlib
import json
from typing import Any

from .tools import capture_screenshot, save_html_document


def create_anthropic_claude_mcp_server() -> Any:
    """Create an in-process MCP server for Claude Agent SDK tools."""
    claude_agent_sdk = importlib.import_module("claude_agent_sdk")
    save_tool = claude_agent_sdk.tool(
        "save_html_document",
        "Save an HTML document into the sandbox web root.",
        {
            "file_name": str,
            "file_contents": str,
        },
    )(_save_html_document)
    screenshot_tool = claude_agent_sdk.tool(
        "capture_screenshot",
        "Capture a screenshot of a file served by the sandbox HTTP server.",
        {
            "file_name": str,
        },
    )(_capture_screenshot)

    return claude_agent_sdk.create_sdk_mcp_server(
        name="sandbox_agent",
        version="1.0.0",
        tools=[
            save_tool,
            screenshot_tool,
        ],
    )


async def _save_html_document(args: dict[str, Any]) -> dict[str, Any]:
    result = save_html_document(
        file_name=str(args.get("file_name", "")),
        file_contents=str(args.get("file_contents", "")),
    )
    return _tool_result(result)


async def _capture_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    result = capture_screenshot(file_name=str(args.get("file_name", "")))
    return _tool_result(result)


def _tool_result(result: dict[str, bool | str]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result),
            }
        ],
        "structuredContent": result,
        "is_error": not bool(result.get("success")),
    }
