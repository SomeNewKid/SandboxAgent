"""Agent contracts shared by agents and the harness."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from .state import GoalState

if TYPE_CHECKING:
    from .reducer import StateReducer
    from .tool import ToolRegistry
    from .validation import ValidationRule


@dataclass(frozen=True)
class AgentRequest:
    """Request passed from the harness to an agent."""

    goal_state: GoalState
    tool_registry: ToolRegistry


@dataclass(frozen=True)
class StateUpdate:
    """State update requested by an agent for harness validation."""

    operation: str
    arguments: dict[str, object]


def _empty_state_updates() -> list[StateUpdate]:
    return []


@dataclass(frozen=True, kw_only=True)
class AgentDecision(ABC):
    """Decision returned by an agent to the harness."""

    reason: str
    state_updates: list[StateUpdate] = field(default_factory=_empty_state_updates)


@dataclass(frozen=True, kw_only=True)
class ActionDecision(AgentDecision):
    """Decision requesting the harness to execute a tool."""

    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True, kw_only=True)
class FinalDecision(AgentDecision):
    """Decision requesting the harness to stop the agent run."""

    completion_type: str
    details: dict[str, object]


class Agent(Protocol):
    """Protocol implemented by agents managed by the harness."""

    name: str

    def decide(self, request: AgentRequest) -> AgentDecision:
        """Propose the next step for the harness to validate and execute."""
        ...

    def get_validation_rules(self) -> list[ValidationRule]:
        """Return validation rules specific to this agent."""
        ...

    def get_state_reducers(self) -> list[StateReducer]:
        """Return reducers used by this agent to update goal state."""
        ...
