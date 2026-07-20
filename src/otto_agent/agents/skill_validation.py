"""Validation rules derived from agent skills."""

from otto_agent.agent import AgentDecision, FinalDecision
from otto_agent.state import GoalState
from otto_agent.validation import ValidationError

from .skill import AgentSkill, FinalDetailField


class SkillVocabularyRule:
    """Validate decision vocabulary against an agent skill."""

    def __init__(self, skill: AgentSkill) -> None:
        """Create the rule for one agent skill."""
        self._skill = skill

    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        """Return validation errors for invalid skill vocabulary."""
        errors: list[ValidationError] = []

        for state_update in decision.state_updates:
            if state_update.operation == "add_claim":
                errors.extend(
                    self._validate_state_update_type(
                        arguments=state_update.arguments,
                        type_key="claim_type",
                        allowed_values=self._skill.claim_types,
                        error_code="invalid_claim_type",
                        type_label="Claim type",
                    )
                )
            elif state_update.operation == "add_fact":
                errors.extend(
                    self._validate_state_update_type(
                        arguments=state_update.arguments,
                        type_key="fact_type",
                        allowed_values=self._skill.fact_types,
                        error_code="invalid_fact_type",
                        type_label="Fact type",
                    )
                )
            elif state_update.operation == "add_output":
                errors.extend(
                    self._validate_state_update_type(
                        arguments=state_update.arguments,
                        type_key="output_type",
                        allowed_values=self._skill.output_types,
                        error_code="invalid_output_type",
                        type_label="Output type",
                    )
                )

        if isinstance(decision, FinalDecision):
            errors.extend(self._validate_final_details(decision))

        return errors

    def _validate_state_update_type(
        self,
        arguments: dict[str, object],
        type_key: str,
        allowed_values: dict[str, str],
        error_code: str,
        type_label: str,
    ) -> list[ValidationError]:
        value = arguments.get(type_key)

        if not isinstance(value, str):
            return []

        if value in allowed_values:
            return []

        return [
            ValidationError(
                code=error_code,
                message=f"{type_label} '{value}' is not valid for this agent skill.",
            )
        ]

    def _validate_final_details(
        self,
        decision: FinalDecision,
    ) -> list[ValidationError]:
        errors: list[ValidationError] = []

        for field_name in decision.details:
            if field_name not in self._skill.final_detail_fields:
                errors.append(
                    ValidationError(
                        code="invalid_final_detail_field",
                        message=(
                            f"Final detail field '{field_name}' is not valid "
                            "for this agent skill."
                        ),
                    )
                )

        for field_name, field in self._skill.final_detail_fields.items():
            if field_name not in decision.details:
                errors.append(
                    ValidationError(
                        code="missing_final_detail_field",
                        message=f"Final detail field '{field_name}' is required.",
                    )
                )
                continue

            value_error = self._validate_final_detail_value(
                field_name,
                field,
                decision.details[field_name],
            )
            if value_error is not None:
                errors.append(value_error)

        return errors

    def _validate_final_detail_value(
        self,
        field_name: str,
        field: FinalDetailField,
        value: object,
    ) -> ValidationError | None:
        if field.allowed_values is None:
            return None

        if isinstance(value, str) and value in field.allowed_values:
            return None

        return ValidationError(
            code="invalid_final_detail_value",
            message=(
                f"Final detail field '{field_name}' has an invalid value for "
                "this agent skill."
            ),
        )
