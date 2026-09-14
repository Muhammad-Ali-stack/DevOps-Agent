from __future__ import annotations

from pathlib import Path

from agents.fix_drafting import FixDraft, FixDraftingAgent, ManualInvestigationFix
from agents.log_watcher import LogWatcher
from agents.root_cause import RootCauseAgent


def main() -> None:
    sample_path = Path(__file__).resolve().parent / "data" / "sample_logs" / "memory_leak.log"
    anomaly = LogWatcher().watch(str(sample_path))[0]
    diagnosis = RootCauseAgent(provider="gemini").analyze(anomaly)
    draft = FixDraftingAgent(provider="gemini").draft(anomaly, diagnosis)

    print("=== memory_leak.log diagnosis ===")
    print(diagnosis.model_dump_json(indent=2))
    print("=== proposed fix ===")
    print(draft.model_dump_json(indent=2))

    assert isinstance(draft, (FixDraft, ManualInvestigationFix))
    if diagnosis.suggested_fix_type in {"code", "config"}:
        assert isinstance(draft, FixDraft)
        if not draft.diff_or_snippet.strip():
            assert draft.risk_level == "high"
            print("No safe diff proposed because the log contains no source-file evidence.")
    else:
        assert isinstance(draft, ManualInvestigationFix)


if __name__ == "__main__":
    main()
