"""Reusable model-backed agent implementation for AgentSkill-based agents."""

from collections.abc import Callable
from dataclasses import dataclass, field

from otto_agent.agent import AgentDecision, AgentRequest
from otto_agent.agents.model_decision import (
    agent_decision_from_model_data,
    create_model_decision_schema,
)
from otto_agent.agents.model_prompt import create_model_user_prompt
from otto_agent.agents.skill import AgentSkill
from otto_agent.agents.skill_validation import SkillVocabularyRule
from otto_agent.model import ModelClientRegistry, ModelRequest
from otto_agent.reducer import StateReducer
from otto_agent.validation import ValidationRule

InputDataFactory = Callable[[AgentRequest], dict[str, object]]


def _default_input_data_factory(request: AgentRequest) -> dict[str, object]:
    return {
        "goal_id": request.goal_state.goal_id,
        "root_entity_type": request.goal_state.root_entity.entity_type,
        "root_entity_id": request.goal_state.root_entity.entity_id,
    }


def _empty_reducers() -> list[StateReducer]:
    return []


@dataclass
class SkilledAgent:
    """Model-backed agent configured by an AgentSkill."""

    name: str
    skill: AgentSkill
    model_client_registry: ModelClientRegistry
    response_schema_name: str
    input_data_factory: InputDataFactory = _default_input_data_factory
    reducers: list[StateReducer] = field(default_factory=_empty_reducers)
    system_prompt: str = (
        "You make structured decisions for an agent harness. "
        "Return only data that matches the provided structured output schema."
    )

    def decide(self, request: AgentRequest) -> AgentDecision:
        """Propose the next step for the harness."""
        model_client = self.model_client_registry.get_text_client()

        if model_client is None:
            raise RuntimeError(
                f"Agent '{self.name}' requires a text model client, "
                "but no text-capable model client was registered."
            )

        model_request = ModelRequest(
            system_prompt=self.system_prompt,
            user_prompt=create_model_user_prompt(
                skill=self.skill,
                goal_state=request.goal_state,
                tool_registry=request.tool_registry,
            ),
            input_data=self.input_data_factory(request),
            response_schema=create_model_decision_schema(
                tool_registry=request.tool_registry,
                skill=self.skill,
            ),
            response_schema_name=self.response_schema_name,
        )

        model_response = model_client.complete(model_request)
        return agent_decision_from_model_data(model_response.data)

    def get_validation_rules(self) -> list[ValidationRule]:
        """Return validation rules specific to this agent."""
        return [SkillVocabularyRule(self.skill)]

    def get_state_reducers(self) -> list[StateReducer]:
        """Return reducers used by this agent to update goal state."""
        return self.reducers
