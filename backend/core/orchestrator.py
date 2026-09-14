from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from agents.fix_drafting import FixDraftingAgent
from agents.log_watcher import Anomaly, LogWatcher
from agents.root_cause import RootCauseAgent
from agents.test_runner import TestRunnerAgent

logger = logging.getLogger("devops_orchestrator")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


class Orchestrator:
    """Coordinator for the log watcher and root-cause analysis pipeline."""

    def __init__(self, sample_logs_dir: str | Path | None = None, provider: str = "groq") -> None:
        self.sample_logs_dir = Path(sample_logs_dir) if sample_logs_dir else Path(__file__).resolve().parent.parent / "data" / "sample_logs"
        self.log_watcher = LogWatcher()
        self.root_cause_agent = RootCauseAgent(provider=provider)
        self.fix_drafting_agent = FixDraftingAgent(provider=provider)
        self.test_runner_agent = TestRunnerAgent()

    def list_sample_logs(self) -> list[str]:
        if not self.sample_logs_dir.exists():
            return []
        return sorted(p.name for p in self.sample_logs_dir.glob("*.log"))

    def analyze_log_file(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        start = time.perf_counter()
        logger.info("Agent: Log Watcher running on %s", path)
        anomalies = self.log_watcher.watch(str(path))
        logger.info("Agent: Log Watcher completed in %.2fs with %d anomaly(s)", time.perf_counter() - start, len(anomalies))
        logger.info("Log Watcher result: %s", [a.model_dump() for a in anomalies])

        diagnoses: list[dict[str, Any]] = []
        for anomaly in anomalies:
            diag_start = time.perf_counter()
            logger.info("Agent: Root Cause Analysis running for anomaly at %s", anomaly.timestamp)
            diagnosis = self.root_cause_agent.analyze(anomaly)
            logger.info("Agent: Root Cause Analysis completed in %.2fs", time.perf_counter() - diag_start)
            logger.info("Root Cause Analysis result: %s", diagnosis.model_dump())
            fix_start = time.perf_counter()
            logger.info("Agent: Fix Drafting running for anomaly at %s", anomaly.timestamp)
            fix_draft = self.fix_drafting_agent.draft(anomaly, diagnosis)
            logger.info("Agent: Fix Drafting completed in %.2fs", time.perf_counter() - fix_start)
            logger.info("Fix Drafting result: %s", fix_draft.model_dump())
            test_start = time.perf_counter()
            logger.info("Agent: Test Runner running for anomaly at %s", anomaly.timestamp)
            test_result = self.test_runner_agent.run(fix_draft)
            logger.info("Agent: Test Runner completed in %.2fs", time.perf_counter() - test_start)
            logger.info("Test Runner result: %s", test_result.model_dump())
            diagnoses.append({
                "anomaly": anomaly.model_dump(),
                "diagnosis": diagnosis.model_dump(),
                "fix_draft": fix_draft.model_dump(),
                "test_result": test_result.model_dump(),
            })

        return {
            "anomalies": [a.model_dump() for a in anomalies],
            "diagnoses": diagnoses,
            "status": "ok",
        }

    def analyze_log_lines(self, lines: list[str]) -> dict[str, Any]:
        start = time.perf_counter()
        logger.info("Agent: Log Watcher running on inline log payload (%d lines)", len(lines))
        anomalies = self.log_watcher.watch(lines)
        logger.info("Agent: Log Watcher completed in %.2fs with %d anomaly(s)", time.perf_counter() - start, len(anomalies))
        logger.info("Log Watcher result: %s", [a.model_dump() for a in anomalies])

        diagnoses = []
        for anomaly in anomalies:
            diag_start = time.perf_counter()
            logger.info("Agent: Root Cause Analysis running for anomaly at %s", anomaly.timestamp)
            diagnosis = self.root_cause_agent.analyze(anomaly)
            logger.info("Agent: Root Cause Analysis completed in %.2fs", time.perf_counter() - diag_start)
            logger.info("Root Cause Analysis result: %s", diagnosis.model_dump())
            fix_start = time.perf_counter()
            logger.info("Agent: Fix Drafting running for anomaly at %s", anomaly.timestamp)
            fix_draft = self.fix_drafting_agent.draft(anomaly, diagnosis)
            logger.info("Agent: Fix Drafting completed in %.2fs", time.perf_counter() - fix_start)
            logger.info("Fix Drafting result: %s", fix_draft.model_dump())
            test_start = time.perf_counter()
            logger.info("Agent: Test Runner running for anomaly at %s", anomaly.timestamp)
            test_result = self.test_runner_agent.run(fix_draft)
            logger.info("Agent: Test Runner completed in %.2fs", time.perf_counter() - test_start)
            logger.info("Test Runner result: %s", test_result.model_dump())
            diagnoses.append({
                "anomaly": anomaly.model_dump(),
                "diagnosis": diagnosis.model_dump(),
                "fix_draft": fix_draft.model_dump(),
                "test_result": test_result.model_dump(),
            })

        return {
            "anomalies": [a.model_dump() for a in anomalies],
            "diagnoses": diagnoses,
            "status": "ok",
        }

    def analyze_sample(self, sample_name: str) -> dict[str, Any]:
        sample_path = self.sample_logs_dir / sample_name
        if not sample_path.exists():
            raise FileNotFoundError(f"Sample log not found: {sample_name}")
        return self.analyze_log_file(sample_path)


__all__ = ["Orchestrator"]
