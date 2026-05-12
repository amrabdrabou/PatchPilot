# Provides a small CLI entry point for running the backend agent loop.
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agent import run_agent
from backend.config import MAX_STEPS, MAX_TOOL_CALLS


def print_help():
    """
    Print available CLI commands and example tasks.
    """
    print("""
Commands:
  /help    Show this help message
  /exit    Exit the program

Examples:
  Run hello.py and tell me what it prints.
  What files have changed?
  Show me the git diff.
""")


def main():
    """
    Run the interactive terminal entry point for PatchPilot.
    """
    print("ReAct Developer Agent")
    print("Type /help for commands.")
    print("Type /exit to quit.")

    while True:
        task = input("\nWhat should the agent do? ")

        if not task.strip():
            continue

        if task == "/exit":
            print("Goodbye.")
            break

        if task == "/help":
            print_help()
            continue

        run_agent(
            task,
            max_steps=MAX_STEPS,
            max_tool_calls=MAX_TOOL_CALLS,
        )


if __name__ == "__main__":
    main()
