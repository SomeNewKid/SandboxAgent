"""Command-line interface for the application."""

from __future__ import annotations

import sys

from docker_sandbox.cli import main as docker_sandbox_main
from docker_sandbox.container_guard import ensure_running_in_docker_sandbox
from sandbox_agent.agent import run_html_lesson_agent


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    args = sys.argv[1:] if argv is None else argv
    if _is_docker_sandbox_invocation(args):
        return docker_sandbox_main(args)

    ensure_running_in_docker_sandbox()

    print(run_html_lesson_agent())
    return 0


def _is_docker_sandbox_invocation(args: list[str]) -> bool:
    return any(argument.startswith("--profile") for argument in args)
