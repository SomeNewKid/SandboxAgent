"""Adapter for converting model output into agent decisions."""

from dataclasses import dataclass
from typing import cast

from otto_agent.agent import (
    ActionDecision,
    AgentDecision,
    FinalDecision,
    StateUpdate,
)
from otto_agent.tool import Tool, ToolArgument, ToolRegistry
from otto_agent.vocabulary import (
    COMPLETION_TYPES,
    STATE_UPDATE_OPERATIONS,
    StateUpdateArgument,
)

from .skill import AgentSkill, FinalDetailField


@dataclass(frozen=True)
class ModelDecision:
    """Structured decision returned by an AI model."""

    reason: str
    state_updates: list[StateUpdate]
    action_decision: "ModelActionDecision | None"
    final_decision: "ModelFinalDecision | None"


@dataclass(frozen=True)
class ModelActionDecision:
    """Action-shaped decision returned by an AI model."""

    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ModelFinalDecision:
    """Final-shaped decision returned by an AI model."""

    completion_type: str
    details: dict[str, object]


def agent_decision_from_model_data(data: dict[str, object]) -> AgentDecision:
    """Convert structured model data into an agent decision."""
    return agent_decision_from_model_decision(model_decision_from_data(data))


def create_model_decision_schema(
    tool_registry: ToolRegistry,
    skill: AgentSkill,
) -> dict[str, object]:
    """Create the structured-output schema for model decisions."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "reason": {
                "type": "string",
                "description": "Brief explanation of why this decision was selected.",
            },
            "state_updates": _create_state_updates_schema(),
            "action_decision": _create_action_decision_schema(tool_registry),
            "final_decision": _create_final_decision_schema(skill),
        },
        "required": [
            "reason",
            "state_updates",
            "action_decision",
            "final_decision",
        ],
    }


def model_decision_from_data(data: dict[str, object]) -> ModelDecision:
    """Convert raw model data into a structured model decision."""
    reason = _reason_from_model_data(data)
    state_updates = _state_updates_from_model_data(data["state_updates"])
    action_decision = data["action_decision"]
    final_decision = data["final_decision"]

    if action_decision is not None and final_decision is not None:
        raise ValueError("Model decision cannot include both decision branches.")

    if action_decision is None and final_decision is None:
        raise ValueError("Model decision must include one decision branch.")

    return ModelDecision(
        reason=reason,
        state_updates=state_updates,
        action_decision=_model_action_decision_from_data(action_decision),
        final_decision=_model_final_decision_from_data(final_decision),
    )


def agent_decision_from_model_decision(model_decision: ModelDecision) -> AgentDecision:
    """Convert a structured model decision into an agent decision."""
    action_decision = model_decision.action_decision

    if action_decision is not None:
        return ActionDecision(
            reason=model_decision.reason,
            state_updates=model_decision.state_updates,
            tool_name=action_decision.tool_name,
            arguments=action_decision.arguments,
        )

    final_decision = model_decision.final_decision

    if final_decision is None:
        raise ValueError("Model decision must include one decision branch.")

    return FinalDecision(
        reason=model_decision.reason,
        state_updates=model_decision.state_updates,
        completion_type=final_decision.completion_type,
        details=final_decision.details,
    )


def _create_state_updates_schema() -> dict[str, object]:
    return {
        "type": "array",
        "description": (
            "Structured updates the agent asks the harness to apply before "
            "processing the decision."
        ),
        "items": {
            "anyOf": [
                _create_state_update_operation_schema(operation_name)
                for operation_name in sorted(STATE_UPDATE_OPERATIONS)
            ],
        },
    }


def _create_state_update_operation_schema(operation_name: str) -> dict[str, object]:
    operation = STATE_UPDATE_OPERATIONS[operation_name]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "operation": {
                "type": "string",
                "enum": [operation_name],
                "description": operation.description,
            },
            "arguments": _create_state_update_arguments_schema(operation.arguments),
        },
        "required": ["operation", "arguments"],
    }


def _create_state_update_arguments_schema(
    arguments: tuple[StateUpdateArgument, ...],
) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            argument.name: _create_argument_property_schema(
                argument.argument_type,
                argument.description,
            )
            for argument in arguments
        },
        "required": [argument.name for argument in arguments],
    }


def _create_action_decision_schema(tool_registry: ToolRegistry) -> dict[str, object]:
    return {
        "anyOf": [
            {"type": "null"},
            *[_create_tool_action_schema(tool) for tool in tool_registry.tools],
        ]
    }


def _create_tool_action_schema(tool: Tool) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "tool_name": {
                "type": "string",
                "enum": [tool.name],
            },
            "arguments": _create_tool_arguments_schema(tool.arguments),
        },
        "required": ["tool_name", "arguments"],
    }


def _create_tool_arguments_schema(
    arguments: tuple[ToolArgument, ...],
) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            argument.name: _create_argument_property_schema(
                argument.argument_type,
                argument.description,
            )
            for argument in arguments
        },
        "required": [argument.name for argument in arguments],
    }


def _create_final_decision_schema(skill: AgentSkill) -> dict[str, object]:
    return {
        "anyOf": [
            {"type": "null"},
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "completion_type": {
                        "type": "string",
                        "enum": list(COMPLETION_TYPES),
                    },
                    "details": _create_final_details_schema(skill),
                },
                "required": ["completion_type", "details"],
            },
        ]
    }


def _create_final_details_schema(skill: AgentSkill) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            field_name: _create_final_detail_field_schema(field)
            for field_name, field in skill.final_detail_fields.items()
        },
        "required": list(skill.final_detail_fields),
    }


def _create_final_detail_field_schema(field: FinalDetailField) -> dict[str, object]:
    if field.allowed_values is not None:
        return {
            "type": "string",
            "description": field.description,
            "enum": list(field.allowed_values),
        }

    return {
        "type": "string",
        "description": field.description,
    }


def _create_argument_property_schema(
    argument_type: str,
    description: str,
) -> dict[str, object]:
    if argument_type == "object":
        return {
            "type": "object",
            "description": description,
            "additionalProperties": False,
            "properties": {},
            "required": [],
        }

    return {
        "type": argument_type,
        "description": description,
    }


def _model_action_decision_from_data(value: object) -> ModelActionDecision | None:
    if value is None:
        return None

    action_decision = _dict_from_model_data(value)
    return ModelActionDecision(
        tool_name=str(action_decision["tool_name"]),
        arguments=_dict_from_model_data(action_decision["arguments"]),
    )


def _model_final_decision_from_data(value: object) -> ModelFinalDecision | None:
    if value is None:
        return None

    final_decision = _dict_from_model_data(value)
    return ModelFinalDecision(
        completion_type=str(final_decision["completion_type"]),
        details=_dict_from_model_data(final_decision["details"]),
    )


def _reason_from_model_data(data: dict[str, object]) -> str:
    reason = data.get("reason")

    if not isinstance(reason, str) or not reason:
        raise ValueError("Model decision reason is required.")

    return reason


def _state_updates_from_model_data(value: object) -> list[StateUpdate]:
    if not isinstance(value, list):
        raise ValueError("Model decision state_updates must be a list.")

    state_update_data = cast(list[dict[str, object]], value)
    return [
        StateUpdate(
            operation=str(state_update["operation"]),
            arguments=_dict_from_model_data(state_update["arguments"]),
        )
        for state_update in state_update_data
    ]


def _dict_from_model_data(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)
