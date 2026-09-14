from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

Provider = Literal["gemini", "groq"]


class LLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:
        """Generate a completion from the provider and return text or structured JSON."""


class _RetryableClient:
    """Shared retry logic for free-tier rate limits and transient failures."""

    max_attempts = 3
    base_delay_seconds = 1.0

    def _request_with_retry(self, request_fn, *, error_context: str) -> Any:
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return request_fn()
            except requests.HTTPError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code not in {429, 500, 502, 503, 504} or attempt == self.max_attempts:
                    raise
            except requests.RequestException as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    raise

            delay = self.base_delay_seconds * (2 ** (attempt - 1))
            time.sleep(delay)

        if last_error is not None:
            raise last_error

        raise RuntimeError(f"Request failed for {error_context}.")


class GeminiClient(_RetryableClient, LLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3.6-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/models",
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing. Set it in your environment or .env file.")

        self.model = model
        self.base_url = base_url.rstrip("/")

    def _build_payload(self, system_prompt: str, user_prompt: str, response_schema: dict[str, Any] | None) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "temperature": 0.2,
        }

        if response_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = {
                key: value for key, value in response_schema.items() if key != "additionalProperties"
            }
        else:
            generation_config["responseMimeType"] = "text/plain"

        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": generation_config,
        }

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = self._build_payload(system_prompt, user_prompt, response_schema)

        def request_fn() -> dict[str, Any]:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()

        result = self._request_with_retry(request_fn, error_context="Gemini generation")

        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected Gemini response shape: {result}") from exc

        if response_schema is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Gemini did not return valid JSON: {text}") from exc

        return text


class GroqClient(_RetryableClient, LLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openai/gpt-oss-20b",
        base_url: str = "https://api.groq.com/openai/v1/chat/completions",
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing. Set it in your environment or .env file.")

        self.model = model
        self.base_url = base_url

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        if response_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        def request_fn() -> dict[str, Any]:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()

        result = self._request_with_retry(request_fn, error_context="Groq generation")

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected Groq response shape: {result}") from exc

        if response_schema is not None:
            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Groq did not return valid JSON: {content}") from exc

        return content


def get_llm_client(provider: Provider = "gemini") -> LLMClient:
    """Return an LLM client configured for the requested provider."""
    if provider == "gemini":
        return GeminiClient()
    if provider == "groq":
        return GroqClient()

    raise ValueError(f"Unsupported provider: {provider}")


__all__ = ["LLMClient", "GeminiClient", "GroqClient", "get_llm_client"]
