# Verifies sandbox path safety and command allowlisting.
from subprocess import CompletedProcess

import pytest

from backend.tools import (
    BASE_DIR,
    REPO_DIR,
    build_allowed_command,
    edit_file,
    git_diff,
    git_status,
    safe_path,
)


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
        ("python -m pytest -q", ["python", "-m", "pytest", "-q"]),
        ("pytest", ["pytest"]),
        ("pytest -q", ["pytest", "-q"]),
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
        'python -c "print(1)"',
        "python -m http.server",
        "python -m pytest --collect-only",
        "python README.md",
        "python hello.py --outside",
        "pytest --collect-only",
        "rm -rf .",
        "git reset --hard",
        "git status --untracked-files=all",
        "git diff -- ../backend",
    ],
)
def test_build_allowed_command_blocks_unsafe_commands(command):
    args, error = build_allowed_command(command)

    assert args is None
    assert error


def test_edit_file_replaces_text_without_printing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("backend.tools.safety.BASE_DIR", tmp_path)
    target = tmp_path / "hello.py"
    target.write_text('print("Student")\n', encoding="utf-8")

    result = edit_file("hello.py", "Student", "Class")

    assert result == "Edited hello.py: replaced one occurrence."
    assert target.read_text(encoding="utf-8") == 'print("Class")\n'
    assert capsys.readouterr().out == ""


def test_git_diff_uses_argv_without_shell(monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return CompletedProcess(
            args=args[0], returncode=0, stdout="diff output", stderr=""
        )

    monkeypatch.setattr("backend.tools.git.subprocess.run", fake_run)

    assert git_diff() == "diff output"
    assert calls[0][0][0] == ["git", "diff", "--", BASE_DIR.name]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["cwd"] == REPO_DIR


def test_git_diff_reports_missing_git(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("backend.tools.git.subprocess.run", fake_run)

    assert git_diff().startswith("Error: git is not installed")


def test_git_diff_rejects_arguments():
    assert (
        git_diff("README.md")
        == "Error: git_diff does not accept arguments. Use git_diff()."
    )


def test_git_status_uses_argv_without_shell(monkeypatch):
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return CompletedProcess(
            args=args[0], returncode=0, stdout=" M file.py", stderr=""
        )

    monkeypatch.setattr("backend.tools.git.subprocess.run", fake_run)

    assert git_status() == " M file.py"
    assert calls[0][0][0] == ["git", "status", "--short", "--", BASE_DIR.name]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["cwd"] == REPO_DIR


def test_git_status_reports_missing_git(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("backend.tools.git.subprocess.run", fake_run)

    assert git_status().startswith("Error: git is not installed")


def test_git_status_rejects_arguments():
    assert (
        git_status("--short")
        == "Error: git_status does not accept arguments. Use git_status()."
    )
