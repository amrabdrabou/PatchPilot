from backend.prompts import build_system_prompt
from backend.model_client import ask_model
from backend.tool_registry import run_tool
from backend.parser import parse_action


def run_agent(user_task, max_steps=5, max_tool_calls=3):
    """
    Main ReAct loop.
    """
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_task},
    ]

    model_calls = 0
    tool_calls = 0
    tool_usage = {}

    for step in range(max_steps):
        print(f"\n--- Step {step + 1} ---")

        assistant_message = ask_model(messages)
        model_calls += 1

        print(assistant_message)

        messages.append({
            "role": "assistant",
            "content": assistant_message,
        })

        if "Final Answer:" in assistant_message:
            print("\nAgent finished.")
            print(f"Model calls used: {model_calls}")
            print(f"Tool calls used: {tool_calls}")

            for tool_name, count in tool_usage.items():
                print(f"Tool {tool_name} used: {count}")

            return

        action = parse_action(assistant_message)

        if action is None:
            observation = "Error: No valid action found. Use format: Action: tool_name(\"argument\")"

        else:
            if tool_calls >= max_tool_calls:
                observation = "Error: Tool call limit reached. You must now give a Final Answer."

            else:
                tool_name, arguments = action

                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

                print(f"Tool used: {tool_name}")
                print(f"Tool arguments: {arguments}")

                result = run_tool(tool_name, arguments)
                tool_calls += 1

                observation = f"Observation: {result}"

        print(observation)

        messages.append({
            "role": "user",
            "content": observation,
        })

    print("\nAgent stopped because it reached the maximum number of steps.")
    print(f"Model calls used: {model_calls}")
    print(f"Tool calls used: {tool_calls}")

    for tool_name, count in tool_usage.items():
        print(f"Tool {tool_name} used: {count}")
