"""Prompt creation for model-backed agents."""

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, cast

from otto_agent.state import GoalState
from otto_agent.tool import ToolRegistry
from otto_agent.vocabulary import COMPLETION_TYPES, STATE_UPDATE_OPERATIONS

from .skill import AgentSkill, FinalDetailField


def create_model_user_prompt(
    skill: AgentSkill,
    goal_state: GoalState,
    tool_registry: ToolRegistry,
) -> str:
    """Create prompt text for a model decision request."""
    sections = [
        "You are deciding the next step for an agent goal.",
        _agent_goal_section(skill),
        _agent_instructions_section(skill),
        _decision_rules_section(),
        _output_requirement_section(),
        _available_tools_section(tool_registry),
        _completion_types_section(),
        _state_update_operations_section(),
        _claim_types_section(skill),
        _fact_types_section(skill),
        _output_types_section(skill),
        _final_detail_fields_section(skill),
        _goal_state_section(goal_state),
        _tool_results_section(goal_state),
    ]

    return "\n\n".join(section for section in sections if section)


def _agent_goal_section(skill: AgentSkill) -> str:
    return f"Agent goal:\n{skill.goal}"


def _agent_instructions_section(skill: AgentSkill) -> str:
    if not skill.instructions:
        return ""

    return f"Agent instructions:\n{skill.instructions}"


def _decision_rules_section() -> str:
    return "\n".join(
        [
            "Decision rules:",
            (
                "- On each turn, choose the single next step that best advances "
                "the current goal."
            ),
            (
                "- Return an action_decision when an available tool is needed "
                "before the goal can safely finish."
            ),
            (
                "- Return a final_decision when the goal is complete, blocked, "
                "needs handoff, or needs approval."
            ),
            (
                "- Set exactly one of action_decision or final_decision to an "
                "object. Set the other field to null."
            ),
            "- Do not request a tool unless it is listed in the available tools.",
            (
                "- Use only the current goal state and prior tool results; do "
                "not invent missing data."
            ),
            "- Keep reason brief and explain why this next step was chosen.",
        ]
    )


def _output_requirement_section() -> str:
    return "\n".join(
        [
            "Output requirement:",
            "- Your response must match the provided structured output schema.",
            "- Do not include free-form text outside the structured response.",
        ]
    )


def _available_tools_section(tool_registry: ToolRegistry) -> str:
    lines = ["Available tools:"]

    for tool in tool_registry.tools:
        lines.append(f"- {tool.name}: {tool.description}")
        lines.append("  Arguments:")

        for argument in tool.arguments:
            lines.append(
                f"  - {argument.name} ({argument.argument_type}): "
                f"{argument.description}"
            )

    return "\n".join(lines)


def _completion_types_section() -> str:
    lines = ["Completion types:"]

    for completion_type, description in COMPLETION_TYPES.items():
        lines.append(f"- {completion_type}: {description}")

    return "\n".join(lines)


def _state_update_operations_section() -> str:
    lines = ["State update operations:"]

    for operation, metadata in sorted(STATE_UPDATE_OPERATIONS.items()):
        lines.append(f"- {operation}: {metadata.description}")
        lines.append("  Arguments:")

        for argument in metadata.arguments:
            lines.append(
                f"  - {argument.name} ({argument.argument_type}): "
                f"{argument.description}"
            )

    return "\n".join(lines)


def _claim_types_section(skill: AgentSkill) -> str:
    if not skill.claim_types:
        return ""

    lines = [
        "Allowed claim types:",
        "Use these values only in state_updates entries whose operation is add_claim.",
    ]

    for claim_type, description in sorted(skill.claim_types.items()):
        lines.append(f"- {claim_type}: {description}")

    return "\n".join(lines)


def _fact_types_section(skill: AgentSkill) -> str:
    if not skill.fact_types:
        return ""

    lines = [
        "Allowed fact types:",
        "Use these values only in state_updates entries whose operation is add_fact.",
    ]

    for fact_type, description in sorted(skill.fact_types.items()):
        lines.append(f"- {fact_type}: {description}")

    return "\n".join(lines)


def _output_types_section(skill: AgentSkill) -> str:
    if not skill.output_types:
        return ""

    lines = [
        "Allowed output types:",
        "Use these values only in state_updates entries whose operation is add_output.",
    ]

    for output_type, description in sorted(skill.output_types.items()):
        lines.append(f"- {output_type}: {description}")

    return "\n".join(lines)


def _final_detail_fields_section(skill: AgentSkill) -> str:
    if not skill.final_detail_fields:
        return ""

    lines = [
        "Final detail fields:",
        "Use these fields only in final_decision.details.",
    ]

    for field_name, metadata in sorted(skill.final_detail_fields.items()):
        lines.extend(_final_detail_field_lines(field_name, metadata))

    return "\n".join(lines)


def _final_detail_field_lines(
    field_name: str,
    field_metadata: FinalDetailField,
) -> list[str]:
    lines = [f"- {field_name}: {field_metadata.description}"]

    if not field_metadata.allowed_values:
        lines.append("  Allowed values: any value that satisfies the description.")
        return lines

    lines.append("  Allowed values:")

    for value, description in sorted(field_metadata.allowed_values.items()):
        lines.append(f"  - {value}: {description}")

    return lines


def _goal_state_section(goal_state: GoalState) -> str:
    serialized = json.dumps(
        _json_safe_goal_state(goal_state),
        indent=2,
        sort_keys=True,
    )
    return f"Current goal state:\n{serialized}"


def _tool_results_section(goal_state: GoalState) -> str:
    serialized = json.dumps(
        _json_safe_value(goal_state.tool_results),
        indent=2,
        sort_keys=True,
    )
    return f"Prior tool results:\n{serialized}"


def _json_safe_goal_state(goal_state: GoalState) -> dict[str, object]:
    goal_state_data = _json_safe_value(goal_state)
    goal_state_dict = cast(dict[str, object], goal_state_data)
    return {
        key: value for key, value in goal_state_dict.items() if key != "tool_results"
    }


def _json_safe_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        dataclass_value = cast(Any, value)
        dataclass_dict = asdict(dataclass_value)
        return _json_safe_value(dataclass_dict)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        dict_value = cast(dict[object, object], value)
        return {str(key): _json_safe_value(item) for key, item in dict_value.items()}

    if isinstance(value, list):
        list_value = cast(list[object], value)
        return [_json_safe_value(item) for item in list_value]

    if isinstance(value, tuple):
        tuple_value = cast(tuple[object, ...], value)
        return [_json_safe_value(item) for item in tuple_value]

    return value
