# Verifies shared model-result normalization helpers.
from backend import model_results


def test_normalize_model_result_accepts_structured_result():
    """
    Structured model results return content plus usage metadata.
    """
    content, usage = model_results.normalize_model_result(
        {
            "content": "Final Answer: done",
            "usage": {"total_tokens": 3},
        }
    )

    assert content == "Final Answer: done"
    assert usage == {"total_tokens": 3}


def test_normalize_model_result_accepts_plain_string():
    """
    Plain strings are supported for tests and simple callers.
    """
    content, usage = model_results.normalize_model_result('Action: read_file("a.py")')

    assert content == 'Action: read_file("a.py")'
    assert usage == {}


def test_add_token_usage_accumulates_known_usage_keys():
    """
    Token usage totals only accumulate the known billing counters.
    """
    totals = {
        "prompt_tokens": 1,
        "completion_tokens": 2,
        "total_tokens": 3,
    }

    model_results.add_token_usage(
        totals,
        {
            "prompt_tokens": 4,
            "completion_tokens": 5,
            "total_tokens": 9,
            "ignored": 99,
        },
    )

    assert totals == {
        "prompt_tokens": 5,
        "completion_tokens": 7,
        "total_tokens": 12,
    }


def test_build_observation_tags_blocked_error_and_success_results():
    """
    Observations are tagged consistently for both CLI and web loops.
    """
    assert model_results.build_observation("Blocked command: rm -rf /").startswith(
        "Observation [blocked]:"
    )
    assert model_results.build_observation("Error: missing file").startswith(
        "Observation [error]:"
    )
    assert model_results.build_observation("hello").startswith("Observation:")


def test_build_stopped_answer_includes_latest_assistant_message():
    """
    Stopped runs can surface the latest useful assistant text.
    """
    answer = model_results.build_stopped_answer(
        [
            {"role": "assistant", "content": "older"},
            {"role": "user", "content": "continue"},
            {"role": "assistant", "content": "newer"},
        ],
        "Stopped.",
    )

    assert answer == "Stopped.\n\nBest effort partial answer:\nnewer"
