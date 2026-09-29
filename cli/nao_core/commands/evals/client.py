from dataclasses import dataclass, field
from typing import Any

import httpx

from nao_core.commands.test.runner import ModelConfig

DEFAULT_TIMEOUT_SECONDS = 300.0


@dataclass
class AgentAnswer:
    """The agent's final answer plus the context it pulled while producing it."""

    text: str
    model: str
    tool_results: list[dict] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    duration_ms: int | None = None


class AgentTimeoutError(Exception):
    pass


class AgentBackendError(Exception):
    pass


class EvalsClient:
    """Runs one eval input through the backend's non-persisting agent route."""

    def __init__(self, http_client: httpx.Client, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self._http_client = http_client
        self._timeout = timeout

    def ask(self, input: str, model: ModelConfig | None) -> AgentAnswer:
        payload: dict[str, Any] = {"input": input}
        if model:
            payload["model"] = {"provider": model.provider, "modelId": model.model_id}

        try:
            response = self._http_client.post("/api/evals/chat", json=payload, timeout=self._timeout)
        except httpx.TimeoutException as e:
            raise AgentTimeoutError(f"Agent did not answer within {self._timeout:g}s") from e
        except httpx.HTTPError as e:
            raise AgentBackendError(str(e)) from e

        if response.status_code != 200:
            raise AgentBackendError(f"{response.status_code} {response.text}")

        return _parse_answer(response.json())


def _parse_answer(data: dict) -> AgentAnswer:
    model = data.get("model") or {}
    return AgentAnswer(
        text=data["text"],
        model=f"{model.get('provider')}:{model.get('modelId')}",
        tool_results=data.get("tool_results", []),
        usage=data.get("usage"),
        cost=data.get("cost"),
        duration_ms=data.get("duration_ms"),
    )
