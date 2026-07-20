"""Agent skill definitions used by model-backed agents."""

from dataclasses import dataclass, field


def _empty_string_dictionary() -> dict[str, str]:
    return {}


def _empty_final_detail_fields() -> dict[str, "FinalDetailField"]:
    return {}


@dataclass(frozen=True)
class FinalDetailField:
    """Field that may appear in a final decision's details."""

    description: str
    allowed_values: dict[str, str] | None = None


@dataclass(frozen=True)
class AgentSkill:
    """Vocabulary and guidance for one agent capability."""

    name: str
    goal: str
    instructions: str = ""
    claim_types: dict[str, str] = field(default_factory=_empty_string_dictionary)
    fact_types: dict[str, str] = field(default_factory=_empty_string_dictionary)
    output_types: dict[str, str] = field(default_factory=_empty_string_dictionary)
    final_detail_fields: dict[str, FinalDetailField] = field(
        default_factory=_empty_final_detail_fields
    )
