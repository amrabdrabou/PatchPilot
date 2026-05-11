# Verifies sandbox path safety and command allowlisting.
import pytest

from backend.tools import BASE_DIR, build_allowed_command, safe_path


def test_safe_path_allows_project_file():
    path = safe_path("README.md")

    assert path == BASE_DIR / "README.md"


def test_safe_path_allows_project_root():
    path = safe_path(".")

    assert path == BASE_DIR


def test_safe_path_blocks_parent_escape():
    with pytest.raises(ValueError, match="outside the allowed project folder"):
        safe_path("..")


def test_safe_path_blocks_sibling_prefix_escape():
    with pytest.raises(ValueError, match="outside the allowed project folder"):
        safe_path("../test_project_evil")


@pytest.mark.parametrize(
    ("command", "expected_args"),
    [
        ("python hello.py", ["python", "hello.py"]),
        ("py hello.py", ["py", "hello.py"]),
        ("python -m pytest", ["python", "-m", "pytest"]),
        ("pytest", ["pytest"]),
        ("git status --short", ["git", "status", "--short"]),
        ("git diff", ["git", "diff"]),
    ],
)
def test_build_allowed_command_accepts_safe_commands(command, expected_args):
    args, error = build_allowed_command(command)

    assert args == expected_args
    assert error is None


@pytest.mark.parametrize(
    "command",
    [
        "",
        "python",
        "python -c \"print(1)\"",
        "python -m http.server",
        "python README.md",
        "rm -rf .",
        "git reset --hard",
    ],
)
def test_build_allowed_command_blocks_unsafe_commands(command):
    args, error = build_allowed_command(command)

    assert args is None
    assert error
