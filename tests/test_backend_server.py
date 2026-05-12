# Verifies FastAPI endpoints that coordinate run lifecycle state.
from fastapi.testclient import TestClient

import backend.backend_server as backend_server


def test_stop_run_endpoint_reports_stop_request(monkeypatch):
    calls = []
    client = TestClient(backend_server.app)

    def fake_request_stop_run(run_id):
        calls.append(run_id)
        return True

    monkeypatch.setattr(backend_server, "request_stop_run", fake_request_stop_run)

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
