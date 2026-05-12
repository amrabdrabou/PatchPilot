# Verifies model API retries and token usage extraction.
from types import SimpleNamespace

import pytest

import backend.model_client as model_client


class FakeTransientError(Exception):
    status_code = 429


class FakePermanentError(Exception):
    status_code = 400


def build_response(content="Final Answer: done"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=2,
            completion_tokens=3,
            total_tokens=5,
        ),
    )


def test_ask_model_result_retries_transient_errors(monkeypatch):
    calls = []
    sleeps = []
    responses = [FakeTransientError("rate limit"), build_response()]

    def fake_create(**kwargs):
        calls.append(kwargs)
        result = responses.pop(0)

        if isinstance(result, Exception):
            raise result

        return result

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(model_client, "get_client", lambda: fake_client)
    monkeypatch.setattr(model_client.time, "sleep", sleeps.append)

    result = model_client.ask_model_result([{"role": "user", "content": "hi"}])

    assert result == {
        "content": "Final Answer: done",
        "usage": {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        },
    }
    assert len(calls) == 2
    assert sleeps == [model_client.MODEL_RETRY_BACKOFF_SECONDS]


def test_ask_model_result_does_not_retry_permanent_errors(monkeypatch):
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        raise FakePermanentError("bad request")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(model_client, "get_client", lambda: fake_client)
    monkeypatch.setattr(model_client.time, "sleep", lambda delay: None)

    with pytest.raises(FakePermanentError):
        model_client.ask_model_result([{"role": "user", "content": "hi"}])

    assert len(calls) == 1


def test_ask_model_result_stops_after_retry_limit(monkeypatch):
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        raise FakeTransientError("still limited")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(model_client, "get_client", lambda: fake_client)
    monkeypatch.setattr(model_client.time, "sleep", lambda delay: None)

    with pytest.raises(FakeTransientError):
        model_client.ask_model_result([{"role": "user", "content": "hi"}])

    assert len(calls) == model_client.MODEL_MAX_RETRIES + 1
