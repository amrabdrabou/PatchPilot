# Builds stream event payloads and compact trace entries.
import json

from backend.run_logger import stockholm_now_iso


MAX_TRACE_CONTENT_CHARS = 500


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


def compact_content(content):
    """
    Limit trace content so run logs stay compact.
    """
    text = str(content)

    if len(text) <= MAX_TRACE_CONTENT_CHARS:
        return text

    return text[:MAX_TRACE_CONTENT_CHARS] + "\n... trace content truncated ..."


def record_trace(state, event_type, content, extra=None):
    """
    Append one compact trace entry to the run state.
    """
    entry = {
        "time": stockholm_now_iso(),
        "step": state["step"],
        "type": event_type,
        "content": compact_content(content),
    }

    if extra:
        entry.update(extra)

    state["trace"].append(entry)


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
