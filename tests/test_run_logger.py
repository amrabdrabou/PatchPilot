# Verifies structured JSONL run logging.
import json

from backend.run_logger import build_run_log_record, stockholm_now_iso, write_run_log


def test_stockholm_now_iso_uses_stockholm_timezone():
    timestamp = stockholm_now_iso()

    assert timestamp.endswith("+01:00") or timestamp.endswith("+02:00")


def test_write_run_log_appends_json_line(tmp_path):
    log_file = tmp_path / "runs.jsonl"
    record = build_run_log_record(
        run_id="run-1",
        task="Inspect files",
        started_at="2026-05-11T20:00:00+02:00",
        status="final",
        final_answer="Final Answer: done",
        steps=2,
        max_steps=10,
        model_calls=2,
        tool_calls=1,
        max_tool_calls=8,
        tool_usage={"read_file": 1},
        interface="web",
    )

    write_run_log(record, log_file=log_file)

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    saved = json.loads(lines[0])
    assert saved["run_id"] == "run-1"
    assert saved["task"] == "Inspect files"
    assert saved["status"] == "final"
    assert saved["tool_usage"] == {"read_file": 1}
    assert saved["token_usage"] == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    assert saved["trace"] == []
    assert saved["interface"] == "web"
    assert "ended_at" in saved
