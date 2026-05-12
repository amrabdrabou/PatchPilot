# Verifies deterministic context-window compaction.
from backend import context_window


def test_compact_messages_returns_original_when_under_budget():
    """
    Small histories are passed through unchanged.
    """
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "short"},
    ]

    compacted, omitted_count = context_window.compact_messages_for_context(
        messages,
        max_chars=100,
        keep_recent_messages=4,
        max_message_chars=50,
    )

    assert compacted is messages
    assert omitted_count == 0


def test_compact_messages_preserves_system_and_recent_messages():
    """
    Over-budget histories keep system context and the recent conversation tail.
    """
    messages = [
        {"role": "system", "content": "system rules"},
        {"role": "user", "content": "old user " * 20},
        {"role": "assistant", "content": "old assistant " * 20},
        {"role": "user", "content": "recent user"},
        {"role": "assistant", "content": "recent assistant"},
    ]

    compacted, omitted_count = context_window.compact_messages_for_context(
        messages,
        max_chars=120,
        keep_recent_messages=2,
        max_message_chars=50,
    )

    assert compacted[0] == {"role": "system", "content": "system rules"}
    assert compacted[1]["role"] == "user"
    assert compacted[1]["content"].startswith(context_window.CONTEXT_SUMMARY_PREFIX)
    assert compacted[-2:] == messages[-2:]
    assert omitted_count == 2


def test_compact_messages_truncates_large_recent_message():
    """
    Large recent messages are visibly truncated before the model call.
    """
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "old" * 50},
        {"role": "assistant", "content": "x" * 200},
    ]

    compacted, omitted_count = context_window.compact_messages_for_context(
        messages,
        max_chars=120,
        keep_recent_messages=1,
        max_message_chars=40,
    )

    assert omitted_count == 1
    assert "... context message truncated ..." in compacted[-1]["content"]
    assert len(compacted[-1]["content"]) <= 40


def test_compact_messages_handles_zero_recent_messages():
    """
    Keeping no recent messages produces only system plus compaction summary.
    """
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "older"},
    ]

    compacted, omitted_count = context_window.compact_messages_for_context(
        messages,
        max_chars=20,
        keep_recent_messages=0,
        max_message_chars=10,
    )

    assert omitted_count == 2
    assert len(compacted) == 2


def test_compact_messages_pins_original_task_when_provided():
    """
    Long histories keep the original run task pinned right after the system
    prompt so the model never loses sight of the goal.
    """
    messages = [
        {"role": "system", "content": "system rules"},
        {"role": "user", "content": "refactor parser.py"},
        {"role": "assistant", "content": "old assistant " * 30},
        {"role": "user", "content": "Observation: stale " * 20},
        {"role": "assistant", "content": "recent assistant"},
        {"role": "user", "content": "Observation: fresh"},
    ]

    compacted, omitted_count = context_window.compact_messages_for_context(
        messages,
        max_chars=200,
        keep_recent_messages=2,
        max_message_chars=80,
        original_task="refactor parser.py",
    )

    assert compacted[0] == {"role": "system", "content": "system rules"}
    assert compacted[1]["role"] == "user"
    assert compacted[1]["content"].startswith(context_window.ORIGINAL_TASK_PREFIX)
    assert "refactor parser.py" in compacted[1]["content"]
    assert omitted_count >= 1
