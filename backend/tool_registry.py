# Maps model-requested tool names to safe Python functions.
from backend.tools import (
    list_files,
    read_file,
    run_bash,
    search_files,
    edit_file,
    git_diff,
    git_status,
)


TOOLS = {
    "list_files": {
        "function": list_files,
        "description": "Lists files inside a directory.",
        "example": 'Action: list_files(".")',
    },
    "read_file": {
        "function": read_file,
        "description": "Reads a file inside the project folder.",
        "example": 'Action: read_file("README.md")',
    },
    "run_bash": {
        "function": run_bash,
        "description": "Runs a bash command inside the project folder.",
        "example": 'Action: run_bash("python hello.py")',
    },
    "search_files": {
        "function": search_files,
        "description": "Searches for text inside files in the project folder.",
        "example": 'Action: search_files("greet")',
    },
    "edit_file": {
        "function": edit_file,
        "description": "Edits a file by replacing old_text with new_text.",
        "example": 'Action: edit_file("hello.py", "Student", "Class")',
    },
    "git_diff": {
        "function": git_diff,
        "description": "Shows the git diff for changed files in the project folder.",
        "example": "Action: git_diff()",
    },
    "git_status": {
        "function": git_status,
        "description": "Shows a short git status for the project folder. Takes no arguments.",
        "example": "Action: git_status()",
    },
}


def run_tool(tool_name, arguments):
    """
    Runs the Python function that matches the tool name.
    """
    tool = TOOLS.get(tool_name)

    if tool is None:
        return f"Error: unknown tool '{tool_name}'."

    try:
        return tool["function"](*arguments)
    except TypeError as error:
        return f"Error: wrong arguments for tool '{tool_name}': {error}"
    except Exception as error:
        return f"Error while running tool '{tool_name}': {error}"


def get_tool_descriptions():
    """
    Builds a text description of all available tools for the system prompt.
    """
    descriptions = []

    for index, (tool_name, tool_info) in enumerate(TOOLS.items(), start=1):
        descriptions.append(
            f"{index}. {tool_name}(argument)\n"
            f"   - {tool_info['description']}\n"
            f"   - Example: {tool_info['example']}"
        )

    return "\n\n".join(descriptions)
