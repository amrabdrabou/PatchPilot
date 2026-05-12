// Verifies frontend API helpers build the expected backend requests.
import { afterEach, describe, expect, test, vi } from "vitest";

import {
  archiveCurrentConversation,
  deleteConversation,
  listConversations,
  loadConversation,
} from "./agentApi";

function mockJsonResponse(body, options = {}) {
  return Promise.resolve({
    json: () => Promise.resolve(body),
    ok: options.ok ?? true,
    status: options.status ?? 200,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("agentApi conversation helpers", () => {
  test("lists saved conversations", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(await mockJsonResponse({ conversations: [] }));

    await expect(listConversations()).resolves.toEqual({ conversations: [] });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/conversations",
      {}
    );
  });

  test("loads one saved conversation", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(await mockJsonResponse({ conversation: { id: "conv-1" } }));

    await expect(loadConversation("conv-1")).resolves.toEqual({
      conversation: { id: "conv-1" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/conversations/conv-1",
      {}
    );
  });

  test("archives the current message stream", async () => {
    const messages = [{ id: "msg-1", text: "hello" }];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(await mockJsonResponse({ archived_conversation: {} }));

    await archiveCurrentConversation(messages);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/conversations/archive-current",
      {
        body: JSON.stringify({ messages }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      }
    );
  });

  test("deletes one saved conversation", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(await mockJsonResponse({ deleted: true }));

    await expect(deleteConversation("conv-1")).resolves.toEqual({ deleted: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/conversations/conv-1",
      {
        method: "DELETE",
      }
    );
  });

  test("throws for failed archive responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      await mockJsonResponse({}, { ok: false, status: 500 })
    );

    await expect(archiveCurrentConversation([])).rejects.toThrow(
      "Request failed with status 500"
    );
  });
});
