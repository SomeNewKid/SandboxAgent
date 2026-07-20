"""Validation behavior used by the agent harness."""

from otto_agent.agent import AgentDecision
from otto_agent.state import GoalState
from otto_agent.validation import ValidationError, ValidationResult, ValidationRule


def validate_decision(
    decision: AgentDecision,
    goal_state: GoalState,
    rules: list[ValidationRule],
) -> ValidationResult:
    """Validate an agent decision using the provided rules."""
    errors: list[ValidationError] = []

    for rule in rules:
        errors.extend(rule.validate(decision, goal_state))

    return ValidationResult(errors=errors)
