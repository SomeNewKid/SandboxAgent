"""Agent harness entry points."""

from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from otto_agent.agent import (
    ActionDecision,
    Agent,
    AgentDecision,
    AgentRequest,
    FinalDecision,
    StateUpdate,
)
from otto_agent.guardrail import (
    AfterToolCallGuardrailContext,
    BeforeRunGuardrailContext,
    BeforeToolCallGuardrailContext,
    FinalDecisionGuardrailContext,
    Guardrail,
    GuardrailResult,
    GuardrailSet,
)
from otto_agent.reducer import StateReducer
from otto_agent.state import GoalState, GoalStatus
from otto_agent.tool import ToolRegistry, ToolResult, ToolRuntime
from otto_agent.validation import ValidationResult

from .rules import HARNESS_VALIDATION_RULES, RegisteredToolRule
from .tool_executor import ToolExecutor
from .trace import Trace, TraceEvent
from .validation import validate_decision


class RunStatus(StrEnum):
    """Public status of an agent harness run."""

    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RunResult:
    """Public result of running an agent goal."""

    run_id: str
    status: RunStatus
    completion_type: str | None
    details: dict[str, object]
    trace_events: tuple[TraceEvent, ...]


class AgentHarness:
    """Runs agents against goals."""

    def run_agent_goal(
        self,
        agent: Agent,
        goal_state: GoalState,
        tool_registry: ToolRegistry,
        max_agent_turns: int,
        tool_runtime: ToolRuntime | None = None,
        guardrails: GuardrailSet | None = None,
    ) -> RunResult:
        """Run one agent against one goal."""
        trace = Trace()
        executor = ToolExecutor(tool_registry)
        runtime = tool_runtime or ToolRuntime()

        before_run_guardrail_result = _apply_guardrails(
            guardrails.before_run if guardrails else (),
            BeforeRunGuardrailContext(
                agent_name=agent.name,
                goal_state=goal_state,
            ),
            trace,
        )

        if not before_run_guardrail_result.allowed:
            goal_state.status = GoalStatus.FAILED
            trace.event(
                "guardrail",
                f"Before-run guardrail blocked: {before_run_guardrail_result.reason}",
            )
            return RunResult(
                run_id=goal_state.goal_id,
                status=RunStatus.FAILED,
                completion_type=None,
                details={
                    "agent": agent.name,
                    "reason_code": "guardrail_blocked",
                    "reason": before_run_guardrail_result.reason,
                },
                trace_events=trace.events,
            )

        _run_agent_loop(
            agent=agent,
            goal_state=goal_state,
            tool_registry=tool_registry,
            tool_executor=executor,
            tool_runtime=runtime,
            max_agent_turns=max_agent_turns,
            trace=trace,
            guardrails=guardrails,
        )

        if goal_state.status == GoalStatus.COMPLETED:
            result = goal_state.results[-1]
            return RunResult(
                run_id=goal_state.goal_id,
                status=RunStatus.COMPLETED,
                completion_type=result.result_type,
                details=result.data,
                trace_events=trace.events,
            )

        if goal_state.status == GoalStatus.FAILED and goal_state.results:
            result = goal_state.results[-1]
            return RunResult(
                run_id=goal_state.goal_id,
                status=RunStatus.FAILED,
                completion_type=result.result_type,
                details=result.data,
                trace_events=trace.events,
            )

        return RunResult(
            run_id=goal_state.goal_id,
            status=RunStatus.FAILED,
            completion_type=None,
            details={"agent": agent.name, "reason_code": "goal_not_completed"},
            trace_events=trace.events,
        )


