# Verifies streamed run lifecycle, stopping, and active-run cleanup.
import backend.agent_stream as agent_stream


def setup_function():
    agent_stream.ACTIVE_RUNS.clear()


def test_final_run_is_removed_from_active_runs(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: "Final Answer: done",
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("finish", max_steps=2))

    assert events[-1]["type"] == "final"
    assert events[-1]["content"] == "Final Answer: done"
    assert agent_stream.ACTIVE_RUNS == {}


def test_final_run_logs_token_usage_and_trace(monkeypatch):
    saved_records = []
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: {
            "content": "Final Answer: done",
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 4,
                "total_tokens": 7,
            },
        },
    )
    monkeypatch.setattr(agent_stream, "write_run_log", saved_records.append)

    events = list(agent_stream.start_agent_stream("finish", max_steps=2))

    assert events[-1]["type"] == "final"
    assert saved_records[0]["token_usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
    }
    assert [entry["type"] for entry in saved_records[0]["trace"]] == [
        "start",
        "step",
        "assistant_message",
        "final",
    ]


def test_stream_compacts_context_before_model_call(monkeypatch):
    seen_messages = []

    def fake_ask_model(messages):
        seen_messages.append(messages)
        return "Final Answer: compacted"

    monkeypatch.setattr(agent_stream, "ask_model", fake_ask_model)
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)
    monkeypatch.setattr(agent_stream, "MAX_CONTEXT_CHARS", 120)
    monkeypatch.setattr(agent_stream, "CONTEXT_KEEP_RECENT_MESSAGES", 1)
    monkeypatch.setattr(agent_stream, "MAX_CONTEXT_MESSAGE_CHARS", 40)

    list(agent_stream.start_agent_stream("x" * 200, max_steps=1))

    assert seen_messages[0][1]["content"].startswith("Context summary:")
    assert len(seen_messages[0]) <= 3


def test_step_limit_run_is_removed_from_active_runs(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: "Thought: still working",
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("loop", max_steps=1))

    assert events[-1]["type"] == "stopped"
    assert "maximum number of steps" in events[-1]["content"]
    assert agent_stream.ACTIVE_RUNS == {}


def test_step_limit_includes_best_effort_assistant_message(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: "Thought: partial useful work",
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("loop", max_steps=1))

    assert "Best effort partial answer:" in events[-1]["content"]
    assert "Thought: partial useful work" in events[-1]["content"]


def test_approval_pause_keeps_run_active(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: 'Action: edit_file("hello.py", "old", "new")',
    )

    events = list(agent_stream.start_agent_stream("edit", max_steps=2))

    assert events[-1]["type"] == "approval_required"
    assert len(agent_stream.ACTIVE_RUNS) == 1


def test_rejected_tool_run_is_removed_from_active_runs(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: 'Action: edit_file("hello.py", "old", "new")',
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("edit", max_steps=2))
    approval_event = events[-1]
    reject_events = list(
        agent_stream.reject_pending_tool(
            approval_event["run_id"],
            approval_event["approval_id"],
        )
    )

    assert reject_events[-1]["type"] == "final"
    assert agent_stream.ACTIVE_RUNS == {}


def test_rejected_tool_uses_blocked_observation(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: 'Action: edit_file("hello.py", "old", "new")',
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("edit", max_steps=2))
    approval_event = events[-1]
    reject_events = list(
        agent_stream.reject_pending_tool(
            approval_event["run_id"],
            approval_event["approval_id"],
        )
    )

    assert reject_events[1]["content"].startswith("Observation [blocked]:")


def test_stop_request_stops_and_removes_run(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: "Thought: still working",
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)
    state = agent_stream.create_run_state("stop me", max_steps=2, max_tool_calls=1)

    assert agent_stream.request_stop_run(state["run_id"]) is True

    events = list(agent_stream.run_agent_until_pause(state))

    assert events[-1]["type"] == "stopped"
    assert "user requested stop" in events[-1]["content"]
    assert agent_stream.ACTIVE_RUNS == {}


def test_stop_before_tool_execution_does_not_run_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: 'Action: read_file("README.md")',
    )
    monkeypatch.setattr(agent_stream, "run_tool", lambda *args: calls.append(args))
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    stream = agent_stream.start_agent_stream("tool", max_steps=2)

    assert next(stream)["type"] == "start"
    assert next(stream)["type"] == "step"
    assert next(stream)["type"] == "assistant_message"
    tool_call = next(stream)

    assert tool_call["type"] == "tool_call"
    agent_stream.request_stop_run(tool_call["run_id"])

    stopped_event = next(stream)

    assert stopped_event["type"] == "stopped"
    assert calls == []
    assert agent_stream.ACTIVE_RUNS == {}


def test_approved_tool_clears_pending_before_execution(monkeypatch):
    pending_seen_by_tool = []
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: 'Action: edit_file("hello.py", "old", "new")',
    )
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("edit", max_steps=2))
    approval_event = events[-1]
    state = agent_stream.ACTIVE_RUNS[approval_event["run_id"]]

    def fake_run_tool(tool_name, arguments):
        pending_seen_by_tool.append(state["pending_tool"])
        state["stop_requested"] = True
        return "edited"

    monkeypatch.setattr(agent_stream, "run_tool", fake_run_tool)

    approve_events = list(
        agent_stream.approve_pending_tool(
            approval_event["run_id"],
            approval_event["approval_id"],
        )
    )

    assert pending_seen_by_tool == [None]
    assert approve_events[-1]["type"] == "stopped"


def test_stop_after_approval_decision_does_not_run_tool(monkeypatch):
    calls = []
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: 'Action: edit_file("hello.py", "old", "new")',
    )
    monkeypatch.setattr(agent_stream, "run_tool", lambda *args: calls.append(args))
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("edit", max_steps=2))
    approval_event = events[-1]
    approval_stream = agent_stream.approve_pending_tool(
        approval_event["run_id"],
        approval_event["approval_id"],
    )
    decision_event = next(approval_stream)

    assert decision_event["type"] == "approval_decision"
    agent_stream.request_stop_run(approval_event["run_id"])

    stopped_event = next(approval_stream)

    assert stopped_event["type"] == "stopped"
    assert calls == []
    assert agent_stream.ACTIVE_RUNS == {}


def test_stop_request_reports_missing_run():
    assert agent_stream.request_stop_run("missing") is False


def test_model_error_stops_and_removes_run(monkeypatch):
    def failing_model(messages):
        raise RuntimeError("network down")

    monkeypatch.setattr(agent_stream, "ask_model", failing_model)
    monkeypatch.setattr(agent_stream, "write_run_log", lambda record: None)

    events = list(agent_stream.start_agent_stream("fail", max_steps=2))

    assert events[-2]["type"] == "error"
    assert events[-2]["content"] == "Model call failed safely: RuntimeError."
    assert events[-1]["type"] == "stopped"
    assert agent_stream.ACTIVE_RUNS == {}


def test_log_failure_does_not_break_final_run(monkeypatch):
    monkeypatch.setattr(
        agent_stream,
        "ask_model",
        lambda messages: "Final Answer: done",
    )

    def failing_log(record):
        raise OSError("log blocked")

    monkeypatch.setattr(agent_stream, "write_run_log", failing_log)

    events = list(agent_stream.start_agent_stream("finish", max_steps=2))

    assert events[-1]["type"] == "final"
    assert agent_stream.ACTIVE_RUNS == {}
