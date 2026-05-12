# Keeps agent message history inside a simple character budget.


CONTEXT_SUMMARY_PREFIX = "Context summary:"
ORIGINAL_TASK_PREFIX = "Original task:"


def message_char_count(message):
    """
    Estimate one chat message's context size using role and content text.
    """
    return len(str(message.get("role", ""))) + len(str(message.get("content", "")))


def messages_char_count(messages):
    """
    Estimate total context size for a list of chat messages.
    """
    return sum(message_char_count(message) for message in messages)


def truncate_content(content, max_chars):
    """
    Cap one message body while making truncation visible to the model.
    """
    text = str(content)
    marker = "\n... context message truncated ..."

    if len(text) <= max_chars:
        return text

    if max_chars <= len(marker):
        return text[:max_chars]

    return text[:max_chars - len(marker)] + marker


def truncate_message(message, max_message_chars):
    """
    Return a copy of one message with a bounded content field.
    """
    return {
        **message,
        "content": truncate_content(message.get("content", ""), max_message_chars),
    }


def build_compaction_summary(omitted_messages):
    """
    Describe omitted history without exposing large old observations again.
    """
    return f"{CONTEXT_SUMMARY_PREFIX} {len(omitted_messages)} compacted."


def compact_messages_for_context(
    messages,
    max_chars,
    keep_recent_messages,
    max_message_chars,
    original_task=None,
):
    """
    Return messages capped to a context budget plus the count of omitted messages.

    When ``original_task`` is provided, the function injects a pinned user
    message right after the system prompt so the model keeps the run goal in
    scope after older history is summarized away.
    """
    if messages_char_count(messages) <= max_chars:
        return messages, 0

    system_messages = [message for message in messages if message.get("role") == "system"]
    non_system_messages = [
        message for message in messages if message.get("role") != "system"
    ]
    if keep_recent_messages <= 0:
        recent_messages = []
        omitted_messages = non_system_messages
    else:
        recent_messages = non_system_messages[-keep_recent_messages:]
        omitted_messages = non_system_messages[:-keep_recent_messages]

    compacted = [*system_messages[:1]]

    if original_task:
        compacted.append(
            truncate_message(
                {
                    "role": "user",
                    "content": f"{ORIGINAL_TASK_PREFIX} {original_task}",
                },
                max_message_chars,
            )
        )

    if omitted_messages:
        compacted.append({
            "role": "user",
            "content": build_compaction_summary(omitted_messages),
        })

    compacted.extend(
        truncate_message(message, max_message_chars) for message in recent_messages
    )

    while len(compacted) > 2 and messages_char_count(compacted) > max_chars:
        compacted.pop(2)

    if messages_char_count(compacted) > max_chars:
        max_compacted_message_chars = max(1, max_chars // max(1, len(compacted)))
        compacted = [
            truncate_message(
                message,
                min(max_message_chars, max_compacted_message_chars),
            )
            for message in compacted
        ]

    return compacted, len(omitted_messages)
