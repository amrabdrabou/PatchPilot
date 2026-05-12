# Wraps LLM API calls for the PatchPilot runtime.
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from backend.config import MODEL_MAX_RETRIES, MODEL_NAME, MODEL_RETRY_BACKOFF_SECONDS


load_dotenv()

TRANSIENT_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
}
TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

SLEEP_TICK_SECONDS = 0.1


class ModelCallCancelled(Exception):
    """Raised when a caller asks ``ask_model_result`` to stop mid-retry."""


def get_client():
    """
    Create the OpenAI client only when a model call is actually made.
    """
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def is_transient_model_error(error):
    """
    Return True for retryable provider/network failures.
    """
    if type(error).__name__ in TRANSIENT_ERROR_NAMES:
        return True

    status_code = getattr(error, "status_code", None)

    return status_code in TRANSIENT_STATUS_CODES


def retry_delay(attempt):
    """
    Return a short linear backoff delay for one retry attempt.
    """
    return MODEL_RETRY_BACKOFF_SECONDS * attempt


def interruptible_sleep(total_seconds, should_stop):
    """
    Sleep up to ``total_seconds``, returning early if ``should_stop`` returns True.

    When ``should_stop`` is None this falls back to one ``time.sleep`` call so
    existing callers and tests see no behavior change.
    """
    if should_stop is None:
        time.sleep(total_seconds)
        return

    elapsed = 0.0

    while elapsed < total_seconds:
        if should_stop():
            return

        chunk = min(SLEEP_TICK_SECONDS, total_seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk


def extract_token_usage(response):
    """
    Return token counters from an LLM response when the provider includes them.
    """
    usage = getattr(response, "usage", None)

    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }


def ask_model_result(messages, should_stop=None):
    """
    Send messages to the LLM and return text plus token usage.

    When ``should_stop`` is provided it is polled before each attempt and during
    retry backoff sleeps. If it returns True the function raises
    ``ModelCallCancelled`` so the caller can route the run into a stop-safe
    cleanup path instead of treating cancellation as a generic failure.
    """
    last_error = None

    for attempt in range(1, MODEL_MAX_RETRIES + 2):
        if should_stop is not None and should_stop():
            raise ModelCallCancelled()

        try:
            response = get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0,
            )
            break
        except Exception as error:
            last_error = error

            if not is_transient_model_error(error) or attempt > MODEL_MAX_RETRIES:
                raise

            interruptible_sleep(retry_delay(attempt), should_stop)

            if should_stop is not None and should_stop():
                raise ModelCallCancelled()
    else:
        raise last_error

    return {
        "content": response.choices[0].message.content,
        "usage": extract_token_usage(response),
    }
