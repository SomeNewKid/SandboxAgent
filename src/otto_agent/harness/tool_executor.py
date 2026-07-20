"""Tool execution mechanics for the harness."""

from otto_agent.state import ToolResult
from otto_agent.tool import ToolRegistry, ToolRequest, ToolRuntime


class ToolExecutor:
    """Execute tools from a configured tool registry."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        """Create the executor with the tools available for an agent run."""
        self._tool_registry = tool_registry

    def execute(
        self,
        tool_name: str,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        """Execute the named tool."""
        tool = self._tool_registry.get(tool_name)

        if tool is None:
            raise ValueError(f"Tool '{tool_name}' is not registered.")

        return tool.execute(tool_request, tool_runtime)
