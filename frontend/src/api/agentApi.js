// Keeps backend HTTP calls in one place for the agent hub.
const API_BASE_URL = "http://127.0.0.1:8000";

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

function postJson(path, body) {
  return fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

async function postJsonResult(path, body) {
  const response = await postJson(path, body);

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

export function getState() {
  return fetchJson("/state");
}

export function resetMessages() {
  return fetchJson("/reset", {
    method: "POST",
  });
}

export function startAgentRun(task) {
  return postJson("/run-agent-stream", { task });
}

export function approveToolCall(runId, approvalId) {
  return postJson("/approve-tool", {
    run_id: runId,
    approval_id: approvalId,
  });
}

export function rejectToolCall(runId, approvalId) {
  return postJson("/reject-tool", {
    run_id: runId,
    approval_id: approvalId,
  });
}

export function stopAgentRun(runId) {
  return fetchJson("/stop-run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ run_id: runId }),
  });
}

export function listConversations() {
  return fetchJson("/conversations");
}

export function loadConversation(conversationId) {
  return fetchJson(`/conversations/${conversationId}`);
}

export function archiveCurrentConversation(messages) {
  return postJsonResult("/conversations/archive-current", { messages });
}

export function deleteConversation(conversationId) {
  return fetchJson(`/conversations/${conversationId}`, {
    method: "DELETE",
  });
}
