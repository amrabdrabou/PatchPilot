# Verifies stream event payload and trace helpers.
import json

from backend import stream_events


def test_make_event_merges_extra_fields():
    """
    Stream events include type, content, and optional metadata.
    """
    event = stream_events.make_event("step", "Step 1", {"run_id": "run-1"})

    assert event == {
        "type": "step",
        "content": "Step 1",
        "run_id": "run-1",
    }


def test_format_sse_encodes_json_event():
    """
    SSE chunks wrap one JSON event with the data prefix.
    """
    chunk = stream_events.format_sse({"type": "final", "content": "done"})

    assert chunk.startswith("data: ")
    assert chunk.endswith("\n\n")
    assert json.loads(chunk.removeprefix("data: ").strip()) == {
        "type": "final",
        "content": "done",
    }


def test_record_trace_compacts_long_content():
    """
    Long trace content is truncated before being stored in run state.
    """
    state = {"step": 2, "trace": []}

    stream_events.record_trace(state, "assistant_message", "x" * 600, {"tool_name": "read_file"})

    assert state["trace"][0]["step"] == 2
    assert state["trace"][0]["type"] == "assistant_message"
    assert state["trace"][0]["tool_name"] == "read_file"
    assert "... trace content truncated ..." in state["trace"][0]["content"]


def test_build_progress_payload_returns_counters():
    """
    Progress payloads expose only the counters used by the UI.
    """
    state = {
        "step": 1,
        "max_steps": 5,
        "model_calls": 2,
        "tool_calls": 3,
        "max_tool_calls": 4,
        "ignored": "value",
    }

    assert stream_events.build_progress_payload(state) == {
        "step": 1,
        "max_steps": 5,
        "model_calls": 2,
        "tool_calls": 3,
        "max_tool_calls": 4,
    }
