import ast
import re


def parse_action(text):
    """
    Parses actions like:

    Action: read_file("hello.py")
    Action: edit_file("hello.py", "Student", "Class")
    Action: git_diff()
    """
    pattern = r"Action:\s*(\w+)\((.*)\)"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return None

    tool_name = match.group(1)
    raw_args = match.group(2).strip()

    if raw_args == "":
        return tool_name, []

    try:
        args = ast.literal_eval(f"({raw_args},)")
    except Exception:
        return None

    return tool_name, list(args)