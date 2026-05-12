# Exposes the agent hub API and streaming endpoints.
from copy import deepcopy

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool
from backend.agent_stream import (
    start_agent_stream,
    approve_pending_tool,
    reject_pending_tool,
)
from backend.config import MAX_STEPS, MAX_TASK_LENGTH, MAX_TOOL_CALLS
from backend.run_state import request_run_stop
from backend.stream_events import format_sse

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DEFAULT_AGENTS = [
    {
        "id": "backend",
        "name": "PatchPilot",
        "color": "text-[#79ff5b]",
    },
]


agents = deepcopy(DEFAULT_AGENTS)
messages = []


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=MAX_TASK_LENGTH)


class ApprovalRequest(BaseModel):
    run_id: str
    approval_id: str


class StopRunRequest(BaseModel):
    run_id: str


@app.get("/state")
def get_state():
    """
    Return current UI state and configured run limits.
    """
    return {
        "agents": agents,
        "messages": messages,
        "limits": {
            "maxSteps": MAX_STEPS,
            "maxToolCalls": MAX_TOOL_CALLS,
        },
    }


@app.post("/reset")
def reset_all_messages():
    """
    Reset in-memory agents and messages to their defaults.
    """
    global messages, agents

    agents = deepcopy(DEFAULT_AGENTS)
    messages = []

    return {
        "agents": agents,
        "messages": messages,
        "limits": {
            "maxSteps": MAX_STEPS,
            "maxToolCalls": MAX_TOOL_CALLS,
        },
    }


async def stream_events_with_disconnect(request, events):
    """
    Yield SSE chunks and request run stop if the client disconnects.

    The agent's event generator does blocking work (LLM HTTP calls, tool
    execution, retry sleeps). Iterating it directly inside this async function
    would block the asyncio event loop and prevent other endpoints — including
    ``/stop-run`` — from running. ``iterate_in_threadpool`` offloads each
    ``next()`` call to a worker thread so the loop stays responsive.
    """
    active_run_id = None

    async for event in iterate_in_threadpool(events):
        if event.get("run_id"):
            active_run_id = event["run_id"]

        if await request.is_disconnected():
            if active_run_id:
                request_run_stop(active_run_id)
            break

        yield format_sse(event)


@app.post("/run-agent-stream")
def run_agent_stream_endpoint(request: Request, body: AgentRunRequest):
    """
    Stream a new PatchPilot run to the frontend.
    """
    events = start_agent_stream(
        body.task,
        max_steps=MAX_STEPS,
        max_tool_calls=MAX_TOOL_CALLS,
    )

    return StreamingResponse(
        stream_events_with_disconnect(request, events),
        media_type="text/event-stream",
    )

@app.post("/approve-tool")
def approve_tool_endpoint(request: Request, body: ApprovalRequest):
    """
    Stream the result of approving a pending tool call.
    """
    events = approve_pending_tool(
        body.run_id,
        body.approval_id,
    )

    return StreamingResponse(
        stream_events_with_disconnect(request, events),
        media_type="text/event-stream",
    )


@app.post("/stop-run")
def stop_run_endpoint(request: StopRunRequest):
    """
    Request a running stream to stop at the next safe checkpoint.
    """
    stopped = request_run_stop(request.run_id)

    return {
        "run_id": request.run_id,
        "stop_requested": stopped,
    }


@app.post("/reject-tool")
def reject_tool_endpoint(request: Request, body: ApprovalRequest):
    """
    Stream the result of rejecting a pending tool call.
    """
    events = reject_pending_tool(
        body.run_id,
        body.approval_id,
    )

    return StreamingResponse(
        stream_events_with_disconnect(request, events),
        media_type="text/event-stream",
    )
