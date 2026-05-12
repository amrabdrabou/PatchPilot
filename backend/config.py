# Stores shared runtime limits, paths, and model settings.
from pathlib import Path


MODEL_NAME = "gpt-4.1-mini"
MODEL_MAX_RETRIES = 2
MODEL_RETRY_BACKOFF_SECONDS = 0.5

MAX_STEPS = 10
MAX_TOOL_CALLS = 8
MAX_CONTEXT_CHARS = 24000
CONTEXT_KEEP_RECENT_MESSAGES = 8
MAX_CONTEXT_MESSAGE_CHARS = 6000

# Mirrors the frontend MAX_DRAFT_LENGTH cap so direct API clients cannot bypass
# the textarea limit by POSTing oversized tasks.
MAX_TASK_LENGTH = 4000

COMMAND_TIMEOUT_SECONDS = 10
MAX_COMMAND_OUTPUT_CHARS = 3000

REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECT_DIR = REPO_ROOT / "test_project"

COMMAND_LOG_FILE = REPO_ROOT / "logs" / "commands.log"

RUN_LOG_FILE = REPO_ROOT / "logs" / "runs.jsonl"
