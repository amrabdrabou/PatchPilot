# Verifies FastAPI endpoints that coordinate run lifecycle state.
import asyncio

from fastapi.testclient import TestClient

import backend.backend_server as backend_server
from backend.config import MAX_TASK_LENGTH


def test_stop_run_endpoint_reports_stop_request(monkeypatch):
    calls = []
    client = TestClient(backend_server.app)

    def fake_request_run_stop(run_id):
        calls.append(run_id)
        return True

    monkeypatch.setattr(backend_server, "request_run_stop", fake_request_run_stop)

    response = client.post("/stop-run", json={"run_id": "run-1"})

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run-1",
        "stop_requested": True,
    }
    assert calls == ["run-1"]


def test_stream_endpoint_returns_sse(monkeypatch):
    client = TestClient(backend_server.app)

    def fake_start_agent_stream(task, max_steps, max_tool_calls):
        yield {
            "type": "start",
            "content": "Agent started.",
            "run_id": "run-1",
        }

    monkeypatch.setattr(backend_server, "start_agent_stream", fake_start_agent_stream)

    response = client.post("/run-agent-stream", json={"task": "hello"})

    assert response.status_code == 200
    assert 'data: {"type": "start", "content": "Agent started.", "run_id": "run-1"}' in response.text


def test_run_agent_stream_rejects_oversized_task():
    client = TestClient(backend_server.app)

    response = client.post(
        "/run-agent-stream",
        json={"task": "x" * (MAX_TASK_LENGTH + 1)},
    )

    assert response.status_code == 422


def test_run_agent_stream_rejects_empty_task():
    client = TestClient(backend_server.app)

    response = client.post("/run-agent-stream", json={"task": ""})

    assert response.status_code == 422


class _FakeRequest:
    """Minimal Request stub for stream_events_with_disconnect tests."""

    def __init__(self, disconnect_after=None):
        self._disconnect_after = disconnect_after
        self._calls = 0

    async def is_disconnected(self):
        self._calls += 1

        if self._disconnect_after is None:
            return False

        return self._calls > self._disconnect_after


def _collect_stream(request, events):
    async def collect():
        chunks = []

        async for chunk in backend_server.stream_events_with_disconnect(
            request, events
        ):
            chunks.append(chunk)

        return chunks

    return asyncio.run(collect())


def test_stream_events_yields_all_events_when_connected(monkeypatch):
    stop_calls = []
    monkeypatch.setattr(
        backend_server,
        "request_run_stop",
        lambda run_id: stop_calls.append(run_id) or True,
    )

    events = [
        {"type": "start", "run_id": "run-1", "content": "go"},
        {"type": "final", "run_id": "run-1", "content": "done"},
    ]

    chunks = _collect_stream(_FakeRequest(), iter(events))

    assert len(chunks) == 2
    assert stop_calls == []


def test_stream_events_requests_stop_on_client_disconnect(monkeypatch):
    stop_calls = []
    monkeypatch.setattr(
        backend_server,
        "request_run_stop",
        lambda run_id: stop_calls.append(run_id) or True,
    )

    events = [
        {"type": "start", "run_id": "run-2", "content": "go"},
        {"type": "step", "run_id": "run-2", "content": "step 1"},
        {"type": "final", "run_id": "run-2", "content": "done"},
    ]

    chunks = _collect_stream(_FakeRequest(disconnect_after=1), iter(events))

    assert len(chunks) == 1
    assert stop_calls == ["run-2"]


def test_stream_events_skips_stop_when_no_run_id_seen(monkeypatch):
    stop_calls = []
    monkeypatch.setattr(
        backend_server,
        "request_run_stop",
        lambda run_id: stop_calls.append(run_id) or True,
    )

    events = [
        {"type": "ping", "content": "hello"},
    ]

    chunks = _collect_stream(_FakeRequest(disconnect_after=0), iter(events))

    assert chunks == []
    assert stop_calls == []
