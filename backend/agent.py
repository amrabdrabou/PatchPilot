from backend.prompts import build_system_prompt
from backend.model_client import ask_model_result as ask_model
from backend.model_results import (
    add_token_usage,
    build_observation,
    normalize_model_result,
)
from backend.tool_registry import run_tool
from backend.parser import is_final_answer, parse_action
from backend.run_logger import build_run_log_record, stockholm_now_iso, write_run_log


APPROVAL_REQUIRED_TOOLS = {
    "run_bash",
    "edit_file",
}

MAX_TRACE_CONTENT_CHARS = 500


def compact_content(content):
    """
    Limit CLI trace content before writing it to run logs.
    """
    text = str(content)

    if len(text) <= MAX_TRACE_CONTENT_CHARS:
        return text

    return text[:MAX_TRACE_CONTENT_CHARS] + "\n... trace content truncated ..."


def ask_cli_approval(tool_name, arguments):
    """
    Ask the terminal user before running tools that can change files or run commands.
    """
    print(f"\nApproval required for tool: {tool_name}")
    print(f"Arguments: {arguments}")

    answer = input("Approve this tool call? Type 'yes' to approve: ")

    return answer.strip().lower() == "yes"


def run_agent(user_task, max_steps=5, max_tool_calls=3):
    """
    Run the terminal ReAct loop until a final answer or limit is reached.
    """
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_task},
    ]

    model_calls = 0
    tool_calls = 0
    tool_usage = {}
    token_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    trace = []
    started_at = stockholm_now_iso()
    run_id = f"cli-{started_at}"

    def record_trace(step, event_type, content, extra=None):
        """
        Append one compact CLI trace entry.
        """
        entry = {
            "time": stockholm_now_iso(),
            "step": step,
            "type": event_type,
            "content": compact_content(content),
        }

        if extra:
            entry.update(extra)

        trace.append(entry)

    def log_cli_run(status, final_answer, steps):
        """
        Write a structured log entry for this CLI run.
        """
        try:
            write_run_log(
                build_run_log_record(
                    run_id=run_id,
                    task=user_task,
                    started_at=started_at,
                    status=status,
                    final_answer=final_answer,
                    steps=steps,
                    max_steps=max_steps,
                    model_calls=model_calls,
                    tool_calls=tool_calls,
                    max_tool_calls=max_tool_calls,
                    tool_usage=tool_usage,
                    token_usage=token_usage,
                    trace=trace,
                    interface="cli",
                )
            )
        except Exception:
            pass

    for step in range(max_steps):
        print(f"\n--- Step {step + 1} ---")

        try:
            assistant_message, usage = normalize_model_result(ask_model(messages))
            add_token_usage(token_usage, usage)
            model_calls += 1
        except Exception as error:
            final_answer = f"Agent stopped after a handled model error: {type(error).__name__}."
            print(final_answer)
            record_trace(step + 1, "error", final_answer)
            log_cli_run("error", final_answer, step + 1)
            return

        print(assistant_message)
        record_trace(step + 1, "assistant_message", assistant_message)

        messages.append({
            "role": "assistant",
            "content": assistant_message,
        })

        if is_final_answer(assistant_message):
            print("\nAgent finished.")
            print(f"Model calls used: {model_calls}")
            print(f"Tool calls used: {tool_calls}")
            print(f"Tokens used: {token_usage['total_tokens']}")

            for tool_name, count in tool_usage.items():
                print(f"Tool {tool_name} used: {count}")

            log_cli_run("final", assistant_message, step + 1)
            return

        action = parse_action(assistant_message)

        if action is None:
            observation = "Error: No valid action found. Use format: Action: tool_name(\"argument\")"
            record_trace(step + 1, "error", observation)

        else:
            if tool_calls >= max_tool_calls:
                observation = "Error: Tool call limit reached. You must now give a Final Answer."
                record_trace(step + 1, "error", observation)

            else:
                tool_name, arguments = action

                print(f"Tool used: {tool_name}")
                print(f"Tool arguments: {arguments}")
                record_trace(
                    step + 1,
                    "tool_call",
                    f"{tool_name}({arguments})",
                    {"tool_name": tool_name},
                )

                if tool_name in APPROVAL_REQUIRED_TOOLS and not ask_cli_approval(tool_name, arguments):
                    result = f"User rejected tool call: {tool_name}({arguments})"
                else:
                    try:
                        result = run_tool(tool_name, arguments)
                    except Exception as error:
                        result = f"Tool execution failed safely: {type(error).__name__}."
                    tool_calls += 1
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

                observation = build_observation(result)
                record_trace(step + 1, "observation", observation)

        print(observation)

        messages.append({
            "role": "user",
            "content": observation,
        })

    print("\nAgent stopped because it reached the maximum number of steps.")
    print(f"Model calls used: {model_calls}")
    print(f"Tool calls used: {tool_calls}")
    print(f"Tokens used: {token_usage['total_tokens']}")

    for tool_name, count in tool_usage.items():
        print(f"Tool {tool_name} used: {count}")

    log_cli_run(
        "stopped",
        "Agent stopped because it reached the maximum number of steps.",
        max_steps,
    )
