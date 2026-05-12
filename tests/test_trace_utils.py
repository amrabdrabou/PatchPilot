# Verifies shared trace formatting helpers.
from backend import trace_utils


def test_compact_content_keeps_short_text():
    """
    Short trace content is stored unchanged.
    """
    assert trace_utils.compact_content("small") == "small"


def test_compact_content_truncates_long_text():
    """
    Long trace content is capped before logs store it.
    """
    compacted = trace_utils.compact_content("x" * 600)

    assert len(compacted) < 600
    assert "... trace content truncated ..." in compacted


def test_build_trace_entry_includes_extra_fields():
    """
    Trace entries include base metadata plus optional context.
    """
    entry = trace_utils.build_trace_entry(
        3,
        "tool_call",
        "read_file",
        {"tool_name": "read_file"},
    )

    assert entry["step"] == 3
    assert entry["type"] == "tool_call"
    assert entry["content"] == "read_file"
    assert entry["tool_name"] == "read_file"
    assert entry["time"]
