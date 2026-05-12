# Verifies sandboxed file tools after splitting the tool package.
import backend.tools.file as file_tools
import backend.tools.safety as safety


def test_list_files_reports_missing_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)

    assert file_tools.list_files("missing") == "Error: missing does not exist."


def test_list_files_reports_non_directories(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    (tmp_path / "hello.py").write_text("print('hi')\n", encoding="utf-8")

    assert file_tools.list_files("hello.py") == "Error: hello.py is not a directory."


def test_list_files_returns_stable_sorted_output(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    (tmp_path / "zeta.py").write_text("", encoding="utf-8")
    (tmp_path / "alpha").mkdir()
    (tmp_path / "Beta.py").write_text("", encoding="utf-8")

    assert file_tools.list_files(".") == "alpha/\nBeta.py\nzeta.py"


def test_read_file_reports_missing_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)

    assert file_tools.read_file("missing.py") == "Error: missing.py does not exist."


def test_read_file_truncates_large_output(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    monkeypatch.setattr(file_tools, "MAX_COMMAND_OUTPUT_CHARS", 5)
    (tmp_path / "big.txt").write_text("abcdefg", encoding="utf-8")

    assert file_tools.read_file("big.txt") == "abcde\n... output truncated ..."


def test_read_file_reports_non_utf8_files(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe")

    assert file_tools.read_file("binary.bin") == "Error: binary.bin is not a UTF-8 text file."


def test_search_files_skips_binary_files(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe\x00needle")

    assert file_tools.search_files("needle") == "No matches found for: needle"


def test_search_files_reports_matching_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    (tmp_path / "hello.py").write_text("first\nNeedle here\n", encoding="utf-8")

    assert file_tools.search_files("needle") == "hello.py:2: Needle here"


def test_search_files_skips_large_files(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    monkeypatch.setattr(file_tools, "MAX_SEARCH_FILE_BYTES", 5)
    (tmp_path / "large.txt").write_text("needle", encoding="utf-8")

    assert file_tools.search_files("needle") == "No matches found for: needle"


def test_edit_file_replaces_only_first_match(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    target = tmp_path / "hello.py"
    target.write_text("name = 'Student'\nprint('Student')\n", encoding="utf-8")

    result = file_tools.edit_file("hello.py", "Student", "Class")

    assert result == "Edited hello.py: replaced one occurrence."
    assert target.read_text(encoding="utf-8") == "name = 'Class'\nprint('Student')\n"


def test_edit_file_rejects_empty_old_text(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    target = tmp_path / "hello.py"
    target.write_text("print('Student')\n", encoding="utf-8")

    result = file_tools.edit_file("hello.py", "", "Class")

    assert result == "Error: old_text cannot be empty. No changes made."
    assert target.read_text(encoding="utf-8") == "print('Student')\n"


def test_edit_file_reports_non_utf8_files(monkeypatch, tmp_path):
    monkeypatch.setattr(safety, "BASE_DIR", tmp_path)
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe")

    result = file_tools.edit_file("binary.bin", "old", "new")

    assert result == "Error: binary.bin is not a UTF-8 text file. No changes made."
