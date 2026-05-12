# Wraps LLM API calls for the PatchPilot runtime.
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from backend.config import MODEL_MAX_RETRIES, MODEL_NAME, MODEL_RETRY_BACKOFF_SECONDS


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TRANSIENT_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
}
TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


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


def ask_model_result(messages):
    """
    Send messages to the LLM and return text plus token usage.
    """
    last_error = None

    for attempt in range(1, MODEL_MAX_RETRIES + 2):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0,
            )
            break
        except Exception as error:
            last_error = error

            if not is_transient_model_error(error) or attempt > MODEL_MAX_RETRIES:
                raise

            time.sleep(retry_delay(attempt))
    else:
        raise last_error

    return {
        "content": response.choices[0].message.content,
        "usage": extract_token_usage(response),
    }
