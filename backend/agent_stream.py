# Runs the streaming ReAct loop used by the web UI.
from backend.model_client import ask_model_result as ask_model
from backend.model_results import (
    add_token_usage,
    build_observation,
    build_stopped_answer,
    normalize_model_result,
)
from backend.config import (
    CONTEXT_KEEP_RECENT_MESSAGES,
    MAX_CONTEXT_CHARS,
    MAX_CONTEXT_MESSAGE_CHARS,
)
from backend.context_window import compact_messages_for_context
from backend.parser import is_final_answer, parse_action
from backend.run_logger import build_run_log_record, write_run_log
from backend.run_state import (
    ACTIVE_RUNS,
    cleanup_run,
    clear_pending_tool,
    create_pending_tool,
    create_run_state,
    get_run_state,
    request_run_stop,
)
from backend.stream_events import (
    build_progress_payload,
    make_event,
    record_trace,
)
from backend.tool_registry import run_tool


APPROVAL_REQUIRED_TOOLS = {
    "run_bash",
    "edit_file",
}


def log_stream_run(state, status, final_answer):
    """
    Write a structured log entry for a completed stream run.
    """
    try:
        write_run_log(
            build_run_log_record(
                run_id=state["run_id"],
                task=state["task"],
                started_at=state["started_at"],
                status=status,
                final_answer=final_answer,
                steps=state["step"],
                max_steps=state["max_steps"],
                model_calls=state["model_calls"],
                tool_calls=state["tool_calls"],
                max_tool_calls=state["max_tool_calls"],
                tool_usage=state["tool_usage"],
                token_usage=state["token_usage"],
                trace=state["trace"],
                interface="web",
            )
        )
    except Exception:
        pass


def fail_run_safely(state, message):
    """
    Finish a run after an unexpected runtime error.
    """
    run_id = state["run_id"]
    state["finished"] = True
    clear_pending_tool(state)
    record_trace(state, "error", message)
    record_trace(state, "stopped", "Agent stopped because an internal error was handled safely.")
    log_stream_run(state, "error", message)
    cleanup_run(run_id)

    yield make_event(
        "error",
        message,
        {
            "run_id": run_id,
            **build_progress_payload(state),
        },
    )

    yield make_event(
        "stopped",
        "Agent stopped because an internal error was handled safely.",
        {
            "run_id": run_id,
            **build_progress_payload(state),
            "tool_usage": state["tool_usage"],
        },
    )


def stop_run_safely(state):
    """
    Finish a run that has received a user stop request.
    """
    run_id = state["run_id"]
    state["finished"] = True
    clear_pending_tool(state)
    final_answer = build_stopped_answer(
        state["messages"],
        "Agent stopped because the user requested stop.",
    )
    record_trace(state, "stopped", final_answer)
    log_stream_run(state, "stopped", final_answer)
    cleanup_run(run_id)

    yield make_event(
        "stopped",
        final_answer,
        {
            "run_id": run_id,
            **build_progress_payload(state),
            "tool_usage": state["tool_usage"],
        },
    )


