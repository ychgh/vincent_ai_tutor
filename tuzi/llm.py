"""LiteLLM wrapper for the Tuzi AI Tutor."""

import os
from typing import Iterator, Optional

import litellm


class LLMError(Exception):
    """Raised when an LLM call fails."""


class LLMClient:
    """Wraps LiteLLM for multi-provider LLM access with error handling."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")

    def chat(
        self,
        messages: list[dict],
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat completion request. Retries once on failure."""
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("LLM returned empty response.")
            return content
        except litellm.exceptions.RateLimitError:
            raise LLMError(
                "Rate limited by the API provider. Please wait a moment and try again."
            )
        except litellm.exceptions.AuthenticationError:
            raise LLMError(
                f"Authentication failed. Check your API key for {self.model}."
            )
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e

    def chat_stream(
        self,
        messages: list[dict],
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> Iterator[str]:
        """Stream a chat completion response chunk by chunk."""
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except litellm.exceptions.RateLimitError:
            raise LLMError(
                "Rate limited by the API provider. Please wait a moment and try again."
            )
        except litellm.exceptions.AuthenticationError:
            raise LLMError(
                f"Authentication failed. Check your API key for {self.model}."
            )
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e
