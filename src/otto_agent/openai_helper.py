"""Helper functions for OpenAI clients."""

import json
from typing import cast

from openai import OpenAI

from .model import (
    ModelCallBudget,
    ModelClientRegistration,
    ModelClientRegistry,
    ModelRequest,
    ModelResponse,
)


class OpenAIClient:
    """OpenAI-backed model client."""

    def __init__(self, model: str | None = None) -> None:
        """Create the model client."""
        self._client = OpenAI()
        self._model = model or "gpt-4.1-mini"

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return a structured model response."""
        if request.response_schema is None:
            raise ValueError("OpenAIClient requires a response schema.")

        response = self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                {
                    "role": "user",
                    "content": request.user_prompt,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": request.response_schema_name,
                    "schema": request.response_schema,
                    "strict": True,
                },
            },
        )
        data = json.loads(response.output_text)
        return ModelResponse(data=cast(dict[str, object], data))


def create_openai_model_client_registry(
    max_model_calls: int = 0, model_name: str = "gpt-4.1-mini"
) -> ModelClientRegistry:
    """Create model clients for real OpenAI-backed runs."""

    return ModelClientRegistry(
        model_call_budget=ModelCallBudget(max_paid_model_calls=max_model_calls),
        clients=(
            ModelClientRegistration(
                name="openai",
                client=OpenAIClient(model=model_name),
                is_text_enabled=True,
                is_vision_enabled=True,
                is_paid=True,
            ),
        ),
    )
