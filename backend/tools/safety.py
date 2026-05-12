# Holds sandbox path checks and command allowlist logic for runtime tools.
from pathlib import Path
import shlex

from backend.config import PROJECT_DIR

BASE_DIR = Path(PROJECT_DIR).resolve()
REPO_DIR = BASE_DIR.parent

ALLOWED_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "log",
    "show",
    "status",
}

ALLOWED_GIT_OPTIONS = {
    "branch": {"--show-current", "--list", "-a"},
    "diff": {"--stat", "--name-only", "--name-status"},
    "log": {"--oneline", "--stat"},
    "show": {"--stat", "--name-only", "--name-status"},
    "status": {"--short", "--porcelain"},
}

ALLOWED_PYTEST_OPTIONS = {
    "-q",
    "-s",
    "-v",
    "--disable-warnings",
    "--tb=auto",
    "--tb=long",
    "--tb=short",
}


def safe_path(path: str) -> Path:
    """
    Convert a user-provided path into a safe path inside test_project.
    """
    requested_path = (BASE_DIR / path).resolve()

    try:
        requested_path.relative_to(BASE_DIR)
    except ValueError:
        raise ValueError("Access denied: path is outside the allowed project folder.")

    return requested_path


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
        return build_allowed_pytest_command(parts, argument_start=1)

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
            return build_allowed_pytest_command(parts, argument_start=3)

        return None, "Only 'python -m pytest' is allowed for module execution."

    if parts[1] in {"-c", "-"}:
        return None, "Inline Python execution is not allowed."

    script_path = safe_path(parts[1])

    if script_path.suffix != ".py":
        return None, "Python commands may only run .py files."

    if not script_path.exists():
        return None, f"Python script does not exist: {parts[1]}"

    argument_error = validate_python_script_arguments(parts[2:])

    if argument_error:
        return None, argument_error

    return parts, None


def build_allowed_pytest_command(
    parts: list[str],
    argument_start: int,
) -> tuple[list[str] | None, str | None]:
    """
    Allow pytest with a small set of options and sandbox-local paths.
    """
    for argument in parts[argument_start:]:
        if argument.startswith("-"):
            if argument in ALLOWED_PYTEST_OPTIONS or argument.startswith("--maxfail="):
                continue

            return None, f"Pytest option is not allowed: {argument}"

        try:
            safe_path(argument)
        except ValueError:
            return None, f"Pytest path is outside the sandbox: {argument}"

    return parts, None


def validate_python_script_arguments(arguments: list[str]) -> str | None:
    """
    Reject script arguments that look like unsafe options or path escapes.
    """
    for argument in arguments:
        if argument.startswith("-"):
            return f"Python script option arguments are not allowed: {argument}"

        if "/" in argument or "\\" in argument:
            try:
                safe_path(argument)
            except ValueError:
                return f"Python script argument path is outside the sandbox: {argument}"

    return None


def build_allowed_git_command(parts: list[str]) -> tuple[list[str] | None, str | None]:
    """
    Allow only read-only git commands for inspection.
    """
    if len(parts) < 2:
        return None, "Git commands must include a subcommand."

    subcommand = parts[1].lower()

    if subcommand not in ALLOWED_GIT_SUBCOMMANDS:
        return None, f"Git subcommand is not allowed: {parts[1]}"

    allowed_options = ALLOWED_GIT_OPTIONS[subcommand]

    for argument in parts[2:]:
        if argument.startswith("-"):
            if argument not in allowed_options:
                return None, f"Git option is not allowed for {subcommand}: {argument}"

            continue

        if subcommand == "show":
            if "/" in argument or "\\" in argument:
                return None, "Git show revisions must not include paths."

            continue

        try:
            safe_path(argument)
        except ValueError:
            return None, f"Git path is outside the sandbox: {argument}"

    return parts, None
