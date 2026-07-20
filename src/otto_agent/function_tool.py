"""Helpers for exposing ordinary functions as agent tools."""

from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass

from otto_agent.state import ToolResult
from otto_agent.tool import ToolArgument, ToolRequest, ToolRuntime

ToolFunction = Callable[..., object]


@dataclass(frozen=True)
class FunctionTool:
    """Tool adapter for an ordinary Python function."""

    name: str
    description: str
    function: ToolFunction
    arguments: tuple[ToolArgument, ...] = ()
    result_key: str = "value"

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        """Execute the wrapped function and return a structured tool result."""
        keyword_arguments = {
            argument.name: tool_request[argument.name] for argument in self.arguments
        }
        result = self.function(**keyword_arguments)

        return ToolResult(
            tool_name=self.name,
            arguments=tool_request,
            data=self._result_data(result),
        )

    def _result_data(self, result: object) -> dict[str, object]:
        if is_dataclass(result) and not isinstance(result, type):
            return asdict(result)

        if isinstance(result, dict):
            return dict(result)

        return {self.result_key: result}