def _run_agent_loop(
    agent: Agent,
    goal_state: GoalState,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    tool_runtime: ToolRuntime,
    max_agent_turns: int,
    trace: Trace,
    guardrails: GuardrailSet | None = None,
) -> None:
    done = False
    turns_completed = 0

    while not done and turns_completed < max_agent_turns:
        request = AgentRequest(
            goal_state=goal_state,
            tool_registry=tool_registry,
        )
        decision = agent.decide(request)
        trace.event(agent.name, decision.reason)
        validation = _validate_agent_decision(
            agent=agent,
            decision=decision,
            goal_state=goal_state,
            tool_registry=tool_registry,
        )

        if not validation.accepted:
            done = _apply_validation_failure(goal_state, validation, trace)
            turns_completed += 1
            continue

        _apply_state_updates(goal_state, decision.state_updates)

        if isinstance(decision, FinalDecision):
            done = _apply_final_decision(
                agent,
                goal_state,
                decision,
                trace,
                guardrails.final_decision if guardrails else None,
            )
        elif isinstance(decision, ActionDecision):
            done = _apply_action_decision(
                agent,
                goal_state=goal_state,
                decision=decision,
                reducers=agent.get_state_reducers(),
                tool_executor=tool_executor,
                tool_runtime=tool_runtime,
                trace=trace,
                before_tool_guardrails=(
                    guardrails.before_tool_call if guardrails else None
                ),
                after_tool_guardrails=(
                    guardrails.after_tool_call if guardrails else None
                ),
            )
        else:
            goal_state.status = GoalStatus.FAILED
            trace.event("harness", "Agent returned an unsupported decision.")
            done = True

        turns_completed += 1

    if not done:
        goal_state.status = GoalStatus.FAILED
        trace.event(
            "harness",
            f"Stopped after reaching {max_agent_turns} turn.",
        )


def _validate_agent_decision(
    agent: Agent,
    decision: AgentDecision,
    goal_state: GoalState,
    tool_registry: ToolRegistry,
) -> ValidationResult:
    validation = validate_decision(
        decision,
        goal_state,
        HARNESS_VALIDATION_RULES,
    )

    if not validation.accepted:
        return validation

    validation = validate_decision(
        decision,
        goal_state,
        [RegisteredToolRule(tool_registry)],
    )

    if not validation.accepted:
        return validation

    return validate_decision(
        decision,
        goal_state,
        agent.get_validation_rules(),
    )


def _apply_validation_failure(
    goal_state: GoalState,
    validation: ValidationResult,
    trace: Trace,
) -> bool:
    goal_state.status = GoalStatus.FAILED
    for error in validation.errors:
        trace.event("harness", f"Validation failed: {error.code}: {error.message}")
    return True


def _apply_state_updates(
    goal_state: GoalState,
    state_updates: list[StateUpdate],
) -> None:
    for state_update in state_updates:
        if state_update.operation == "add_claim":
            goal_state.add_claim(
                claim_type=str(state_update.arguments["claim_type"]),
                data=_dict_from_argument(state_update.arguments["data"]),
            )
        elif state_update.operation == "add_fact":
            goal_state.add_fact(
                fact_type=str(state_update.arguments["fact_type"]),
                data=_dict_from_argument(state_update.arguments["data"]),
            )
        elif state_update.operation == "add_output":
            goal_state.add_output(
                output_type=str(state_update.arguments["output_type"]),
                data=_dict_from_argument(state_update.arguments["data"]),
            )


