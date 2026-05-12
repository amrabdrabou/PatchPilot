# Implements sandboxed file inspection, search, and one-replacement edits.
from backend.config import MAX_COMMAND_OUTPUT_CHARS
from backend.tools import safety

MAX_SEARCH_FILE_BYTES = 200_000
MAX_SEARCH_FILES = 200
IGNORED_SEARCH_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def truncate_output(output: str) -> str:
    """
    Limit file tool output before sending it back to the model or UI.
    """
    if len(output) <= MAX_COMMAND_OUTPUT_CHARS:
        return output

    return output[:MAX_COMMAND_OUTPUT_CHARS] + "\n... output truncated ..."


def list_files(path: str = ".") -> str:
    """
    List files inside a sandbox directory.
    """
    try:
        folder = safety.safe_path(path)
    except ValueError as error:
        return f"Error: {error}"

    if not folder.exists():
        return f"Error: {path} does not exist."

    if not folder.is_dir():
        return f"Error: {path} is not a directory."

    try:
        items = []
        for item in sorted(folder.iterdir(), key=lambda path: path.name.lower()):
            if item.is_dir():
                items.append(f"{item.name}/")
            else:
                items.append(item.name)
    except OSError as error:
        return f"Error: could not list {path}: {error}"

    return truncate_output("\n".join(items))


def read_file(path: str) -> str:
    """
    Read one file from inside the sandbox.
    """
    try:
        file_path = safety.safe_path(path)
    except ValueError as error:
        return f"Error: {error}"

    if not file_path.exists():
        return f"Error: {path} does not exist."

    if not file_path.is_file():
        return f"Error: {path} is not a file."

    try:
        return truncate_output(file_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return f"Error: {path} is not a UTF-8 text file."
    except OSError as error:
        return f"Error: could not read {path}: {error}"


def search_files(query: str) -> str:
    """
    Search sandbox text files for a case-insensitive query.
    """
    results = []

    scanned_files = 0

    for file_path in safety.BASE_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        if any(part in IGNORED_SEARCH_DIRS for part in file_path.relative_to(safety.BASE_DIR).parts):
            continue

        try:
            if file_path.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
        except OSError:
            continue

        scanned_files += 1

        if scanned_files > MAX_SEARCH_FILES:
            break

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if query.lower() in line.lower():
                relative_path = file_path.relative_to(safety.BASE_DIR)
                results.append(f"{relative_path}:{line_number}: {line}")

    if not results:
        return f"No matches found for: {query}"

    return truncate_output("\n".join(results[:50]))


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    Replace one text occurrence in a sandbox file after approval.
    """
    try:
        file_path = safety.safe_path(path)
    except ValueError as error:
        return f"Error: {error}"

    if not file_path.exists():
        return f"Error: {path} does not exist."

    if not file_path.is_file():
        return f"Error: {path} is not a file."

    if not old_text:
        return "Error: old_text cannot be empty. No changes made."

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: {path} is not a UTF-8 text file. No changes made."
    except OSError as error:
        return f"Error: could not read {path}: {error}"

    if old_text not in content:
        return "Error: old_text was not found in the file. No changes made."

    updated_content = content.replace(old_text, new_text, 1)

    try:
        file_path.write_text(updated_content, encoding="utf-8")
    except OSError as error:
        return f"Error: could not write {path}: {error}"

    return f"Edited {path}: replaced one occurrence."
