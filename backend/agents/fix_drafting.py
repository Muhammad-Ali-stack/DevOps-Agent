from __future__ import annotations

import json
import traceback
from typing import Any, Literal

from pydantic import BaseModel

from agents.log_watcher import Anomaly
from agents.root_cause import RootCauseDiagnosis
from core.llm_client import LLMClient, get_llm_client


class FixDraft(BaseModel):
    fix_type: Literal["code", "config"]
    file_hint: str
    diff_or_snippet: str
    explanation: str
    risk_level: Literal["low", "medium", "high"]


class ManualInvestigationFix(BaseModel):
    fix_type: Literal["manual"] = "manual"
    file_hint: str = ""
    diff_or_snippet: str = ""
    explanation: str = "Manual investigation required; no safe code or configuration fix was drafted."
    risk_level: Literal["low", "medium", "high"] = "high"


class FixDraftingAgent:
    """Draft a focused code or configuration fix from an anomaly diagnosis."""

    def __init__(self, llm_client: LLMClient | None = None, provider: str = "groq") -> None:
        self.llm_client = llm_client
        self.provider = provider
        self.response_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "fix_type": {"type": "string", "enum": ["code", "config"]},
                "file_hint": {"type": "string"},
                "diff_or_snippet": {"type": "string"},
                "explanation": {"type": "string"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["fix_type", "file_hint", "diff_or_snippet", "explanation", "risk_level"],
            "additionalProperties": False,
        }

    def draft(self, anomaly: Anomaly, diagnosis: RootCauseDiagnosis) -> FixDraft | ManualInvestigationFix:
        if diagnosis.suggested_fix_type not in {"code", "config"}:
            return ManualInvestigationFix()

        if self.llm_client is None:
            try:
                self.llm_client = get_llm_client(self.provider)
            except ValueError:
                return ManualInvestigationFix(
                    explanation="LLM unavailable; manual investigation required before proposing a fix.",
                )

        system_prompt = (
            "You are a senior SRE preparing a small, reviewable remediation proposal. "
            "Use only the supplied evidence. Never invent files, APIs, or line numbers. "
            "If the evidence is insufficient, return a high-risk proposal that explicitly says more investigation is needed. "
            "Return only valid JSON matching the requested schema."
        )
        base_prompt = self._build_prompt(anomaly, diagnosis)
        strict_prompt = (
            "Strict mode: return exactly one JSON object and no markdown fences. "
            "For code fixes, diff_or_snippet must be a focused unified diff, not a full file rewrite. "
            "For config fixes, provide only the relevant config snippet. "
            f"{base_prompt}"
        )

        for attempt, prompt in enumerate((base_prompt, strict_prompt), start=1):
            result: Any = None
            try:
                model_name = getattr(self.llm_client, "model", "unknown")
                print(f"Fix Drafting LLM call (attempt {attempt}): provider={self.provider}, model={model_name}")
                result = self.llm_client.generate(
                    system_prompt,
                    prompt,
                    response_schema=self.response_schema,
                )
                print(f"Fix Drafting raw LLM response (attempt {attempt}): {result!r}")
                parsed = self._coerce_to_dict(result)
                validation_error = self._schema_validation_error(parsed, diagnosis.suggested_fix_type)
                if validation_error is None:
                    return FixDraft(**parsed)
                print(f"Fix Drafting schema validation error (attempt {attempt}): {validation_error}")
            except Exception as exc:
                response = getattr(exc, "response", None)
                api_key = getattr(self.llm_client, "api_key", None)
                error_message = str(exc)
                if api_key:
                    error_message = error_message.replace(api_key, "[REDACTED]")
                print(f"Fix Drafting exception (attempt {attempt}): {type(exc).__name__}: {error_message}")
                formatted_traceback = traceback.format_exc()
                if api_key:
                    formatted_traceback = formatted_traceback.replace(api_key, "[REDACTED]")
                print(f"Fix Drafting full traceback (attempt {attempt}):\n{formatted_traceback}")
                if response is not None:
                    print(f"Fix Drafting raw HTTP response (attempt {attempt}): {response.text}")
                elif result is not None:
                    print(f"Fix Drafting raw result before parsing (attempt {attempt}): {result!r}")
                continue

        return ManualInvestigationFix(
            explanation="The fix draft could not be validated safely; manual investigation is required.",
        )

    def _build_prompt(self, anomaly: Anomaly, diagnosis: RootCauseDiagnosis) -> str:
        return (
            "Incident evidence:\n"
            f"- timestamp: {anomaly.timestamp}\n"
            f"- severity: {anomaly.severity}\n"
            f"- message: {anomaly.message}\n"
            f"- raw context:\n{anomaly.raw_context}\n\n"
            "Root-cause diagnosis:\n"
            f"{diagnosis.model_dump_json(indent=2)}\n\n"
            f"Draft only a {diagnosis.suggested_fix_type} fix. "
            "Set risk_level to high if the evidence does not support a confident change. "
            "Return fix_type, file_hint, diff_or_snippet, explanation, and risk_level."
        )

    def _coerce_to_dict(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return parsed
        raise ValueError(f"Unexpected structured output: {result!r}")

    def _schema_validation_error(self, payload: dict[str, Any], expected_type: str) -> str | None:
        required = {"fix_type", "file_hint", "diff_or_snippet", "explanation", "risk_level"}
        missing = sorted(required - payload.keys())
        if missing:
            return f"missing required fields: {missing}"
        if payload.get("fix_type") != expected_type:
            return f"fix_type={payload.get('fix_type')!r} does not match expected {expected_type!r}"
        if payload.get("risk_level") not in {"low", "medium", "high"}:
            return f"risk_level={payload.get('risk_level')!r} is not one of 'low', 'medium', or 'high'"
        invalid_types = sorted(key for key in required if not isinstance(payload.get(key), str))
        if invalid_types:
            return f"fields must be strings: {invalid_types}"
        return None

    def _is_valid(self, payload: dict[str, Any], expected_type: str) -> bool:
        return self._schema_validation_error(payload, expected_type) is None


__all__ = ["FixDraft", "FixDraftingAgent", "ManualInvestigationFix"]
