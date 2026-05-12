// Tracks run progress and limits from backend stream events.
import { useCallback, useMemo, useState } from "react";

export const EMPTY_LIMITS = {
  maxSteps: 0,
  maxToolCalls: 0,
};

export const EMPTY_PROGRESS = {
  modelCalls: 0,
  status: "idle",
  stepsUsed: 0,
  toolCallsUsed: 0,
};

export function useRunProgress() {
  const [limits, setLimits] = useState(EMPTY_LIMITS);
  const [runProgress, setRunProgress] = useState(EMPTY_PROGRESS);

  const progress = useMemo(
    () => ({
      ...runProgress,
      maxSteps: limits.maxSteps,
      maxToolCalls: limits.maxToolCalls,
    }),
    [limits, runProgress]
  );

  const updateProgressFromEvent = useCallback((event) => {
    const hasProgress =
      event.step !== undefined ||
      event.model_calls !== undefined ||
      event.tool_calls !== undefined ||
      event.max_steps !== undefined ||
      event.max_tool_calls !== undefined;

    if (!hasProgress) return;

    setRunProgress((currentProgress) => ({
      ...currentProgress,
      modelCalls: event.model_calls ?? currentProgress.modelCalls,
      status:
        event.type === "final" || event.type === "stopped"
          ? "finished"
          : event.type === "approval_required"
          ? "waiting"
          : "running",
      stepsUsed: event.step ?? currentProgress.stepsUsed,
      toolCallsUsed: event.tool_calls ?? currentProgress.toolCallsUsed,
    }));

    setLimits((currentLimits) => ({
      maxSteps: event.max_steps ?? currentLimits.maxSteps,
      maxToolCalls: event.max_tool_calls ?? currentLimits.maxToolCalls,
    }));
  }, []);

  return {
    limits,
    progress,
    runProgress,
    setLimits,
    setRunProgress,
    updateProgressFromEvent,
  };
}
