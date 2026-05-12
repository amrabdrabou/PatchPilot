# Runs approved commands in the sandbox and records command audit entries.
from pathlib import Path
import subprocess

from backend.config import (
    COMMAND_LOG_FILE,
    COMMAND_TIMEOUT_SECONDS,
    MAX_COMMAND_OUTPUT_CHARS,
)
from backend.run_logger import stockholm_now_iso
from backend.tools import safety


def run_bash(command: str) -> str:
    """
    Run an allowlisted command inside the sandbox after approval.
    """
    command_args, error = safety.build_allowed_command(command)

    if error or command_args is None:
        log_command(command, "BLOCKED")
        return f"Blocked command: {error or 'Command could not be parsed.'}"

    try:
        log_command(command, "ALLOWED")

        result = subprocess.run(
            command_args,
            shell=False,
            cwd=safety.BASE_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        output = result.stdout

        if result.stderr:
            output += "\nERROR:\n" + result.stderr

        if not output.strip():
            output = "Command finished with no output."

        return output[:MAX_COMMAND_OUTPUT_CHARS]

    except subprocess.TimeoutExpired:
        log_command(command, "TIMEOUT")
        return "Error: command timed out."
    except FileNotFoundError:
        log_command(command, "MISSING")
        return f"Error: command program is not installed: {command_args[0]}."
    except OSError as error:
        log_command(command, "ERROR")
        return f"Error: command could not run: {error}."


def log_command(command: str, status: str):
    """
    Append one command audit entry to the command log.
    """
    try:
        log_path = Path(COMMAND_LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = stockholm_now_iso()

        with log_path.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {status}: {command}\n")
    except OSError:
        pass
