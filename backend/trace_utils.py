# Builds compact trace entries for CLI and web run logs.
from backend.run_logger import stockholm_now_iso


MAX_TRACE_CONTENT_CHARS = 500


def compact_content(content):
    """
    Limit trace content so run logs stay compact.
    """
    text = str(content)

    if len(text) <= MAX_TRACE_CONTENT_CHARS:
        return text

    return text[:MAX_TRACE_CONTENT_CHARS] + "\n... trace content truncated ..."


def build_trace_entry(step, event_type, content, extra=None):
    """
    Build one compact trace entry with Stockholm-local timestamp metadata.
    """
    entry = {
        "time": stockholm_now_iso(),
        "step": step,
        "type": event_type,
        "content": compact_content(content),
    }

    if extra:
        entry.update(extra)

    return entry
