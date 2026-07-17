"""AI agent that generates and screenshots a basic HTML page."""

from __future__ import annotations

import contextlib
import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from agents import Agent, Runner

from .tools import capture_screenshot_tool, save_html_document_tool

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_HTTP_HOST = "127.0.0.1"
_HTTP_BASE_URL_ENVIRONMENT_VARIABLE = "SANDBOX_AGENT_HTTP_BASE_URL"
_DEFAULT_MODEL = "gpt-5-mini"
_AGENT_PROMPT = """
Create a single basic-style HTML document named index.html that explains the
basics of HTML to a new developer at a middle-school student level.

The page should be friendly, clear, and self-contained. Include simple sections
that explain what HTML is, elements, tags, attributes, headings, paragraphs,
links, images, lists, and how a browser reads HTML. Use embedded CSS in a
<style> block so the page is readable and pleasant, but keep the design simple.

After saving index.html, capture a screenshot of index.html.
"""


def create_html_lesson_agent(model: str = _DEFAULT_MODEL) -> Agent:
    """Create the Sandbox Agent HTML lesson generator."""
    return Agent(
        name="HTML Lesson Page Builder",
        model=model,
        instructions=(
            "You are a careful web page builder. Use the provided tools to save "
            "exactly one HTML file and then capture its screenshot. Do not finish "
            "until both tool calls have succeeded."
        ),
        tools=[
            save_html_document_tool,
            capture_screenshot_tool,
        ],
    )


def run_html_lesson_agent(model: str = _DEFAULT_MODEL) -> str:
    """Run the HTML lesson agent and return its final output."""
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with _serve_site_directory(_SITE_DIRECTORY) as base_url:
        previous_base_url = os.environ.get(_HTTP_BASE_URL_ENVIRONMENT_VARIABLE)
        os.environ[_HTTP_BASE_URL_ENVIRONMENT_VARIABLE] = base_url
        try:
            result = Runner.run_sync(
                create_html_lesson_agent(model),
                _AGENT_PROMPT,
                max_turns=10,
            )
        finally:
            _restore_environment_variable(
                _HTTP_BASE_URL_ENVIRONMENT_VARIABLE,
                previous_base_url,
            )

    return str(result.final_output)


@contextlib.contextmanager
def _serve_site_directory(site_directory: Path) -> Iterator[str]:
    handler_class = partial(
        SimpleHTTPRequestHandler,
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
