# Writes structured JSONL run records for UI and CLI agent runs.
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.config import RUN_LOG_FILE

try:
    STOCKHOLM_TIMEZONE = ZoneInfo("Europe/Stockholm")
except ZoneInfoNotFoundError:
    STOCKHOLM_TIMEZONE = None


def last_sunday(year, month):
    """
    Return the day number for the last Sunday in a month.
    """
    date = datetime(year, month + 1, 1) - timedelta(days=1)

    while date.weekday() != 6:
        date -= timedelta(days=1)

    return date.day


def stockholm_fallback_timezone(now_utc):
    """
    Return CET or CEST when system timezone data is unavailable.
    """
    year = now_utc.year
    dst_start = datetime(year, 3, last_sunday(year, 3), 1, tzinfo=timezone.utc)
    dst_end = datetime(year, 10, last_sunday(year, 10), 1, tzinfo=timezone.utc)

    if dst_start <= now_utc < dst_end:
        return timezone(timedelta(hours=2), "CEST")

    return timezone(timedelta(hours=1), "CET")


def stockholm_now_iso():
    """
    Return the current Europe/Stockholm time as an ISO timestamp.
    """
    if STOCKHOLM_TIMEZONE is not None:
        return datetime.now(STOCKHOLM_TIMEZONE).isoformat()

    now_utc = datetime.now(timezone.utc)
    return now_utc.astimezone(stockholm_fallback_timezone(now_utc)).isoformat()


def write_run_log(record, log_file=RUN_LOG_FILE):
    """
    Append one structured run record to the JSONL run log.
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")


def build_run_log_record(
    *,
    run_id,
    task,
    started_at,
    status,
    final_answer,
    steps,
    max_steps,
    model_calls,
    tool_calls,
    max_tool_calls,
    tool_usage,
    interface,
    token_usage=None,
    trace=None,
):
    """
    Build a serializable summary of one completed or stopped run.
    """
    return {
        "run_id": run_id,
        "task": task,
        "started_at": started_at,
        "ended_at": stockholm_now_iso(),
        "status": status,
        "final_answer": final_answer,
        "steps": steps,
        "max_steps": max_steps,
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "max_tool_calls": max_tool_calls,
        "tool_usage": dict(tool_usage),
        "token_usage": token_usage
        or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "trace": trace or [],
        "interface": interface,
    }
