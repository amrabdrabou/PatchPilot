# Provides read-only git inspection helpers scoped to the sandbox path.
import subprocess

from backend.config import COMMAND_TIMEOUT_SECONDS, MAX_COMMAND_OUTPUT_CHARS
from backend.tools import safety


def git_diff(*args) -> str:
    """
    Show git diff for sandbox changes, ignoring accidental arguments.
    """
    if args:
        return "Error: git_diff does not accept arguments. Use git_diff()."

    try:
        result = subprocess.run(
            ["git", "diff", "--", safety.BASE_DIR.name],
            shell=False,
            cwd=safety.REPO_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        output = result.stdout

        if result.stderr:
            output += "\nERROR:\n" + result.stderr

        if not output.strip():
            return "No git diff found. No tracked files were changed, or this is not a git repository."

        return output[:MAX_COMMAND_OUTPUT_CHARS]

    except subprocess.TimeoutExpired:
        return "Error: git diff command timed out."
    except FileNotFoundError:
        return "Error: git is not installed in the agent runtime. Rebuild the backend container after installing git."
    except OSError as error:
        return f"Error: git diff could not run: {error}"


def git_status(*args) -> str:
    """
    Show short git status for sandbox changes, ignoring accidental arguments.
    """
    if args:
        return "Error: git_status does not accept arguments. Use git_status()."

    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", safety.BASE_DIR.name],
            shell=False,
            cwd=safety.REPO_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        output = result.stdout

        if result.stderr:
            output += "\nERROR:\n" + result.stderr

        if not output.strip():
            return "Working tree clean. No changed files."

        return output[:MAX_COMMAND_OUTPUT_CHARS]

    except subprocess.TimeoutExpired:
        return "Error: git status command timed out."
    except FileNotFoundError:
        return "Error: git is not installed in the agent runtime. Rebuild the backend container after installing git."
    except OSError as error:
        return f"Error: git status could not run: {error}"
