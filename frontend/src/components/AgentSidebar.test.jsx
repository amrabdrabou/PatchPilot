// Verifies sidebar agent and saved conversation controls.
// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import AgentSidebar from "./AgentSidebar";

const AGENTS = [{ id: "backend", name: "PatchPilot", color: "text-cyan-300" }];
const PROGRESS = {
  maxSteps: 10,
  maxToolCalls: 8,
  modelCalls: 1,
  status: "idle",
  stepsUsed: 2,
  toolCallsUsed: 0,
};

function renderSidebar(overrides = {}) {
  const props = {
    agents: AGENTS,
    conversations: [
      {
        id: "conv-1",
        message_count: 2,
        title: "Saved parser fix",
        updated_at: "2026-05-13T00:00:00+02:00",
      },
    ],
    messages: [],
    onReset: vi.fn(),
    onDeleteConversation: vi.fn(),
    onSelectAgent: vi.fn(),
    onSelectConversation: vi.fn(),
    progress: PROGRESS,
    selectedAgentId: "backend",
    ...overrides,
  };

  render(<AgentSidebar {...props} />);

  return props;
}

afterEach(() => {
  cleanup();
});

describe("AgentSidebar", () => {
  test("renders saved conversations and loads one when selected", () => {
    const props = renderSidebar();

    expect(screen.getByText("Conversations")).toBeInTheDocument();
    expect(screen.getByText("Saved parser fix")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open Saved parser fix" }));

    expect(props.onSelectConversation).toHaveBeenCalledWith("conv-1");
  });

  test("deletes a saved conversation without loading it", () => {
    const props = renderSidebar();

    fireEvent.click(screen.getByRole("button", { name: "Delete Saved parser fix" }));

    expect(props.onDeleteConversation).toHaveBeenCalledWith("conv-1");
    expect(props.onSelectConversation).not.toHaveBeenCalled();
  });

  test("renders an empty conversation state", () => {
    renderSidebar({ conversations: [] });

    expect(screen.getByText("No saved conversations")).toBeInTheDocument();
  });
});
