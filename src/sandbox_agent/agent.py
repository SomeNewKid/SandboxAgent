"""AI agent that generates and screenshots a basic HTML page."""

from __future__ import annotations

import contextlib
import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.request import urlopen

if TYPE_CHECKING:
    from agents import Agent

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_HELLO_WORLD_OUTPUT_PATH = _OUTPUT_DIRECTORY / "hello.txt"
_HELLO_WORLD_MESSAGE = "Hello, World"
_SCRAPE_URL = "https://example.com"
_SCRAPED_OUTPUT_PATH = _OUTPUT_DIRECTORY / "scraped.txt"
_ENVIRONMENT_VARIABLE_OUTPUT_PATH = _OUTPUT_DIRECTORY / "environment_variable.txt"
_ALICE_OUTPUT_PATH = _OUTPUT_DIRECTORY / "alice.txt"
_MISSING_ENVIRONMENT_VARIABLE_MESSAGE = "[NO NAMED VARIABLE]"
_EMPTY_ENVIRONMENT_VARIABLE_MESSAGE = "[EMPTY NAMED VARIABLE]"
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
_AGENTS_SDK_PROMPT = """
Create a single lightweight HTML document named example.html that explains what
HTML is to a new developer.

Use the save_html_document tool to save the file. The document should be
self-contained, valid HTML, friendly, and concise. Include a simple title,
heading, a few short paragraphs, and a small list. Do not capture a screenshot.
"""


def run_hello_world() -> str:
    """Run the minimal sandbox workload and return its output message."""
    _HELLO_WORLD_OUTPUT_PATH.write_text(_HELLO_WORLD_MESSAGE, encoding="utf-8")
    return _HELLO_WORLD_MESSAGE


def run_scrape_example_com() -> str:
    """Scrape example.com, save the response body, and return it."""
    with urlopen(_SCRAPE_URL, timeout=30) as response:
        content = response.read().decode("utf-8")

    _SCRAPED_OUTPUT_PATH.write_text(content, encoding="utf-8")
    return content


def echo_environment_variable(name: str) -> str:
    """Save and return a normalized representation of an environment variable."""
    value = os.environ.get(name)
    if value is None:
        output = _MISSING_ENVIRONMENT_VARIABLE_MESSAGE
    elif value.strip() == "":
        output = _EMPTY_ENVIRONMENT_VARIABLE_MESSAGE
    else:
        output = value

    _ENVIRONMENT_VARIABLE_OUTPUT_PATH.write_text(output, encoding="utf-8")
    return output


def use_openai_responses_api(model: str = _DEFAULT_MODEL) -> str:
    """Call the OpenAI Responses API and save the generated text."""
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=(
            "Return exactly the first sentence of Alice's Adventures in "
            "Wonderland, and no other text."
        ),
    )
    output = response.output_text.strip()
    _ALICE_OUTPUT_PATH.write_text(output, encoding="utf-8")
    return output


def create_html_explanation_agent(model: str = _DEFAULT_MODEL) -> Agent:
    """Create the Agents SDK HTML explanation writer."""
    from agents import Agent

    from .tools import save_html_document_tool

    return Agent(
        name="HTML Explanation Writer",
        model=model,
        instructions=(
            "You are a careful HTML author. Use the provided tool to save exactly "
            "one file named example.html. Do not finish until the tool call has "
            "succeeded."
        ),
        tools=[save_html_document_tool],
    )


def use_openai_agents_sdk(model: str = _DEFAULT_MODEL) -> str:
    """Run an OpenAI Agents SDK workload that saves an HTML document."""
    from agents import Runner

    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    result = Runner.run_sync(
        create_html_explanation_agent(model),
        _AGENTS_SDK_PROMPT,
        max_turns=8,
    )
    return str(result.final_output)


def create_html_lesson_agent(model: str = _DEFAULT_MODEL) -> Agent:
    """Create the Sandbox Agent HTML lesson generator."""
    from agents import Agent

    from .tools import capture_screenshot_tool, save_html_document_tool

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
    from agents import Runner

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
