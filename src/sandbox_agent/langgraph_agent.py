"""LangGraph agent that generates and screenshots a basic HTML page."""

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


def create_langgraph_agent(model: str = _DEFAULT_MODEL) -> Any:
    """Create the LangGraph HTML lesson generator."""
    from .langgraph_tools import capture_screenshot_tool, save_html_document_tool

    chat_openai_module = importlib.import_module("langchain_openai")
    langgraph_prebuilt_module = importlib.import_module("langgraph.prebuilt")
    chat_model = chat_openai_module.ChatOpenAI(model=model)
    return langgraph_prebuilt_module.create_react_agent(
        chat_model,
        tools=[
            save_html_document_tool,
            capture_screenshot_tool,
        ],
        prompt=(
            "You are a careful web page builder. Use the provided tools to save "
            "exactly one HTML file and then capture its screenshot. Do not finish "
            "until both tool calls have succeeded."
        ),
        name="html_lesson_page_builder",
    )


def run_html_lesson_langgraph_agent(model: str = _DEFAULT_MODEL) -> str:
    """Run the LangGraph HTML lesson agent and return its final output."""
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with _serve_site_directory(_SITE_DIRECTORY) as base_url:
        previous_base_url = os.environ.get(_HTTP_BASE_URL_ENVIRONMENT_VARIABLE)
        os.environ[_HTTP_BASE_URL_ENVIRONMENT_VARIABLE] = base_url
        try:
            try:
                result = create_langgraph_agent(model).invoke(
                    {"messages": [{"role": "user", "content": _AGENT_PROMPT}]},
                    config={"recursion_limit": 30},
                )
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

    return _final_output_text(result)


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
        message = "LangGraph created index.html, but screenshot capture failed."
        raise RuntimeError(message) from screenshot_error

    return "Captured index.html"


def _final_output_text(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        text = _message_text(message)
        if text:
            return text

    return ""


def _message_text(message: object) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                text_parts.append(item["text"])

        return "".join(text_parts).strip()

    return ""


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
