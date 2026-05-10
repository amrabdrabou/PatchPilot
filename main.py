from agent import run_agent
from config import MAX_STEPS, MAX_TOOL_CALLS


def main():
    task = input("What should the agent do? ")
    run_agent(
        task,
        max_steps=MAX_STEPS,
        max_tool_calls=MAX_TOOL_CALLS,
    )


if __name__ == "__main__":
    main()