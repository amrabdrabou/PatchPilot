# Verifies command execution safety after splitting the tool package.
from subprocess import CompletedProcess, TimeoutExpired

import backend.tools.command as command_tools
import backend.tools.safety as safety


def test_run_bash_logs_blocked_commands(monkeypatch, tmp_path):
    log_file = tmp_path / "commands.log"
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", log_file)

    result = command_tools.run_bash("rm -rf .")

    assert result.startswith("Blocked command:")
    assert "BLOCKED: rm -rf ." in log_file.read_text(encoding="utf-8")


def test_run_bash_logs_stockholm_timestamp(monkeypatch, tmp_path):
    log_file = tmp_path / "commands.log"
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", log_file)
    monkeypatch.setattr(command_tools, "stockholm_now_iso", lambda: "2026-05-11T12:00:00+02:00")

    command_tools.run_bash("rm -rf .")

    assert "[2026-05-11T12:00:00+02:00] BLOCKED: rm -rf ." in log_file.read_text(
        encoding="utf-8"
    )


def test_run_bash_uses_argv_without_shell(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", tmp_path / "commands.log")

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(command_tools.subprocess, "run", fake_run)

    assert command_tools.run_bash("pytest") == "ok"
    assert calls[0][0][0] == ["pytest"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["cwd"] == tmp_path


def test_run_bash_truncates_long_output(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", tmp_path / "commands.log")
    monkeypatch.setattr(command_tools, "MAX_COMMAND_OUTPUT_CHARS", 5)

    def fake_run(*args, **kwargs):
        return CompletedProcess(args=args[0], returncode=0, stdout="abcdefg", stderr="")

    monkeypatch.setattr(command_tools.subprocess, "run", fake_run)

    assert command_tools.run_bash("pytest") == "abcde"


def test_run_bash_logs_timeouts(monkeypatch, tmp_path):
    log_file = tmp_path / "commands.log"
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", log_file)

    def fake_run(*args, **kwargs):
        raise TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr(command_tools.subprocess, "run", fake_run)

    assert command_tools.run_bash("pytest") == "Error: command timed out."
    log_text = log_file.read_text(encoding="utf-8")
    assert "ALLOWED: pytest" in log_text
    assert "TIMEOUT: pytest" in log_text


def test_run_bash_reports_missing_program(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", tmp_path / "commands.log")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(command_tools.subprocess, "run", fake_run)

    assert command_tools.run_bash("pytest") == "Error: command program is not installed: pytest."


def test_log_command_failure_does_not_raise(monkeypatch, tmp_path):
    blocked_log_path = tmp_path / "missing" / "commands.log"
    monkeypatch.setattr(command_tools, "COMMAND_LOG_FILE", blocked_log_path)
    monkeypatch.setattr(command_tools.Path, "open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))

    command_tools.log_command("pytest", "ALLOWED")
