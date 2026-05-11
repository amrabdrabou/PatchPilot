# Implements safe file, command, and git tools for the agent sandbox.
from pathlib import Path
from datetime import datetime
from backend.config import (
    PROJECT_DIR,
    COMMAND_TIMEOUT_SECONDS,
    MAX_COMMAND_OUTPUT_CHARS,
    COMMAND_LOG_FILE,
)
import shlex
import subprocess

BASE_DIR = Path(PROJECT_DIR).resolve()


def safe_path(path: str) -> Path:
    """
    Convert a user-provided path into a safe path inside test_project.
    This prevents the agent from reading files outside the allowed folder.
    """
    requested_path = (BASE_DIR / path).resolve()

    try:
        requested_path.relative_to(BASE_DIR)
    except ValueError:
        raise ValueError("Access denied: path is outside the allowed project folder.")

    return requested_path


def list_files(path: str = ".") -> str:
    """
    List files inside a directory.
    """
    folder = safe_path(path)

    if not folder.exists():
        return f"Error: {path} does not exist."

    if not folder.is_dir():
        return f"Error: {path} is not a directory."

    items = []
    for item in folder.iterdir():
        if item.is_dir():
            items.append(f"{item.name}/")
        else:
            items.append(item.name)

    return "\n".join(items)


def read_file(path: str) -> str:
    """
    Read a file inside the project folder.
    """
    file_path = safe_path(path)

    if not file_path.exists():
        return f"Error: {path} does not exist."

    if not file_path.is_file():
        return f"Error: {path} is not a file."

    return file_path.read_text(encoding="utf-8")


ALLOWED_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "log",
    "show",
    "status",
}


def build_allowed_command(command: str) -> tuple[list[str] | None, str | None]:
    """
    Parse a command and return argv only for approved command shapes.
    """
    try:
        parts = shlex.split(command)
    except ValueError as error:
        return None, f"Could not parse command: {error}"

    if not parts:
        return None, "Empty commands are not allowed."

    program = parts[0].lower()

    if program in {"python", "py"}:
        return build_allowed_python_command(parts)

    if program == "pytest":
        return parts, None

    if program == "git":
        return build_allowed_git_command(parts)

    return None, (
        "Command is not allowed. Allowed commands are: "
        "python <script.py>, python -m pytest, py <script.py>, pytest, "
        "and read-only git commands."
    )


def build_allowed_python_command(parts: list[str]) -> tuple[list[str] | None, str | None]:
    """
    Allow Python scripts and pytest module runs, but not arbitrary inline code.
    """
    if len(parts) < 2:
        return None, "Python commands must run a script or '-m pytest'."

    if parts[1] == "-m":
        if len(parts) >= 3 and parts[2] == "pytest":
            return parts, None

        return None, "Only 'python -m pytest' is allowed for module execution."

    if parts[1] in {"-c", "-"}:
        return None, "Inline Python execution is not allowed."

    script_path = safe_path(parts[1])

    if script_path.suffix != ".py":
        return None, "Python commands may only run .py files."

    if not script_path.exists():
        return None, f"Python script does not exist: {parts[1]}"

    return parts, None


def build_allowed_git_command(parts: list[str]) -> tuple[list[str] | None, str | None]:
    """
    Allow only read-only git commands for inspection.
    """
    if len(parts) < 2:
        return None, "Git commands must include a subcommand."

    subcommand = parts[1].lower()

    if subcommand not in ALLOWED_GIT_SUBCOMMANDS:
        return None, f"Git subcommand is not allowed: {parts[1]}"

    return parts, None


def run_bash(command: str) -> str:
    """
    Run a bash command safely inside the project folder.
    Frontend approval happens before this function is called.
    """

    command_args, error = build_allowed_command(command)

    if error:
        log_command(command, "BLOCKED")
        return f"Blocked command: {error}"

    try:
        log_command(command, "ALLOWED")

        result = subprocess.run(
            command_args,
            shell=False,
            cwd=BASE_DIR,
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

def log_command(command: str, status: str):
    """
    Logs every bash command request.
    """
    log_path = Path(COMMAND_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat(timespec="seconds")

    with log_path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {status}: {command}\n")


def search_files(query: str) -> str:
    """
    Search for text inside files in the project folder.
    """
    results = []

    for file_path in BASE_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if query.lower() in line.lower():
                relative_path = file_path.relative_to(BASE_DIR)
                results.append(f"{relative_path}:{line_number}: {line}")

    if not results:
        return f"No matches found for: {query}"

    return "\n".join(results[:50])

def edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    Safely edit a file by replacing old_text with new_text.
    Requires human confirmation before changing the file.
    """
    file_path = safe_path(path)

    if not file_path.exists():
        return f"Error: {path} does not exist."

    if not file_path.is_file():
        return f"Error: {path} is not a file."

    content = file_path.read_text(encoding="utf-8")

    if old_text not in content:
        return "Error: old_text was not found in the file. No changes made."

    print("\nThe agent wants to edit this file:")
    print(path)

    print("\nReplace this text:")
    print(old_text)

    print("\nWith this text:")
    print(new_text)

    updated_content = content.replace(old_text, new_text, 1)

    file_path.write_text(updated_content, encoding="utf-8")

    return f"Edited {path}: replaced one occurrence."

def git_diff(*args) -> str:
    """
    Show git diff for the project folder.
    This helps review what the agent changed.

    Accepts ignored args so Action: git_diff("") does not crash.
    """
    try:
        result = subprocess.run(
            "git diff",
            shell=True,
            cwd=BASE_DIR,
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

def git_status(*args) -> str:
    """
    Show git status for the project folder.
    This helps see which files are changed, staged, or untracked.

    Accepts ignored args so Action: git_status("") does not crash.
    """
    try:
        result = subprocess.run(
            "git status --short",
            shell=True,
            cwd=BASE_DIR,
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