def run_agent_until_pause(state):
    """
    Advance a run until it finishes, pauses for approval, or reaches a limit.
    """

    run_id = state["run_id"]

    while state["step"] < state["max_steps"]:
        if state.get("stop_requested"):
            yield from stop_run_safely(state)
            return

        state["step"] += 1

        yield make_event(
            "step",
            f"Step {state['step']}",
            {
                "run_id": run_id,
                **build_progress_payload(state),
            },
        )
        record_trace(state, "step", f"Step {state['step']}")

        try:
            state["messages"], compacted_count = compact_messages_for_context(
                state["messages"],
                MAX_CONTEXT_CHARS,
                CONTEXT_KEEP_RECENT_MESSAGES,
                MAX_CONTEXT_MESSAGE_CHARS,
            )

            if compacted_count:
                record_trace(
                    state,
                    "context_compaction",
                    f"Compacted {compacted_count} older messages before model call.",
                )

            assistant_message, usage = normalize_model_result(ask_model(state["messages"]))
            add_token_usage(state["token_usage"], usage)
            state["model_calls"] += 1
        except Exception as error:
            message = f"Model call failed safely: {type(error).__name__}."
            yield from fail_run_safely(state, message)
            return

        if state.get("stop_requested"):
            yield from stop_run_safely(state)
            return

        yield make_event(
            "assistant_message",
            assistant_message,
            {
                "run_id": run_id,
                **build_progress_payload(state),
            },
        )
        record_trace(state, "assistant_message", assistant_message)

        state["messages"].append({
            "role": "assistant",
            "content": assistant_message,
        })

        if is_final_answer(assistant_message):
            state["finished"] = True
            record_trace(state, "final", assistant_message)
            log_stream_run(state, "final", assistant_message)
            cleanup_run(run_id)

            yield make_event(
                "final",
                assistant_message,
                {
                    "run_id": run_id,
                    **build_progress_payload(state),
                    "tool_usage": state["tool_usage"],
                },
            )
            return

        action = parse_action(assistant_message)

        if action is None:
            observation = (
                'Error: No valid action found. '
                'Use format: Action: tool_name("argument")'
            )

            yield make_event(
                "error",
                observation,
                {
                    "run_id": run_id,
                    **build_progress_payload(state),
                },
            )
            record_trace(state, "error", observation)

            state["messages"].append({
                "role": "user",
                "content": observation,
            })

            continue

        tool_name, arguments = action

        if state["tool_calls"] >= state["max_tool_calls"]:
            observation = (
                "Error: Tool call limit reached. "
                "You must now give a Final Answer."
            )

            yield make_event(
                "error",
                observation,
                {
                    "run_id": run_id,
                    **build_progress_payload(state),
                },
            )
            record_trace(state, "error", observation)

            state["messages"].append({
                "role": "user",
                "content": observation,
            })

            continue

        yield make_event(
            "tool_call",
            f"{tool_name}({arguments})",
            {
                "run_id": run_id,
                "tool_name": tool_name,
                "arguments": arguments,
                **build_progress_payload(state),
            },
        )
        record_trace(
            state,
            "tool_call",
            f"{tool_name}({arguments})",
            {"tool_name": tool_name},
        )

        if tool_name in APPROVAL_REQUIRED_TOOLS:
            pending_tool = create_pending_tool(state, tool_name, arguments)

            yield make_event(
                "approval_required",
                f"Tool '{tool_name}' requires approval before it can run.",
                {
                    "run_id": run_id,
                    "approval_id": pending_tool["approval_id"],
                    "tool_name": tool_name,
                    "arguments": arguments,
                    **build_progress_payload(state),
                },
            )
            record_trace(
                state,
                "approval_required",
                f"Tool '{tool_name}' requires approval before it can run.",
                {"tool_name": tool_name},
            )

            return

        if state.get("stop_requested"):
            yield from stop_run_safely(state)
            return

        try:
            result = run_tool(tool_name, arguments)
        except Exception as error:
            message = f"Tool execution failed safely: {type(error).__name__}."
            yield from fail_run_safely(state, message)
            return

        state["tool_calls"] += 1
        state["tool_usage"][tool_name] = state["tool_usage"].get(tool_name, 0) + 1

        observation = build_observation(result)

        yield make_event(
            "observation",
            observation,
            {
                "run_id": run_id,
                **build_progress_payload(state),
            },
        )
        record_trace(state, "observation", observation)

        state["messages"].append({
            "role": "user",
            "content": observation,
        })

    state["finished"] = True
    stopped_answer = build_stopped_answer(
        state["messages"],
        "Agent stopped because it reached the maximum number of steps.",
    )
    record_trace(state, "stopped", stopped_answer)
    log_stream_run(
        state,
        "stopped",
        stopped_answer,
    )
    cleanup_run(run_id)

    yield make_event(
        "stopped",
        stopped_answer,
        {
            "run_id": run_id,
            **build_progress_payload(state),
            "tool_usage": state["tool_usage"],
        },
    )


