"""State reducer contracts shared by agents and the harness."""

from typing import Protocol

from .state import GoalState, ToolResult


class StateReducer(Protocol):
    """Protocol implemented by deterministic goal-state reducers."""

    def apply(
        self,
        goal_state: GoalState,
        tool_result: ToolResult,
    ) -> None:
        """Apply deterministic state changes from a tool result."""
        ...
