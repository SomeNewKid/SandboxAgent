"""Tool contracts shared by the harness and domain tools."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from .state import ToolResult

ToolRequest = dict[str, object]


def _empty_runtime_values() -> Mapping[str, object]:
    return {}


@dataclass(frozen=True)
class ToolRuntime:
    """Harness-provided runtime values hidden from agent tool requests."""

    values: Mapping[str, object] = field(default_factory=_empty_runtime_values)


@dataclass(frozen=True)
class ToolArgument:
    """Argument accepted by a tool."""

    name: str
    argument_type: str
    description: str


class Tool(Protocol):
    """Protocol implemented by tools executed by the harness."""

    name: str
    description: str
    arguments: tuple[ToolArgument, ...]

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        """Execute the tool with structured arguments."""
        ...


@dataclass(frozen=True)
class ToolRegistry:
    """Collection of tools available to an agent run."""

    tools: tuple[Tool, ...]

    def __post_init__(self) -> None:
        tool_names: set[str] = set()

        for tool in self.tools:
            if tool.name in tool_names:
                raise ValueError(f"Duplicate tool name: {tool.name}")

            tool_names.add(tool.name)

    def get(self, tool_name: str) -> Tool | None:
        """Return the named tool, if available."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool

        return None
