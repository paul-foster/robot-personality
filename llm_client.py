"""Ollama communication boundary for the robot personality module."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import ollama


class LLMError(RuntimeError):
    """Raised when the local language model cannot produce a response."""


class ChatCompletionClient(Protocol):
    def chat(self, *, model: str, messages: Sequence[dict[str, str]]) -> Any:
        """Return a chat completion from the configured model."""


class OllamaLLM:
    """Small adapter that keeps Ollama details out of conversation logic."""

    def __init__(
        self,
        model: str,
        host: str,
        client: ChatCompletionClient | None = None,
    ) -> None:
        self.model = model
        self._client = client or ollama.Client(host=host)

    def respond(self, messages: Sequence[dict[str, str]]) -> str:
        """Ask Ollama for one response and return normalized response text."""

        try:
            response = self._client.chat(model=self.model, messages=messages)
            content = _response_content(response)
        except ollama.ResponseError as error:
            raise LLMError(f"Ollama rejected the request: {error}") from error
        except Exception as error:
            raise LLMError(
                "Could not reach Ollama. Check that the Ollama service is running "
                f"and that model {self.model!r} is installed. Details: {error}"
            ) from error

        if not content:
            raise LLMError("Ollama returned an empty response")
        return content


def _response_content(response: Any) -> str:
    """Extract content from both current Ollama objects and mapping responses."""

    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "")
    else:
        message = getattr(response, "message", None)
        content = getattr(message, "content", "") if message is not None else ""

    return content.strip() if isinstance(content, str) else ""


__all__ = ["ChatCompletionClient", "LLMError", "OllamaLLM"]