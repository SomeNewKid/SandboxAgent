"""BeeAI agent that generates and screenshots a basic HTML page."""

from __future__ import annotations

import asyncio
import contextlib
import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from beeai_framework.agents.base import AgentOutput
    from beeai_framework.agents.lite.agent import LiteAgent
    from beeai_framework.backend.message import Message

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_HTTP_HOST = "127.0.0.1"
_HTTP_BASE_URL_ENVIRONMENT_VARIABLE = "SANDBOX_AGENT_HTTP_BASE_URL"
_DEFAULT_MODEL = "gpt-5-mini"
_AGENT_PROMPT = """
You are a careful web page builder. Use the provided tools to save exactly one
HTML file and then capture its screenshot. Do not finish until both tool calls
have succeeded.

Create a single basic-style HTML document named index.html that explains the
basics of HTML to a new developer at a middle-school student level.

The page should be friendly, clear, and self-contained. Include simple sections
that explain what HTML is, elements, tags, attributes, headings, paragraphs,
links, images, lists, and how a browser reads HTML. Use embedded CSS in a
<style> block so the page is readable and pleasant, but keep the design simple.

After saving index.html, capture a screenshot of index.html.
"""


def create_beeai_agent(model: str = _DEFAULT_MODEL) -> LiteAgent:
    """Create the BeeAI HTML lesson generator."""
    from beeai_framework.adapters.openai.backend.chat import OpenAIChatModel
    from beeai_framework.agents.lite.agent import LiteAgent

    from .beeai_tools import capture_screenshot_tool, save_html_document_tool

    return LiteAgent(
        llm=OpenAIChatModel(model),
        tools=[
            save_html_document_tool,
            capture_screenshot_tool,
        ],
        name="HTML Lesson Page Builder",
        description=(
            "Creates one HTML lesson page and captures a screenshot of the saved page."
        ),
    )


def run_html_lesson_beeai_agent(model: str = _DEFAULT_MODEL) -> str:
    """Run the BeeAI HTML lesson agent and return its final output."""
    return asyncio.run(_run_html_lesson_beeai_agent(model))


async def _run_html_lesson_beeai_agent(model: str = _DEFAULT_MODEL) -> str:
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with _serve_site_directory(_SITE_DIRECTORY) as base_url:
        previous_base_url = os.environ.get(_HTTP_BASE_URL_ENVIRONMENT_VARIABLE)
        os.environ[_HTTP_BASE_URL_ENVIRONMENT_VARIABLE] = base_url
        try:
            try:
                result = await create_beeai_agent(model).run(
                    _AGENT_PROMPT,
                    max_iterations=20,
                )
            except Exception as error:
                return await _complete_partial_agent_run(error)
        finally:
            _restore_environment_variable(
                _HTTP_BASE_URL_ENVIRONMENT_VARIABLE,
                previous_base_url,
            )

    return _final_output_text(result)


async def _complete_partial_agent_run(error: Exception) -> str:
    index_path = _SITE_DIRECTORY / "index.html"
    if not index_path.exists():
        raise error

    from .tools import _capture_screenshot_file

    try:
        await asyncio.to_thread(_capture_screenshot_file, "index.html")
    except Exception as screenshot_error:
        message = "BeeAI created index.html, but screenshot capture failed."
        raise RuntimeError(message) from screenshot_error

    return "Captured index.html"


def _final_output_text(result: AgentOutput) -> str:
    for message in reversed(result.output):
        text = _message_text(message)
        if text:
            return text

    return ""


def _message_text(message: Message[Any]) -> str:
    text = getattr(message, "text", "")
    return text if isinstance(text, str) else ""


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
