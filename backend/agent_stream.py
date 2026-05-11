import json
import uuid

from backend.model_client import ask_model
from backend.parser import parse_action
from backend.prompts import build_system_prompt
from backend.tool_registry import run_tool


APPROVAL_REQUIRED_TOOLS = {
    "run_bash",
    "edit_file",
}

ACTIVE_RUNS = {}


def build_progress_payload(state):
    return {
        "step": state["step"],
        "max_steps": state["max_steps"],
        "model_calls": state["model_calls"],
        "tool_calls": state["tool_calls"],
        "max_tool_calls": state["max_tool_calls"],
    }


def make_event(event_type, content, extra=None):
    data = {
        "type": event_type,
        "content": content,
    }

    if extra:
        data.update(extra)

    return data


def format_sse(data):
    return f"data: {json.dumps(data)}\n\n"


def create_run_state(user_task, max_steps=5, max_tool_calls=3):
    run_id = str(uuid.uuid4())

    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
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
        "pending_tool": None,
        "finished": False,
    }

    return ACTIVE_RUNS[run_id]


def run_agent_until_pause(state):
    """
    Runs the agent until:
    - it reaches a final answer
    - it needs frontend approval
    - it reaches max steps
    """

    run_id = state["run_id"]

    while state["step"] < state["max_steps"]:
        state["step"] += 1

        yield make_event(
            "step",
            f"Step {state['step']}",
            {
                "run_id": run_id,
                **build_progress_payload(state),
            },
        )

        assistant_message = ask_model(state["messages"])
        state["model_calls"] += 1

        yield make_event(
            "assistant_message",
            assistant_message,
            {
                "run_id": run_id,
                **build_progress_payload(state),
            },
        )

        state["messages"].append({
            "role": "assistant",
            "content": assistant_message,
        })

        if "Final Answer:" in assistant_message:
            state["finished"] = True

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

        if tool_name in APPROVAL_REQUIRED_TOOLS:
            approval_id = str(uuid.uuid4())

            state["pending_tool"] = {
                "approval_id": approval_id,
                "tool_name": tool_name,
                "arguments": arguments,
            }

            yield make_event(
                "approval_required",
                f"Tool '{tool_name}' requires approval before it can run.",
                {
                    "run_id": run_id,
                    "approval_id": approval_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    **build_progress_payload(state),
                },
            )

            return

        result = run_tool(tool_name, arguments)

        state["tool_calls"] += 1
        state["tool_usage"][tool_name] = state["tool_usage"].get(tool_name, 0) + 1

        observation = f"Observation: {result}"

        yield make_event(
            "observation",
            observation,
            {
                "run_id": run_id,
                **build_progress_payload(state),
            },
        )

        state["messages"].append({
            "role": "user",
            "content": observation,
        })

    state["finished"] = True

    yield make_event(
        "stopped",
        "Agent stopped because it reached the maximum number of steps.",
        {
            "run_id": run_id,
            **build_progress_payload(state),
            "tool_usage": state["tool_usage"],
        },
    )


def start_agent_stream(user_task, max_steps=5, max_tool_calls=3):
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

    yield from run_agent_until_pause(state)


def approve_pending_tool(run_id, approval_id):
    state = ACTIVE_RUNS.get(run_id)

    if state is None:
        yield make_event("error", "Run not found.")
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

    result = run_tool(tool_name, arguments)

    state["tool_calls"] += 1
    state["tool_usage"][tool_name] = state["tool_usage"].get(tool_name, 0) + 1
    state["pending_tool"] = None

    observation = f"Observation: {result}"

    yield make_event(
        "observation",
        observation,
        {
            "run_id": run_id,
            **build_progress_payload(state),
        },
    )

    state["messages"].append({
        "role": "user",
        "content": observation,
    })

    yield from run_agent_until_pause(state)


def reject_pending_tool(run_id, approval_id):
    state = ACTIVE_RUNS.get(run_id)

    if state is None:
        yield make_event("error", "Run not found.")
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

    state["pending_tool"] = None

    observation = (
        f"Observation: User rejected tool call: "
        f"{tool_name}({arguments})"
    )

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

    yield make_event(
        "observation",
        observation,
        {
            "run_id": run_id,
            **build_progress_payload(state),
        },
    )

    state["messages"].append({
        "role": "user",
        "content": observation,
    })

    state["finished"] = True

    yield make_event(
        "final",
        (
            "Final Answer: The requested tool action was rejected by the user, "
            "so I did not perform it. No files or commands were changed."
        ),
        {
            "run_id": run_id,
            **build_progress_payload(state),
            "tool_usage": state["tool_usage"],
        },
    )
