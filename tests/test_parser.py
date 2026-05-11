# Verifies homemade ReAct action parsing.
from backend.parser import parse_action


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
