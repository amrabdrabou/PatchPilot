# Builds stream event payloads and compact trace entries.
import json

from backend.trace_utils import build_trace_entry


def build_progress_payload(state):
    """
    Return progress counters for stream events.
    """
    return {
        "step": state["step"],
        "max_steps": state["max_steps"],
        "model_calls": state["model_calls"],
        "tool_calls": state["tool_calls"],
        "max_tool_calls": state["max_tool_calls"],
    }


def record_trace(state, event_type, content, extra=None):
    """
    Append one compact trace entry to the run state.
    """
    state["trace"].append(build_trace_entry(state["step"], event_type, content, extra))


def make_event(event_type, content, extra=None):
    """
    Build one typed event payload for the frontend stream.
    """
    data = {
        "type": event_type,
        "content": content,
    }

    if extra:
        data.update(extra)

    return data


def format_sse(data):
    """
    Encode an event payload as a server-sent event chunk.
    """
    return f"data: {json.dumps(data)}\n\n"
