from __future__ import annotations

from pathlib import Path

from agents.log_watcher import LogWatcher


def test_log_watcher_detects_timeout() -> None:
    sample_dir = Path(__file__).resolve().parent / "data" / "sample_logs"
    watcher = LogWatcher()

    timeout_log = sample_dir / "web_db_timeout.log"
    anomalies = watcher.watch(str(timeout_log))

    assert len(anomalies) >= 2
    assert any("timeout" in anomaly.message.lower() or "timeout" in anomaly.raw_context.lower() for anomaly in anomalies)


def test_log_watcher_detects_null_pointer() -> None:
    sample_dir = Path(__file__).resolve().parent / "data" / "sample_logs"
    watcher = LogWatcher()

    null_log = sample_dir / "null_pointer.log"
    anomalies = watcher.watch(str(null_log))

    assert len(anomalies) >= 2
    assert any("null pointer" in anomaly.message.lower() or "nullpointerexception" in anomaly.raw_context.lower() for anomaly in anomalies)


def test_log_watcher_detects_memory_leak_latency() -> None:
    sample_dir = Path(__file__).resolve().parent / "data" / "sample_logs"
    watcher = LogWatcher(latency_threshold_ms=3000)

    leak_log = sample_dir / "memory_leak.log"
    anomalies = watcher.watch(str(leak_log))

    assert len(anomalies) >= 2
    assert any("latency" in anomaly.message.lower() or "memory" in anomaly.message.lower() for anomaly in anomalies)


if __name__ == "__main__":
    test_log_watcher_detects_timeout()
    test_log_watcher_detects_null_pointer()
    test_log_watcher_detects_memory_leak_latency()
    print("All Log Watcher tests passed.")
