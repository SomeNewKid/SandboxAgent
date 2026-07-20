"""Shared vocabulary used by agents and the harness."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StateUpdateArgument:
    """Argument accepted by a state update operation."""

    name: str
    argument_type: str
    description: str


@dataclass(frozen=True)
class StateUpdateOperation:
    """State update operation available to model-backed agents."""

    description: str
    arguments: tuple[StateUpdateArgument, ...]


COMPLETION_TYPES = {
    "done": "The agent has completed the goal.",
    "blocked": (
        "The agent could not complete the goal because required information or "
        "conditions were missing."
    ),
    "handoff_request": "Another agent should continue the goal.",
    "approval_request": "Human approval is required before continuing.",
}

STATE_UPDATE_OPERATIONS = {
    "add_claim": StateUpdateOperation(
        description="Record a claim asserted by an external source.",
        arguments=(
            StateUpdateArgument(
                name="claim_type",
                argument_type="string",
                description="The structured type of claim being recorded.",
            ),
            StateUpdateArgument(
                name="data",
                argument_type="object",
                description="Structured data describing the claim and its evidence.",
            ),
        ),
    ),
    "add_fact": StateUpdateOperation(
        description="Record a verified fact supported by available evidence.",
        arguments=(
            StateUpdateArgument(
                name="fact_type",
                argument_type="string",
                description="The structured type of fact being recorded.",
            ),
            StateUpdateArgument(
                name="data",
                argument_type="object",
                description="Structured data describing the verified fact.",
            ),
        ),
    ),
    "add_output": StateUpdateOperation(
        description="Record a concrete output produced while working on the goal.",
        arguments=(
            StateUpdateArgument(
                name="output_type",
                argument_type="string",
                description="The structured type of output being recorded.",
            ),
            StateUpdateArgument(
                name="data",
                argument_type="object",
                description="Structured data describing the output.",
            ),
        ),
    ),
}
