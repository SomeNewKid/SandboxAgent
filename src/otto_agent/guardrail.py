"""Represents the result of a guardrail check and defines the Guardrail protocol."""

from dataclasses import dataclass
from typing import Protocol

from .agent import FinalDecision
from .state import GoalState, ToolResult


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    mutated: bool
    reason: str


class Guardrail(Protocol):
    name: str

    def check(self, context: object) -> GuardrailResult: ...


@dataclass
class BeforeRunGuardrailContext:
    agent_name: str
    goal_state: GoalState


@dataclass
class FinalDecisionGuardrailContext:
    goal_state: GoalState
    decision: FinalDecision


@dataclass
class BeforeToolCallGuardrailContext:
    goal_state: GoalState
    tool_name: str
    arguments: dict[str, object]


@dataclass
class AfterToolCallGuardrailContext:
    goal_state: GoalState
    tool_result: ToolResult


@dataclass(frozen=True)
class GuardrailSet:
    before_run: tuple[Guardrail, ...] = ()
    final_decision: tuple[Guardrail, ...] = ()
    before_tool_call: tuple[Guardrail, ...] = ()
    after_tool_call: tuple[Guardrail, ...] = ()
