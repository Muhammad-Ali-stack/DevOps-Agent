from __future__ import annotations

import json
import traceback
from typing import Any, Literal

from pydantic import BaseModel, Field

from agents.log_watcher import Anomaly
from core.llm_client import LLMClient, get_llm_client


class RootCauseDiagnosis(BaseModel):
    likely_cause: str
    confidence: Literal["high", "medium", "low"]
    explanation: str
    suggested_fix_type: Literal["code", "config", "infra", "unknown"]


class RootCauseAgent:
    """Analyze a flagged anomaly with a structured LLM response."""

    def __init__(self, llm_client: LLMClient | None = None, provider: str = "groq") -> None:
        self.llm_client = llm_client
        self.provider = provider
        self.response_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "likely_cause": {"type": "string"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "explanation": {"type": "string"},
                "suggested_fix_type": {"type": "string", "enum": ["code", "config", "infra", "unknown"]},
            },
            "required": ["likely_cause", "confidence", "explanation", "suggested_fix_type"],
            "additionalProperties": False,
        }

    def analyze(self, anomaly: Anomaly) -> RootCauseDiagnosis:
        if self.llm_client is None:
            try:
                self.llm_client = get_llm_client(self.provider)
            except ValueError:
                return RootCauseDiagnosis(
                    likely_cause="LLM unavailable; manual investigation required",
                    confidence="low",
                    explanation=(
                        "No API key is configured for the selected LLM provider, so the agent fell back to a conservative diagnosis. "
                        "Use the anomaly log context and operational evidence to determine the likely cause manually."
                    ),
                    suggested_fix_type="unknown",
                )

        system_prompt = (
            "You are a senior Site Reliability Engineer and incident responder. "
            "Diagnose the likely root cause from the provided log evidence. "
            "Return only valid JSON that matches the requested schema. "
            "Be conservative and evidence-based."
        )

        base_prompt = (
            f"Incident details:\n"
            f"- timestamp: {anomaly.timestamp}\n"
            f"- severity: {anomaly.severity}\n"
            f"- message: {anomaly.message}\n\n"
            f"Relevant log context:\n{anomaly.raw_context}\n\n"
            "Determine the most likely root cause, confidence, brief explanation, and fix type. "
            "Respond only in JSON with keys: likely_cause, confidence, explanation, suggested_fix_type."
        )

        fallback_prompt = (
            "Strict mode: produce a single JSON object only. "
            "Use the exact schema: {likely_cause: string, confidence: 'high'|'medium'|'low', explanation: string, suggested_fix_type: 'code'|'config'|'infra'|'unknown'}. "
            "Do not include markdown code fences or commentary. "
            f"Anomaly summary: {anomaly.model_dump_json(indent=2)}"
        )

        for index, prompt in enumerate([base_prompt, fallback_prompt], start=1):
            result: Any = None
            try:
                provider_name = self.provider
                model_name = getattr(self.llm_client, "model", "unknown")
                print(f"Root Cause LLM call (attempt {index}): provider={provider_name}, model={model_name}")
                result = self.llm_client.generate(
                    system_prompt,
                    prompt,
                    response_schema=self.response_schema,
                )

                parsed = self._coerce_to_dict(result)
                if self._is_valid(parsed):
                    return RootCauseDiagnosis(**parsed)
                print(f"Root Cause LLM raw result failed schema validation (attempt {index}): {result!r}")
            except Exception as exc:
                response = getattr(exc, "response", None)
                error_message = str(exc)
                api_key = getattr(self.llm_client, "api_key", None)
                if api_key:
                    error_message = error_message.replace(api_key, "[REDACTED]")
                print(f"Root Cause LLM error (attempt {index}): {type(exc).__name__}: {error_message}")
                formatted_traceback = traceback.format_exc()
                if api_key:
                    formatted_traceback = formatted_traceback.replace(api_key, "[REDACTED]")
                print(f"Root Cause LLM full traceback (attempt {index}):\n{formatted_traceback}")
                if response is not None:
                    print(f"Root Cause LLM raw response: {response.text}")
                elif result is not None:
                    print(f"Root Cause LLM raw result before parsing/validation: {result!r}")
                if index == 2:
                    break

        return RootCauseDiagnosis(
            likely_cause="Unable to determine automatically",
            confidence="low",
            explanation=(
                "The LLM request failed or returned an unparseable result, so the diagnosis is intentionally conservative. "
                "Use the raw anomaly context for manual triage."
            ),
            suggested_fix_type="unknown",
        )

    def _coerce_to_dict(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Unparseable JSON output: {result}") from exc
            if isinstance(parsed, dict):
                return parsed
        raise ValueError(f"Unexpected structured output: {result!r}")

    def _is_valid(self, payload: dict[str, Any]) -> bool:
        required = {"likely_cause", "confidence", "explanation", "suggested_fix_type"}
        if not isinstance(payload, dict):
            return False
        if not required.issubset(payload.keys()):
            return False
        if payload.get("confidence") not in {"high", "medium", "low"}:
            return False
        if payload.get("suggested_fix_type") not in {"code", "config", "infra", "unknown"}:
            return False
        return True


__all__ = ["RootCauseAgent", "RootCauseDiagnosis"]
