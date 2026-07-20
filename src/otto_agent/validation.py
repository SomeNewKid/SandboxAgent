"""Validation contracts shared by agents and the harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .agent import AgentDecision
    from .state import GoalState


@dataclass(frozen=True)
class ValidationError:
    """One validation problem found in an agent decision."""

    code: str
    message: str


def _empty_validation_errors() -> list[ValidationError]:
    return []


@dataclass(frozen=True)
class ValidationResult:
    """Validation result for an agent decision."""

    errors: list[ValidationError] = field(default_factory=_empty_validation_errors)

    @property
    def accepted(self) -> bool:
        """Return whether validation found no errors."""
        return not self.errors


class ValidationRule(Protocol):
    """Rule that validates an agent decision."""

    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        """Return validation errors for one rule."""
        ...
