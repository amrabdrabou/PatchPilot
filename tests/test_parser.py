# Verifies homemade ReAct action parsing.
from backend.parser import is_final_answer, parse_action


def test_parse_action_with_one_argument():
    result = parse_action('Thought: read it\nAction: read_file("README.md")')

    assert result == ("read_file", ["README.md"])


def test_parse_action_with_multiple_arguments():
    result = parse_action('Action: edit_file("hello.py", "Student", "Class")')

    assert result == ("edit_file", ["hello.py", "Student", "Class"])


def test_parse_action_with_no_arguments():
    result = parse_action("Action: git_status()")

    assert result == ("git_status", [])


def test_parse_action_returns_none_for_invalid_arguments():
    result = parse_action("Action: read_file(README.md)")

    assert result is None


def test_parse_action_returns_none_when_no_action_exists():
    result = parse_action("Thought: I should answer directly.")

    assert result is None


def test_parse_action_ignores_trailing_parentheses_after_action():
    result = parse_action('Action: read_file("file.py")\n\nTrailing text with (parens)')

    assert result == ("read_file", ["file.py"])


def test_parse_action_accepts_single_quoted_strings():
    result = parse_action("Action: read_file('README.md')")

    assert result == ("read_file", ["README.md"])


def test_parse_action_accepts_multiline_string_arguments():
    result = parse_action('Action: edit_file("a.py", """old\ntext""", """new\ntext""")')

    assert result == ("edit_file", ["a.py", "old\ntext", "new\ntext"])


def test_is_final_answer_requires_line_start():
    assert is_final_answer("Thought: I should not say Final Answer: yet") is False
    assert is_final_answer("Thought: done\nFinal Answer: ready") is True
