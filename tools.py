from pathlib import Path
from datetime import datetime
from config import (
    PROJECT_DIR,
    COMMAND_TIMEOUT_SECONDS,
    MAX_COMMAND_OUTPUT_CHARS,
    COMMAND_LOG_FILE,
)
import subprocess

BASE_DIR = Path(PROJECT_DIR).resolve()


def safe_path(path: str) -> Path:
    """
    Convert a user-provided path into a safe path inside test_project.
    This prevents the agent from reading files outside the allowed folder.
    """
    requested_path = (BASE_DIR / path).resolve()

    if not str(requested_path).startswith(str(BASE_DIR)):
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


    import subprocess


DANGEROUS_COMMANDS = [
    "rm ",
    "rm -",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    "dd ",
    ":(){",
    "chmod -R",
    "chown -R",
    "curl ",
    "wget ",
    "pip install",
    "npm install",
]


def is_safe_command(command: str) -> bool:
    """
    Basic safety check for dangerous bash commands.
    This is not perfect, but it blocks many obvious dangerous commands.
    """
    lowered = command.lower()

    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in lowered:
            return False

    return True


def run_bash(command: str) -> str:
    """
    Run a bash command safely inside the project folder.
    Requires human confirmation before execution.
    """

    if not is_safe_command(command):
        log_command(command, "BLOCKED")
        return f"Blocked dangerous command: {command}"

    print("\nThe agent wants to run this command:")
    print(command)

    choice = input("Allow this command? (y/n): ")

    if choice.lower() != "y":
        log_command(command, "REJECTED")
        return "Command rejected by user."

    try:
        log_command(command, "ALLOWED")

        result = subprocess.run(
            command,
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

    choice = input("Allow this edit? (y/n): ")

    if choice.lower() != "y":
        return "Edit rejected by user."

    updated_content = content.replace(old_text, new_text, 1)

    file_path.write_text(updated_content, encoding="utf-8")

    return f"Edited {path}: replaced one occurrence."

def git_diff() -> str:
    """
    Show git diff for the project folder.
    This helps review what the agent changed.
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