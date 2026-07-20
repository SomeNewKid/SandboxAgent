"""AI model client contracts shared by agents and tools."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ModelRequest:
    """Request sent to an AI model."""

    system_prompt: str
    user_prompt: str
    input_data: dict[str, object]
    response_schema: dict[str, object] | None = None
    response_schema_name: str = "model_response"
    image_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ModelResponse:
    """Structured response returned by an AI model."""

    data: dict[str, object]


class ModelClient(Protocol):
    """Protocol implemented by AI model clients."""

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return a structured model response."""
        ...


@dataclass
class ModelCallBudget:
    """Tracks paid model calls for one run."""

    max_paid_model_calls: int
    paid_model_call_count: int = 0

    def record_paid_call(self) -> None:
        """Record one paid call, raising an error if the budget is exhausted."""
        if self.paid_model_call_count >= self.max_paid_model_calls:
            raise RuntimeError("Paid model call limit exceeded.")

        self.paid_model_call_count += 1


@dataclass(frozen=True)
class BudgetedModelClient:
    """Model client wrapper that enforces a paid-call budget."""

    client: ModelClient
    model_call_budget: ModelCallBudget

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Record a paid call before delegating to the wrapped client."""
        self.model_call_budget.record_paid_call()
        return self.client.complete(request)


@dataclass(frozen=True)
class ModelClientRegistration:
    """Registered model client with selection metadata."""

    name: str
    client: ModelClient
    is_text_enabled: bool
    is_vision_enabled: bool
    is_paid: bool


@dataclass(frozen=True)
class ModelClientRegistry:
    """Collection of model clients available during an agent run."""

    clients: tuple[ModelClientRegistration, ...]
    model_call_budget: ModelCallBudget | None = None

    def __post_init__(self) -> None:
        client_names: set[str] = set()

        for client in self.clients:
            if client.name in client_names:
                raise ValueError(f"Duplicate model client name: {client.name}")

            client_names.add(client.name)

    def get_by_name(self, name: str) -> ModelClient | None:
        """Return the named model client, if available."""
        for client in self.clients:
            if client.name == name:
                return self._create_client(client)

        return None

    def get_text_client(self, prefer_free: bool = True) -> ModelClient | None:
        """Return a text-capable model client, if available."""
        return self._get_client_by_capability(
            prefer_free=prefer_free,
            requires_text=True,
            requires_vision=False,
        )

    def get_vision_client(self, prefer_free: bool = True) -> ModelClient | None:
        """Return a vision-capable model client, if available."""
        return self._get_client_by_capability(
            prefer_free=prefer_free,
            requires_text=False,
            requires_vision=True,
        )

    def _get_client_by_capability(
        self,
        prefer_free: bool,
        requires_text: bool,
        requires_vision: bool,
    ) -> ModelClient | None:
        matching_clients = [
            client
            for client in self.clients
            if (not requires_text or client.is_text_enabled)
            and (not requires_vision or client.is_vision_enabled)
        ]

        if not matching_clients:
            return None

        if prefer_free:
            for client in matching_clients:
                if not client.is_paid:
                    return self._create_client(client)

        return self._create_client(matching_clients[0])

    def _create_client(self, client: ModelClientRegistration) -> ModelClient:
        if not client.is_paid:
            return client.client

        if self.model_call_budget is None:
            raise RuntimeError("Paid model client requires a model call budget.")

        return BudgetedModelClient(
            client=client.client,
            model_call_budget=self.model_call_budget,
        )
