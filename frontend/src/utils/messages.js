// Provides tiny helpers for local message state.
export function createLocalMessageId() {
  return Date.now() + Math.random();
}

export function createMessageTimestamp() {
  return new Date().toISOString();
}

export function formatMessageTimestamp(timestamp) {
  if (!timestamp) return "Time unavailable";

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) return "Time unavailable";

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}
