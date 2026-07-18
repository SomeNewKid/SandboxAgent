"""Anthropic Python SDK workload that generates and screenshots an HTML page."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_HTTP_HOST = "127.0.0.1"
_HTTP_BASE_URL_ENVIRONMENT_VARIABLE = "SANDBOX_AGENT_HTTP_BASE_URL"
_DEFAULT_MODEL = "claude-haiku-4-5"
_MAX_TOOL_ITERATIONS = 10
_AGENT_PROMPT = """
Create a single basic-style HTML document named index.html that explains the
basics of HTML to a new developer at a middle-school student level.

The page should be friendly, clear, and self-contained. Include simple sections
that explain what HTML is, elements, tags, attributes, headings, paragraphs,
links, images, lists, and how a browser reads HTML. Use embedded CSS in a
<style> block so the page is readable and pleasant, but keep the design simple.

After saving index.html, capture a screenshot of index.html.
"""
_SYSTEM_PROMPT = (
    "You are a careful web page builder. Use the provided tools to save exactly "
    "one HTML file and then capture its screenshot. Do not finish until both "
    "tool calls have succeeded."
)


def create_anthropic_client() -> Any:
    """Create an Anthropic Python SDK client."""
    anthropic_module = importlib.import_module("anthropic")
    return anthropic_module.Anthropic()


def run_html_lesson_anthropic_agent(model: str = _DEFAULT_MODEL) -> str:
    """Run the Anthropic Python SDK HTML lesson workload."""
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with _serve_site_directory(_SITE_DIRECTORY) as base_url:
        previous_base_url = os.environ.get(_HTTP_BASE_URL_ENVIRONMENT_VARIABLE)
        os.environ[_HTTP_BASE_URL_ENVIRONMENT_VARIABLE] = base_url
        try:
            try:
                result = _run_anthropic_tool_loop(model)
                completion_result = _ensure_index_screenshot()
                if completion_result:
                    return completion_result
            except Exception as error:
                return _complete_partial_agent_run(error)
        finally:
            _restore_environment_variable(
                _HTTP_BASE_URL_ENVIRONMENT_VARIABLE,
                previous_base_url,
            )

    return result


def _run_anthropic_tool_loop(model: str) -> str:
    from .anthropic_tools import (
        capture_screenshot_tool,
        run_anthropic_tool,
        save_html_document_tool,
    )

    client = create_anthropic_client()
    tools = [save_html_document_tool, capture_screenshot_tool]
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": _AGENT_PROMPT,
        }
    ]
    final_text = ""
    for _ in range(_MAX_TOOL_ITERATIONS):
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append(
            {
                "role": "assistant",
                "content": _content_blocks_to_message_content(message.content),
            }
        )
        tool_results = []
        for block in message.content:
            block_type = getattr(block, "type", "")
            if block_type == "text":
                text = getattr(block, "text", "")
                if isinstance(text, str) and text.strip():
                    final_text = text.strip()
                continue

            if block_type != "tool_use":
                continue

            tool_name = str(getattr(block, "name", ""))
            tool_input = getattr(block, "input", {})
            if not isinstance(tool_input, dict):
                tool_input = {}

            tool_result = run_anthropic_tool(tool_name, tool_input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_result),
                    "is_error": not bool(tool_result.get("success")),
                }
            )

        if not tool_results:
            return final_text

        messages.append(
            {
                "role": "user",
                "content": tool_results,
            }
        )

    return final_text


def _content_blocks_to_message_content(content: object) -> list[dict[str, Any]]:
    blocks = []
    for block in content if isinstance(content, list) else []:
        block_type = getattr(block, "type", "")
        if block_type == "text":
            blocks.append({"type": "text", "text": getattr(block, "text", "")})
        elif block_type == "tool_use":
            blocks.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}),
                }
            )

    return blocks


def _complete_partial_agent_run(error: Exception) -> str:
    index_path = _SITE_DIRECTORY / "index.html"
    if not index_path.exists():
        raise error

    return _capture_index_screenshot()


def _ensure_index_screenshot() -> str:
    index_path = _SITE_DIRECTORY / "index.html"
    screenshot_path = _OUTPUT_DIRECTORY / "index.html.png"
    if not index_path.exists() or screenshot_path.exists():
        return ""

    return _capture_index_screenshot()


def _capture_index_screenshot() -> str:
    from .tools import _capture_screenshot_file

    try:
        asyncio.run(asyncio.to_thread(_capture_screenshot_file, "index.html"))
    except Exception as screenshot_error:
        message = "Anthropic created index.html, but screenshot capture failed."
        raise RuntimeError(message) from screenshot_error

    return "Captured index.html"


@contextlib.contextmanager
def _serve_site_directory(site_directory: Path) -> Iterator[str]:
    class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

    handler_class = partial(
        QuietHTTPRequestHandler,
        directory=str(site_directory),
    )
    server = ThreadingHTTPServer((_HTTP_HOST, 0), handler_class)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    host, port = cast(tuple[str, int], server.server_address)
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def _restore_environment_variable(name: str, previous_value: str | None) -> None:
    if previous_value is None:
        os.environ.pop(name, None)
        return

    os.environ[name] = previous_value
