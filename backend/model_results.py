# Normalizes model/tool results for CLI and web agent loops.


def add_token_usage(token_usage, usage):
    """
    Add one model response's token usage to accumulated totals.
    """
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        token_usage[key] += usage.get(key, 0) or 0


def normalize_model_result(result):
    """
    Accept structured model responses and test-friendly plain strings.
    """
    if isinstance(result, dict):
        return result.get("content", ""), result.get("usage", {})

    return str(result), {}


def build_observation(result):
    """
    Tag observations so the model can distinguish success, error, and blocked work.
    """
    text = str(result)

    if text.startswith("Blocked command:") or text.startswith(
        "User rejected tool call:"
    ):
        return f"Observation [blocked]: {text}"

    if text.startswith("Error:"):
        return f"Observation [error]: {text}"

    return f"Observation: {text}"


def latest_assistant_message(messages):
    """
    Return the latest assistant text for best-effort stopped output.
    """
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return message.get("content", "")

    return ""


def build_stopped_answer(messages, reason):
    """
    Include the latest assistant text when a stopped run has useful partial work.
    """
    assistant_message = latest_assistant_message(messages)

    if not assistant_message:
        return reason

    return f"{reason}\n\nBest effort partial answer:\n{assistant_message}"
