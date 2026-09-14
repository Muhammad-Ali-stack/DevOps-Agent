from __future__ import annotations

from pathlib import Path

from agents.log_watcher import LogWatcher
from agents.root_cause import RootCauseAgent


def main() -> None:
    sample_dir = Path(__file__).resolve().parent / "data" / "sample_logs"
    watcher = LogWatcher()
    agent = RootCauseAgent(provider="gemini")

    for log_path in [
        sample_dir / "web_db_timeout.log",
        sample_dir / "null_pointer.log",
        sample_dir / "memory_leak.log",
    ]:
        anomalies = watcher.watch(str(log_path))
        if not anomalies:
            print(f"{log_path.name}: no anomalies detected")
            continue

        anomaly = anomalies[0]
        diagnosis = agent.analyze(anomaly)
        print(f"\n=== {log_path.name} ===")
        print(diagnosis.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
