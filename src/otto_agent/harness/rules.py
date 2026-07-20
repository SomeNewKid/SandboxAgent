"""Harness validation rules."""

from otto_agent.agent import ActionDecision, AgentDecision, FinalDecision
from otto_agent.state import GoalState
from otto_agent.tool import ToolRegistry
from otto_agent.validation import ValidationError, ValidationRule
from otto_agent.vocabulary import COMPLETION_TYPES, STATE_UPDATE_OPERATIONS


class CompletionTypeRule:
    """Validate final decision completion types."""

    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        """Return validation errors for an invalid completion type."""
        if not isinstance(decision, FinalDecision):
            return []

        if not decision.completion_type:
            return [
                ValidationError(
                    code="missing_completion_type",
                    message="Final decisions must include a completion type.",
                )
            ]

        if decision.completion_type in COMPLETION_TYPES:
            return []

        return [
            ValidationError(
                code="invalid_completion_type",
                message=(f"Completion type '{decision.completion_type}' is not valid."),
            )
        ]


class ToolNameRule:
    """Validate action decision tool names."""

    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        """Return validation errors for a missing tool name."""
        if not isinstance(decision, ActionDecision):
            return []

        if decision.tool_name:
            return []

        return [
            ValidationError(
                code="missing_tool_name",
                message="Action decisions must include a tool name.",
            )
        ]


class RegisteredToolRule:
    """Validate action decision tool names against a tool registry."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        """Create the rule with the registry available for this run."""
        self._tool_registry = tool_registry

    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        """Return validation errors for an unregistered tool name."""
        if not isinstance(decision, ActionDecision):
            return []

        if not decision.tool_name:
            return []

        if self._tool_registry.get(decision.tool_name) is not None:
            return []

        return [
            ValidationError(
                code="unknown_tool",
                message=f"Tool '{decision.tool_name}' is not registered.",
            )
        ]


class StateUpdateShapeRule:
    """Validate state update operation and argument shapes."""

    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        """Return validation errors for invalid state updates."""
        errors: list[ValidationError] = []

        for state_update in decision.state_updates:
            if state_update.operation not in STATE_UPDATE_OPERATIONS:
                errors.append(
                    ValidationError(
                        code="unknown_state_update_operation",
                        message=(
                            f"State update operation "
                            f"'{state_update.operation}' is not valid."
                        ),
                    )
                )
                continue

            if state_update.operation == "add_claim":
                errors.extend(
                    self._validate_typed_data_update(
                        arguments=state_update.arguments,
                        type_key="claim_type",
                        missing_type_code="missing_claim_type",
                        missing_type_message=(
                            "State update add_claim must include a claim type."
                        ),
                    )
                )
            elif state_update.operation == "add_fact":
                errors.extend(
                    self._validate_typed_data_update(
                        arguments=state_update.arguments,
                        type_key="fact_type",
                        missing_type_code="missing_fact_type",
                        missing_type_message=(
                            "State update add_fact must include a fact type."
                        ),
                    )
                )
            elif state_update.operation == "add_output":
                errors.extend(
                    self._validate_typed_data_update(
                        arguments=state_update.arguments,
                        type_key="output_type",
                        missing_type_code="missing_output_type",
                        missing_type_message=(
                            "State update add_output must include an output type."
                        ),
                    )
                )
        return errors

    def _validate_typed_data_update(
        self,
        arguments: dict[str, object],
        type_key: str,
        missing_type_code: str,
        missing_type_message: str,
    ) -> list[ValidationError]:
        errors: list[ValidationError] = []

        if not self._has_non_empty_string(arguments, type_key):
            errors.append(
                ValidationError(
                    code=missing_type_code,
                    message=missing_type_message,
                )
            )

        if not self._has_dict(arguments, "data"):
            errors.append(
                ValidationError(
                    code="missing_data",
                    message="State updates must include data.",
                )
            )

        return errors

    def _has_dict(
        self,
        arguments: dict[str, object],
        key: str,
    ) -> bool:
        return isinstance(arguments.get(key), dict)

    def _has_non_empty_string(
        self,
        arguments: dict[str, object],
        key: str,
    ) -> bool:
        value = arguments.get(key)
        return isinstance(value, str) and bool(value)


HARNESS_VALIDATION_RULES: list[ValidationRule] = [
    CompletionTypeRule(),
    ToolNameRule(),
    StateUpdateShapeRule(),
]
