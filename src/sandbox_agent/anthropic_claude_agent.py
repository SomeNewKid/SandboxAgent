"""Anthropic Claude Agent SDK workload for an HTML lesson page."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
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
_DEFAULT_MODEL: str | None = None
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
    "You are a careful web page builder. Use only the provided sandbox_agent MCP "
    "tools to save exactly one HTML file and then capture its screenshot. Do not "
    "finish until both tool calls have succeeded."
)
_ALLOWED_TOOLS = [
    "mcp__sandbox_agent__save_html_document",
    "mcp__sandbox_agent__capture_screenshot",
]


def create_anthropic_claude_agent(model: str | None = _DEFAULT_MODEL) -> Any:
    """Create Claude Agent SDK options for the HTML lesson workload."""
    claude_agent_sdk = importlib.import_module("claude_agent_sdk")

    from .anthropic_claude_tools import create_anthropic_claude_mcp_server

    options = {
        "tools": [],
        "allowed_tools": _ALLOWED_TOOLS,
        "system_prompt": _SYSTEM_PROMPT,
        "mcp_servers": {
            "sandbox_agent": create_anthropic_claude_mcp_server(),
        },
        "strict_mcp_config": True,
        "permission_mode": "dontAsk",
        "max_turns": 10,
        "cwd": str(_OUTPUT_DIRECTORY),
        "setting_sources": [],
        "env": {
            "API_TIMEOUT_MS": "120000",
            "CLAUDE_CODE_MAX_RETRIES": "2",
        },
    }
    if model:
        options["model"] = model

    return claude_agent_sdk.ClaudeAgentOptions(**options)


def run_html_lesson_anthropic_claude_agent(
    model: str | None = _DEFAULT_MODEL,
) -> str:
    """Run the Claude Agent SDK HTML lesson workload."""
    return asyncio.run(_run_html_lesson_anthropic_claude_agent(model))


async def _run_html_lesson_anthropic_claude_agent(
    model: str | None = _DEFAULT_MODEL,
) -> str:
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with _serve_site_directory(_SITE_DIRECTORY) as base_url:
        previous_base_url = os.environ.get(_HTTP_BASE_URL_ENVIRONMENT_VARIABLE)
        os.environ[_HTTP_BASE_URL_ENVIRONMENT_VARIABLE] = base_url
        try:
            try:
                result = await _run_agent(model)
                completion_result = await _ensure_index_screenshot()
                if completion_result:
                    return completion_result
            except Exception as error:
                return await _complete_partial_agent_run(error)
        finally:
            _restore_environment_variable(
                _HTTP_BASE_URL_ENVIRONMENT_VARIABLE,
                previous_base_url,
            )

    return result


async def _run_agent(model: str | None) -> str:
    claude_agent_sdk = importlib.import_module("claude_agent_sdk")
    final_output = ""
    async for message in claude_agent_sdk.query(
        prompt=_AGENT_PROMPT,
        options=create_anthropic_claude_agent(model),
    ):
        subtype = getattr(message, "subtype", "")
        result = getattr(message, "result", "")
        if subtype == "success" and isinstance(result, str):
            final_output = result.strip()

    return final_output


async def _complete_partial_agent_run(error: Exception) -> str:
    index_path = _SITE_DIRECTORY / "index.html"
    if not index_path.exists():
        raise error

    return await _capture_index_screenshot()


async def _ensure_index_screenshot() -> str:
    index_path = _SITE_DIRECTORY / "index.html"
    screenshot_path = _OUTPUT_DIRECTORY / "index.html.png"
    if not index_path.exists() or screenshot_path.exists():
        return ""

    return await _capture_index_screenshot()


async def _capture_index_screenshot() -> str:
    from .tools import _capture_screenshot_file

    try:
        await asyncio.to_thread(_capture_screenshot_file, "index.html")
    except Exception as screenshot_error:
        message = "Claude Agent SDK created index.html, but screenshot failed."
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