def _dict_from_argument(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _apply_final_decision(
    agent: Agent,
    goal_state: GoalState,
    decision: FinalDecision,
    trace: Trace,
    guardrails: tuple[Guardrail, ...] | None = None,
) -> bool:
    accepted_decision = decision

    if guardrails:
        context = FinalDecisionGuardrailContext(
            goal_state=goal_state,
            decision=decision,
        )

        final_decision_guardrail_result = _apply_guardrails(
            guardrails=guardrails,
            context=context,
            trace=trace,
        )

        if not final_decision_guardrail_result.allowed:
            goal_state.status = GoalStatus.FAILED
            goal_state.add_result(
                "guardrail_blocked",
                {
                    "agent": agent.name,
                    "reason_code": "guardrail_blocked",
                    "reason": final_decision_guardrail_result.reason,
                },
            )
            trace.event(
                "guardrail",
                (
                    "Final-decision guardrail blocked: "
                    f"{final_decision_guardrail_result.reason}"
                ),
            )
            return True

        accepted_decision = context.decision

    goal_state.status = GoalStatus.COMPLETED
    goal_state.add_result(accepted_decision.completion_type, accepted_decision.details)
    trace.event(
        "harness", f"Accepted final decision: {accepted_decision.completion_type}."
    )

    return True


def _apply_action_decision(
    agent: Agent,
    goal_state: GoalState,
    decision: ActionDecision,
    reducers: list[StateReducer],
    tool_executor: ToolExecutor,
    tool_runtime: ToolRuntime,
    trace: Trace,
    before_tool_guardrails: tuple[Guardrail, ...] | None = None,
    after_tool_guardrails: tuple[Guardrail, ...] | None = None,
) -> bool:
    tool_name = decision.tool_name
    arguments = decision.arguments

    if before_tool_guardrails:
        context = BeforeToolCallGuardrailContext(
            goal_state=goal_state,
            tool_name=tool_name,
            arguments=arguments,
        )

        before_tool_call_guardrail_result = _apply_guardrails(
            before_tool_guardrails,
            context,
            trace,
        )

        if not before_tool_call_guardrail_result.allowed:
            blocked_tool_result = ToolResult(
                tool_name=tool_name,
                arguments=arguments,
                data={
                    "blocked": True,
                    "reason_code": "guardrail_blocked",
                    "reason": before_tool_call_guardrail_result.reason,
                },
            )

            goal_state.add_tool_result(blocked_tool_result)

            trace.event(
                "guardrail",
                (
                    "Before-tool-call guardrail blocked tool call: "
                    f"{before_tool_call_guardrail_result.reason}"
                ),
            )

            trace.event(
                "harness",
                f"Skipped tool {tool_name} because a guardrail blocked it.",
            )

            return False

        tool_name = context.tool_name
        arguments = context.arguments

    tool_result = tool_executor.execute(
        tool_name,
        arguments,
        tool_runtime,
    )

    if after_tool_guardrails:
        context = AfterToolCallGuardrailContext(
            goal_state=goal_state,
            tool_result=tool_result,
        )

        after_tool_call_guardrail_result = _apply_guardrails(
            after_tool_guardrails,
            context,
            trace,
        )

        if not after_tool_call_guardrail_result.allowed:
            goal_state.status = GoalStatus.FAILED
            goal_state.add_result(
                "guardrail_blocked",
                {
                    "agent": agent.name,
                    "reason_code": "guardrail_blocked",
                    "reason": after_tool_call_guardrail_result.reason,
                },
            )
            trace.event(
                "guardrail",
                (
                    "After-tool-call guardrail blocked: "
                    f"{after_tool_call_guardrail_result.reason}"
                ),
            )
            return True

        tool_result = context.tool_result

    goal_state.add_tool_result(tool_result)

    for reducer in reducers:
        reducer.apply(goal_state, tool_result)

    trace.event("harness", f"Executed tool {tool_name}.")
    return False


def _apply_guardrails(
    guardrails: tuple[Guardrail, ...],
    context: object,
    trace: Trace,
) -> GuardrailResult:
    mutated = False

    for guardrail in guardrails:
        result = guardrail.check(context)
        trace.event(
            guardrail.name,
            f"Guardrail {'allowed' if result.allowed else 'blocked'}: {result.reason}",
        )

        mutated = mutated or result.mutated

        if not result.allowed:
            return GuardrailResult(
                allowed=False,
                mutated=mutated,
                reason=result.reason,
            )

    return GuardrailResult(
        allowed=True,
        mutated=mutated,
        reason="All guardrails allowed processing.",
    )
