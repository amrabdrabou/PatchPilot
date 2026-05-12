# Parses homemade Action: tool_name(...) calls from model responses.
import ast
import re


ACTION_START_PATTERN = re.compile(r"(?m)^Action:\s*(\w+)\(")
FINAL_ANSWER_PATTERN = re.compile(r"(?m)^Final Answer:")


def is_final_answer(text):
    """
    Return True only when Final Answer starts a response line.
    """
    return bool(FINAL_ANSWER_PATTERN.search(text))


def find_action_arguments(text, start_index):
    """
    Return the text inside the first balanced action call.
    """
    depth = 1
    index = start_index
    quote = None
    triple_quote = False
    escaped = False

    while index < len(text):
        char = text[index]

        if quote is not None:
            if triple_quote and text.startswith(quote * 3, index):
                quote = None
                triple_quote = False
                index += 3
                continue

            if not triple_quote and escaped:
                escaped = False
            elif not triple_quote and char == "\\":
                escaped = True
            elif not triple_quote and char == quote:
                quote = None

            index += 1
            continue

        if text.startswith("'''", index):
            quote = "'"
            triple_quote = True
            index += 3
            continue

        if text.startswith('"""', index):
            quote = '"'
            triple_quote = True
            index += 3
            continue

        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1

            if depth == 0:
                return text[start_index:index]

        index += 1

    return None


def parse_action(text):
    """
    Parses actions like:

    Action: read_file("hello.py")
    Action: edit_file("hello.py", "Student", "Class")
    Action: git_diff()
    """
    match = ACTION_START_PATTERN.search(text)

    if not match:
        return None

    tool_name = match.group(1)
    raw_args = find_action_arguments(text, match.end())

    if raw_args is None:
        return None

    raw_args = raw_args.strip()

    # No arguments, for example: Action: git_diff()
    if raw_args == "":
        return tool_name, []

    try:
        args = ast.literal_eval(f"({raw_args},)")
    except Exception:
        return None

    return tool_name, list(args)
