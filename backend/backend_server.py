# Exposes the agent hub API and streaming endpoints.
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from backend.agent_stream import (
    start_agent_stream,
    approve_pending_tool,
    reject_pending_tool,
    format_sse,
)
from backend.config import MAX_STEPS, MAX_TOOL_CALLS

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


class MessageCreate(BaseModel):
    agentId: str
    text: str

class AgentRunRequest(BaseModel):
    task: str

class ApprovalRequest(BaseModel):
    run_id: str
    approval_id: str


@app.get("/state")
def get_state():
    return {
        "agents": agents,
        "messages": messages,
        "limits": {
            "maxSteps": MAX_STEPS,
            "maxToolCalls": MAX_TOOL_CALLS,
        },
    }


@app.post("/messages")
def create_message(message: MessageCreate):
    new_message = {
        "id": len(messages) + 1,
        "agentId": message.agentId,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "text": message.text,
    }

    messages.append(new_message)

    return new_message


@app.post("/reset")
def reset_all_messages():
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

@app.post("/run-agent-stream")
def run_agent_stream_endpoint(request: AgentRunRequest):
    def event_generator():
        for event in start_agent_stream(
            request.task,
            max_steps=MAX_STEPS,
            max_tool_calls=MAX_TOOL_CALLS,
        ):
            yield format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )

@app.post("/approve-tool")
def approve_tool_endpoint(request: ApprovalRequest):
    def event_generator():
        for event in approve_pending_tool(
            request.run_id,
            request.approval_id,
        ):
            yield format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@app.post("/reject-tool")
def reject_tool_endpoint(request: ApprovalRequest):
    def event_generator():
        for event in reject_pending_tool(
            request.run_id,
            request.approval_id,
        ):
            yield format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
