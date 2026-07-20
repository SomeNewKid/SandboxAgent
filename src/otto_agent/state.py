"""Generic goal state shared by agents and the harness."""

from dataclasses import dataclass, field
from enum import StrEnum


class GoalStatus(StrEnum):
    """Lifecycle status for an agent goal."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class EntityRef:
    """Reference to an entity involved in a goal."""

    entity_type: str
    entity_id: str


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by a tool call."""

    tool_name: str
    arguments: dict[str, object]
    data: dict[str, object]


@dataclass(frozen=True)
class Claim:
    """Validated structured claim recorded during an agent run."""

    claim_type: str
    data: dict[str, object]


@dataclass(frozen=True)
class Fact:
    """Validated structured fact recorded during an agent run."""

    fact_type: str
    data: dict[str, object]


@dataclass(frozen=True)
class GoalOutput:
    """Concrete output produced while working on a goal."""

    output_type: str
    data: dict[str, object]


@dataclass(frozen=True)
class GoalResult:
    """Structured result recorded for a goal."""

    result_type: str
    data: dict[str, object]


def _empty_entity_refs() -> list[EntityRef]:
    return []


def _empty_tool_results() -> list[ToolResult]:
    return []


def _empty_claims() -> list[Claim]:
    return []


def _empty_facts() -> list[Fact]:
    return []


def _empty_goal_outputs() -> list[GoalOutput]:
    return []


def _empty_goal_results() -> list[GoalResult]:
    return []


@dataclass
class GoalState:
    """Harness-owned state for one agent goal."""

    goal_id: str
    status: GoalStatus
    root_entity: EntityRef
    entities: list[EntityRef] = field(default_factory=_empty_entity_refs)
    tool_results: list[ToolResult] = field(default_factory=_empty_tool_results)
    claims: list[Claim] = field(default_factory=_empty_claims)
    facts: list[Fact] = field(default_factory=_empty_facts)
    outputs: list[GoalOutput] = field(default_factory=_empty_goal_outputs)
    results: list[GoalResult] = field(default_factory=_empty_goal_results)

    def __post_init__(self) -> None:
        self.set_entity_reference(self.root_entity)

    def set_entity_reference(self, entity_reference: EntityRef) -> None:
        """Set an entity reference, raising an error for conflicting values."""
        for entity in self.entities:
            if entity.entity_type != entity_reference.entity_type:
                continue

            if entity.entity_id == entity_reference.entity_id:
                return

            raise RuntimeError(
                f"Conflicting entity reference for {entity_reference.entity_type}."
            )

        self.entities.append(entity_reference)

    def add_tool_result(self, tool_result: ToolResult) -> None:
        """Add a tool result to the goal state."""
        self.tool_results.append(tool_result)

    def add_claim(
        self,
        claim_type: str,
        data: dict[str, object],
    ) -> None:
        """Add a claim to the goal state."""
        self.claims.append(
            Claim(
                claim_type=claim_type,
                data=data,
            )
        )

    def add_fact(
        self,
        fact_type: str,
        data: dict[str, object],
    ) -> None:
        """Add a fact to the goal state."""
        self.facts.append(
            Fact(
                fact_type=fact_type,
                data=data,
            )
        )

    def add_output(
        self,
        output_type: str,
        data: dict[str, object],
    ) -> None:
        """Add an output to the goal state."""
        self.outputs.append(
            GoalOutput(
                output_type=output_type,
                data=data,
            )
        )

    def add_result(
        self,
        result_type: str,
        data: dict[str, object],
    ) -> None:
        """Add a result to the goal state."""
        self.results.append(
            GoalResult(
                result_type=result_type,
                data=data,
            )
        )
