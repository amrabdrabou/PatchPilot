# Owns mutable state for streamed PatchPilot runs.
import uuid

from backend.prompts import build_system_prompt
from backend.run_logger import stockholm_now_iso


ACTIVE_RUNS = {}


def create_run_state(user_task, max_steps=5, max_tool_calls=3):
    """
    Create and store the mutable state for one agent run.
    """
    run_id = str(uuid.uuid4())

    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "task": user_task,
        "started_at": stockholm_now_iso(),
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_task},
        ],
        "step": 0,
        "max_steps": max_steps,
        "max_tool_calls": max_tool_calls,
        "model_calls": 0,
        "tool_calls": 0,
        "tool_usage": {},
        "token_usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "trace": [],
        "pending_tool": None,
        "finished": False,
        "stop_requested": False,
    }

    return ACTIVE_RUNS[run_id]


def get_run_state(run_id):
    """
    Return one active run state by id.
    """
    return ACTIVE_RUNS.get(run_id)


def cleanup_run(run_id):
    """
    Remove a terminal run from the active-run registry.
    """
    ACTIVE_RUNS.pop(run_id, None)


def create_pending_tool(state, tool_name, arguments):
    """
    Store one pending approval request on a run and return it.
    """
    pending_tool = {
        "approval_id": str(uuid.uuid4()),
        "tool_name": tool_name,
        "arguments": arguments,
    }

    state["pending_tool"] = pending_tool

    return pending_tool


def clear_pending_tool(state):
    """
    Remove any pending approval request from a run.
    """
    state["pending_tool"] = None


def request_run_stop(run_id):
    """
    Mark an active run so the loop stops at the next safe checkpoint.
    """
    state = get_run_state(run_id)

    if state is None:
        return False

    state["stop_requested"] = True
    clear_pending_tool(state)

    if state.get("finished"):
        cleanup_run(run_id)

    return True
