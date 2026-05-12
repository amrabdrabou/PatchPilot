# Verifies active streamed-run state management.
from backend import run_state


def setup_function():
    """
    Start each test with no active web runs.
    """
    run_state.ACTIVE_RUNS.clear()


def test_create_run_state_registers_expected_defaults():
    """
    New run state includes counters, prompt messages, and cleanup metadata.
    """
    state = run_state.create_run_state("inspect files", max_steps=4, max_tool_calls=2)

    assert run_state.get_run_state(state["run_id"]) is state
    assert state["task"] == "inspect files"
    assert state["max_steps"] == 4
    assert state["max_tool_calls"] == 2
    assert state["step"] == 0
    assert state["tool_calls"] == 0
    assert state["pending_tool"] is None
    assert state["stop_requested"] is False
    assert state["messages"][0]["role"] == "system"
    assert state["messages"][1] == {"role": "user", "content": "inspect files"}


def test_request_run_stop_marks_active_run_and_clears_pending_tool():
    """
    Stop requests clear pending approvals before the loop reaches the next checkpoint.
    """
    state = run_state.create_run_state("run command")
    state["pending_tool"] = {"approval_id": "approval-1"}

    assert run_state.request_run_stop(state["run_id"]) is True

    assert state["stop_requested"] is True
    assert state["pending_tool"] is None


def test_create_pending_tool_stores_approval_details():
    """
    Pending approval details stay in run state until approval, rejection, or stop.
    """
    state = run_state.create_run_state("edit file")

    pending_tool = run_state.create_pending_tool(
        state,
        "edit_file",
        ["hello.py", "old", "new"],
    )

    assert pending_tool["approval_id"]
    assert pending_tool["tool_name"] == "edit_file"
    assert pending_tool["arguments"] == ["hello.py", "old", "new"]
    assert state["pending_tool"] is pending_tool


def test_request_run_stop_cleans_finished_runs():
    """
    A stop request for a finished run removes stale state immediately.
    """
    state = run_state.create_run_state("done")
    state["finished"] = True

    assert run_state.request_run_stop(state["run_id"]) is True

    assert run_state.get_run_state(state["run_id"]) is None


def test_cleanup_run_ignores_missing_ids():
    """
    Cleanup is safe to call for already-removed runs.
    """
    run_state.cleanup_run("missing-run")

    assert run_state.ACTIVE_RUNS == {}
