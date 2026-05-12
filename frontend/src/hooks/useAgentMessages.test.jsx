// Verifies local message state helpers.
// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { useAgentMessages } from "./useAgentMessages";

describe("useAgentMessages", () => {
  test("stores trace appends as chunks instead of repeated text concatenation", () => {
    const { result } = renderHook(() => useAgentMessages());

    act(() => {
      result.current.addLocalMessage("backend", "", "agent_trace", "trace-1");
    });

    act(() => {
      result.current.appendMessageText("trace-1", "[STEP] 1\n");
      result.current.appendMessageText("trace-1", "[FINAL] done\n");
    });

    expect(result.current.messages[0]).toMatchObject({
      id: "trace-1",
      text: "",
      traceParts: ["[STEP] 1\n", "[FINAL] done\n"],
      type: "agent_trace",
    });
  });
});