def start_agent_stream(user_task, max_steps=5, max_tool_calls=3):
    """
    Start a new streamed agent run and yield its events.
    """
    state = create_run_state(
        user_task,
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
    )

    yield make_event(
        "start",
        "Agent started.",
        {
            "run_id": state["run_id"],
            "task": user_task,
            **build_progress_payload(state),
        },
    )
    record_trace(state, "start", "Agent started.")

    yield from run_agent_until_pause(state)


def approve_pending_tool(run_id, approval_id):
    """
    Run an approved pending tool call and continue the stream.
    """
    state = get_run_state(run_id)

    if state is None:
        yield make_event("error", "Run not found.")
        return

    if state.get("stop_requested"):
        yield from stop_run_safely(state)
        return

    pending_tool = state.get("pending_tool")

    if pending_tool is None:
        yield make_event("error", "No pending tool approval found.")
        return

    if pending_tool["approval_id"] != approval_id:
        yield make_event("error", "Approval ID does not match pending tool.")
        return

    tool_name = pending_tool["tool_name"]
    arguments = pending_tool["arguments"]

    yield make_event(
        "approval_decision",
        f"Approved tool call: {tool_name}({arguments})",
        {
            "run_id": run_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "approved": True,
            **build_progress_payload(state),
        },
    )
    record_trace(
        state,
        "approval_decision",
        f"Approved tool call: {tool_name}({arguments})",
        {"tool_name": tool_name, "approved": True},
    )

    clear_pending_tool(state)

    if state.get("stop_requested"):
        yield from stop_run_safely(state)
        return

    try:
        result = run_tool(tool_name, arguments)
    except Exception as error:
        message = f"Tool execution failed safely: {type(error).__name__}."
        yield from fail_run_safely(state, message)
        return

    state["tool_calls"] += 1
    state["tool_usage"][tool_name] = state["tool_usage"].get(tool_name, 0) + 1

    observation = build_observation(result)

    yield make_event(
        "observation",
        observation,
        {
            "run_id": run_id,
            **build_progress_payload(state),
        },
    )
    record_trace(state, "observation", observation)

    state["messages"].append({
        "role": "user",
        "content": observation,
    })

    yield from run_agent_until_pause(state)


def reject_pending_tool(run_id, approval_id):
    """
    Reject a pending tool call and finish the run safely.
    """
    state = get_run_state(run_id)

    if state is None:
        yield make_event("error", "Run not found.")
        return

    if state.get("stop_requested"):
        yield from stop_run_safely(state)
        return

    pending_tool = state.get("pending_tool")

    if pending_tool is None:
        yield make_event("error", "No pending tool approval found.")
        return

    if pending_tool["approval_id"] != approval_id:
        yield make_event("error", "Approval ID does not match pending tool.")
        return

    tool_name = pending_tool["tool_name"]
    arguments = pending_tool["arguments"]

    clear_pending_tool(state)

    observation = build_observation(f"User rejected tool call: {tool_name}({arguments})")

    yield make_event(
        "approval_decision",
        f"Rejected tool call: {tool_name}({arguments})",
        {
            "run_id": run_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "approved": False,
            **build_progress_payload(state),
        },
    )
    record_trace(
        state,
        "approval_decision",
        f"Rejected tool call: {tool_name}({arguments})",
        {"tool_name": tool_name, "approved": False},
    )

    yield make_event(
        "observation",
        observation,
        {
            "run_id": run_id,
            **build_progress_payload(state),
        },
    )
    record_trace(state, "observation", observation)

    state["messages"].append({
        "role": "user",
        "content": observation,
    })

    state["finished"] = True
    final_answer = (
        "Final Answer: The requested tool action was rejected by the user, "
        "so I did not perform it. No files or commands were changed."
    )
    record_trace(state, "final", final_answer)
    log_stream_run(state, "rejected", final_answer)
    cleanup_run(run_id)

    yield make_event(
        "final",
        final_answer,
        {
            "run_id": run_id,
            **build_progress_payload(state),
            "tool_usage": state["tool_usage"],
        },
    )


def request_stop_run(run_id):
    """
    Mark an active run so the stream loop stops at the next safe checkpoint.
    """
    return request_run_stop(run_id)
