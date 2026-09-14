from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

from pydantic import BaseModel, Field


class Anomaly(BaseModel):
    timestamp: str
    severity: str
    message: str
    raw_context: str = Field(default="")


class LogWatcherInput(BaseModel):
    log_lines: list[str] | None = None
    log_file: str | None = None
    tail_lines: int | None = None


class LogWatcher:
    """Fast, deterministic log scanning agent using regex-based heuristics."""

    ERROR_PATTERNS = [
        re.compile(r"\bERROR\b", re.IGNORECASE),
        re.compile(r"\bCRITICAL\b", re.IGNORECASE),
        re.compile(r"Exception|Traceback|Unhandled", re.IGNORECASE),
        re.compile(r"timeout|timed out", re.IGNORECASE),
        re.compile(r"NullPointerException|Null pointer|NoneType", re.IGNORECASE),
        re.compile(r"OOM|out of memory|memory leak", re.IGNORECASE),
    ]

    LATENCY_PATTERN = re.compile(r"duration_ms|latency|response_time|request_time|elapsed.*ms|time.*ms", re.IGNORECASE)

    def __init__(self, latency_threshold_ms: int = 3000) -> None:
        self.latency_threshold_ms = latency_threshold_ms

    def watch(self, input_data: LogWatcherInput | list[str] | str | None) -> list[Anomaly]:
        """Accept a list of log lines, a file path, or a LogWatcherInput model."""
        lines = self._normalize_lines(input_data)
        return self._detect_anomalies(lines)

    def _normalize_lines(self, input_data: LogWatcherInput | list[str] | str | None) -> list[str]:
        if input_data is None:
            return []

        if isinstance(input_data, LogWatcherInput):
            if input_data.log_file:
                lines = self._read_log_file(input_data.log_file, input_data.tail_lines)
                return lines
            if input_data.log_lines:
                return input_data.log_lines
            return []

        if isinstance(input_data, str):
            path = Path(input_data)
            if path.exists():
                return self._read_log_file(str(path), None)
            return input_data.splitlines()

        if isinstance(input_data, Sequence):
            return [str(item) for item in input_data]

        raise TypeError("Unsupported log input type")

    def _read_log_file(self, file_path: str, tail_lines: int | None) -> list[str]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        with path.open("r", encoding="utf-8", errors="replace") as handle:
            all_lines = handle.read().splitlines()

        if tail_lines is not None:
            return all_lines[-tail_lines:]
        return all_lines

    def _detect_anomalies(self, lines: Iterable[str]) -> list[Anomaly]:
        anomalies: list[Anomaly] = []
        observed_lines = list(lines)

        for idx, line in enumerate(observed_lines):
            if not line.strip():
                continue

            match = self._match_line(line)
            if match is None:
                continue

            context_start = max(0, idx - 2)
            context_end = min(len(observed_lines), idx + 3)
            context = "\n".join(observed_lines[context_start:context_end])

            anomalies.append(
                Anomaly(
                    timestamp=self._extract_timestamp(line),
                    severity=match["severity"],
                    message=match["message"],
                    raw_context=context,
                )
            )

        return anomalies

    def _match_line(self, line: str) -> dict[str, str] | None:
        lowered = line.lower()

        if re.search(r"\bcritical\b|fatal|panic", line, re.IGNORECASE):
            return {"severity": "critical", "message": "Critical error condition detected"}

        if re.search(r"\berror\b|exception|traceback|unhandled", line, re.IGNORECASE):
            return {"severity": "error", "message": "Error or exception pattern detected"}

        if re.search(r"timeout|timed out|connection reset|socket hang up", line, re.IGNORECASE):
            return {"severity": "high", "message": "Timeout or connection failure detected"}

        if re.search(r"nullpointerexception|none type|null pointer|unhandled exception", line, re.IGNORECASE):
            return {"severity": "high", "message": "Null pointer / unhandled exception pattern detected"}

        if re.search(r"memory leak|oom|out of memory|gc thrash|heap usage", line, re.IGNORECASE):
            return {"severity": "warning", "message": "Memory pressure or leak pattern detected"}

        if self._has_latency_issue(line):
            return {"severity": "warning", "message": "Latency exceeds configured threshold"}

        return None

    def _has_latency_issue(self, line: str) -> bool:
        if not self.LATENCY_PATTERN.search(line):
            return False

        match = re.search(r"(\d+(?:\.\d+)?)\s*(ms|milliseconds)", line, re.IGNORECASE)
        if not match:
            return False

        value = float(match.group(1))
        return value >= self.latency_threshold_ms

    def _extract_timestamp(self, line: str) -> str:
        ts_match = re.search(r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", line)
        if ts_match:
            return ts_match.group(1)
        return "unknown"


__all__ = ["Anomaly", "LogWatcherInput", "LogWatcher"]
