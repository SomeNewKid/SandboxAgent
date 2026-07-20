"""Otto Agent workload that generates and screenshots a basic HTML page."""

from __future__ import annotations

import asyncio
import contextlib
import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from otto_agent.agents.skill import AgentSkill, FinalDetailField
from otto_agent.harness.runner import AgentHarness, RunResult
from otto_agent.model import ModelClientRegistry
from otto_agent.openai_helper import create_openai_model_client_registry
from otto_agent.skilled_agent import SkilledAgent
from otto_agent.state import EntityRef, GoalState, GoalStatus
from otto_agent.tool import Tool, ToolRegistry

from .otto_tools import capture_screenshot_tool, save_html_document_tool

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_HTTP_HOST = "127.0.0.1"
_HTTP_BASE_URL_ENVIRONMENT_VARIABLE = "SANDBOX_AGENT_HTTP_BASE_URL"
_DEFAULT_MODEL = "gpt-5-mini"
_MAX_MODEL_CALLS = 6
_MAX_AGENT_TURNS = 6

_HTML_LESSON_SKILL = AgentSkill(
    name="html_lesson_page_builder",
    goal=(
        "Create one self-contained HTML document named index.html that explains "
        "the basics of HTML to a new developer at a middle-school student level, "
        "then capture a screenshot of that document."
    ),
    instructions=(
        "First call save_html_document with file_name set to index.html and "
        "file_contents set to a complete HTML document. The page should explain "
        "what HTML is, elements, tags, attributes, headings, paragraphs, links, "
        "images, lists, and how a browser reads HTML. Use embedded CSS in a "
        "style block so the page is readable and pleasant, but keep the design "
        "simple. After the save tool succeeds, call capture_screenshot with "
        "file_name set to index.html. If there are no prior tool results, your "
        "next decision must be an action_decision for save_html_document. If "
        "index.html has been saved but no screenshot has been captured, your "
        "next decision must be an action_decision for capture_screenshot. "
        "Return a final decision only after both tools have succeeded."
    ),
    final_detail_fields={
        "html_file": FinalDetailField(
            description="The HTML file that was created.",
        ),
        "screenshot_file": FinalDetailField(
            description="The screenshot file that was captured.",
        ),
        "reason_code": FinalDetailField(
            description="The structured reason for the final result.",
            allowed_values={
                "html_lesson_created": (
                    "The HTML lesson was created and screenshotted."
                ),
                "html_lesson_failed": "The HTML lesson could not be completed.",
            },
        ),
    },
)


def create_otto_agent(
    model_client_registry: ModelClientRegistry,
) -> SkilledAgent:
    """Create the Otto Agent HTML lesson generator."""
    return SkilledAgent(
        name="html_lesson_otto_agent",
        skill=_HTML_LESSON_SKILL,
        model_client_registry=model_client_registry,
        response_schema_name="html_lesson_otto_agent_decision",
        system_prompt=(
            "You make structured decisions for a web page creation harness. "
            "Use tools exactly as instructed. Return only data matching the "
            "provided structured output schema."
        ),
    )


def run_html_lesson_otto_agent(model: str = _DEFAULT_MODEL) -> str:
    """Run the Otto Agent HTML lesson workload and return its final output."""
    _SITE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with _serve_site_directory(_SITE_DIRECTORY) as base_url:
        previous_base_url = os.environ.get(_HTTP_BASE_URL_ENVIRONMENT_VARIABLE)
        os.environ[_HTTP_BASE_URL_ENVIRONMENT_VARIABLE] = base_url
        try:
            try:
                result = _run_otto_agent(model)
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


def _run_otto_agent(model: str) -> RunResult:
    model_client_registry = create_openai_model_client_registry(
        max_model_calls=_MAX_MODEL_CALLS,
        model_name=model,
    )
    agent = create_otto_agent(model_client_registry)
    return AgentHarness().run_agent_goal(
        agent=agent,
        goal_state=_create_goal_state(),
        tool_registry=_create_tool_registry(),
        max_agent_turns=_MAX_AGENT_TURNS,
    )


def _create_goal_state() -> GoalState:
    return GoalState(
        goal_id="html-lesson-page",
        status=GoalStatus.RUNNING,
        root_entity=EntityRef(
            entity_type="html_document",
            entity_id="index.html",
        ),
    )


def _create_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        tools=cast(
            tuple[Tool, ...],
            (
                save_html_document_tool,
                capture_screenshot_tool,
            ),
        ),
    )


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
        message = "Otto Agent created index.html, but screenshot capture failed."
        raise RuntimeError(message) from screenshot_error

    return "Captured index.html"


def _final_output_text(result: RunResult) -> str:
    if result.status.value != "completed":
        trace_messages = [
            f"{event.sender}: {event.message}" for event in result.trace_events
        ]
        trace_text = "\n".join(trace_messages)
        return f"Otto Agent failed: {result.details}\n{trace_text}"

    return (
        f"{result.details.get('html_file', 'index.html')} created; "
        f"{result.details.get('screenshot_file', 'index.html.png')} captured"
    )


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
