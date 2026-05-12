// Verifies message stream empty, trace, and final-answer rendering.
// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import MessageStream from "./MessageStream";

const AGENT_MAP = {
  backend: {
    color: "text-cyan-300",
    name: "PatchPilot",
  },
};

beforeEach(() => {
  Element.prototype.scrollTo = vi.fn();
});

afterEach(() => {
  cleanup();
});

describe("MessageStream", () => {
  test("renders the empty state when there are no messages", () => {
    render(<MessageStream agentMap={AGENT_MAP} messages={[]} />);

    expect(
      screen.getByText("No messages yet. Send one command to start the simulation.")
    ).toBeInTheDocument();
  });

  test("renders trace output and collapses to the latest trace line", () => {
    render(
      <MessageStream
        agentMap={AGENT_MAP}
        messages={[
          {
            agentId: "backend",
            createdAt: "2026-05-12T18:00:00.000Z",
            id: "trace-1",
            text: "[STEP] 1\n[THOUGHT] Checking files",
            type: "agent_trace",
          },
        ]}
      />
    );

    expect(screen.getByText(/\[STEP\] 1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Steps Group/ }));

    expect(screen.getByText("[THOUGHT] Checking files")).toBeInTheDocument();
  });

  test("renders final trace text separately from collapsed steps", () => {
    render(
      <MessageStream
        agentMap={AGENT_MAP}
        messages={[
          {
            agentId: "backend",
            createdAt: "2026-05-12T18:00:00.000Z",
            finalLabel: "FINAL ANSWER",
            finalText: "Done cleanly.",
            id: "trace-2",
            text: "[STEP] 1\n[FINAL] Done cleanly.",
            type: "agent_trace_final",
          },
        ]}
      />
    );

    expect(screen.getByText("FINAL ANSWER")).toBeInTheDocument();
    expect(screen.getByText("Done cleanly.")).toBeInTheDocument();
    expect(screen.getByText("[FINAL] Done cleanly.")).toBeInTheDocument();
  });
});
