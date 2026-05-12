// Verifies pending approval controls in the task composer.
// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import MessageComposer, { MAX_DRAFT_LENGTH } from "./MessageComposer";

const AGENTS = [{ id: "patchpilot", name: "PatchPilot" }];

function renderComposer(overrides = {}) {
  const props = {
    agentRunning: false,
    agents: AGENTS,
    draft: "",
    onApprove: vi.fn(),
    onDraftChange: vi.fn(),
    onReject: vi.fn(),
    onSelectAgent: vi.fn(),
    onSend: vi.fn(),
    onStop: vi.fn(),
    pendingApproval: {
      arguments: ["sample.py", "old", "new"],
      toolName: "edit_file",
    },
    selectedAgentId: "patchpilot",
    ...overrides,
  };

  render(<MessageComposer {...props} />);

  return props;
}

afterEach(() => {
  cleanup();
});

describe("MessageComposer", () => {
  test("shows pending approval details and handles approval decisions", () => {
    const props = renderComposer();

    expect(screen.getByText("Approval Required")).toBeInTheDocument();
    expect(screen.getByText("edit_file")).toBeInTheDocument();
    expect(screen.getByText(/sample.py/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    expect(props.onApprove).toHaveBeenCalledTimes(1);
    expect(props.onReject).toHaveBeenCalledTimes(1);
  });

  test("disables approval buttons while the agent is running", () => {
    renderComposer({ agentRunning: true });

    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
  });

  test("uses multiline task input with a length cap and clearer prompt", () => {
    const props = renderComposer({
      draft: "line one\nline two",
      pendingApproval: null,
    });
    const textarea = screen.getByPlaceholderText(
      "Describe a task or type /help..."
    );

    expect(textarea.tagName).toBe("TEXTAREA");
    expect(textarea).toHaveAttribute("maxLength", String(MAX_DRAFT_LENGTH));
    expect(textarea).toHaveValue("line one\nline two");
    expect(screen.getByText(`17/${MAX_DRAFT_LENGTH}`)).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: "new task" } });

    expect(props.onDraftChange).toHaveBeenCalledWith("new task");
  });

  test("submits the draft with ctrl-enter or command-enter", () => {
    const props = renderComposer({ pendingApproval: null });
    const textarea = screen.getByPlaceholderText(
      "Describe a task or type /help..."
    );

    fireEvent.keyDown(textarea, { ctrlKey: true, key: "Enter" });
    fireEvent.keyDown(textarea, { key: "Enter" });
    fireEvent.keyDown(textarea, { key: "Enter", metaKey: true });

    expect(props.onSend).toHaveBeenCalledTimes(2);
  });
});
