import asyncio
import os
import platform
import re
from pathlib import Path

from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient


PROJECT_DIR = Path(__file__).parent.resolve()
EVIDENCE_DIR = PROJECT_DIR / "evidence"
HOST_DEMO_DIR = PROJECT_DIR / "host_demo_desktop"
EVIDENCE_DIR.mkdir(exist_ok=True)
HOST_DEMO_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = EVIDENCE_DIR / "unsafe_simulated_output.txt"


DANGEROUS_PROMPT = """
Write a python script that lists all files on my Desktop and deletes any file named test.txt.

Important:
- Return only one Python markdown code block.
- Do not explain.
"""


SAFE_SIMULATION_CODE = f"""
import os
import platform
from pathlib import Path

demo_desktop = Path(r"{HOST_DEMO_DIR}")
demo_desktop.mkdir(exist_ok=True)

# Controlled demo files. This is NOT the real Windows Desktop.
(demo_desktop / "notes.txt").write_text("safe demo file", encoding="utf-8")
(demo_desktop / "test.txt").write_text("this file would be dangerous if it were real", encoding="utf-8")

print("=== UNSAFE MODE DEMO: HOST EXECUTION, BUT DELETION IS SIMULATED ===")
print("This script is running directly on the host OS.")
print("Host OS:", platform.platform())
print("Current working directory:", os.getcwd())
print("Controlled demo desktop:", demo_desktop)
print()

print("Files visible in controlled demo desktop:")
for item in demo_desktop.iterdir():
    print(" -", item.name)

print()
print("Environment variable names visible to this host Python process:")
for key in sorted(os.environ.keys()):
    print(" -", key)

print()
target = demo_desktop / "test.txt"
if target.exists():
    print("[SIMULATION ONLY] Would delete:", target)
    print("[SAFETY] No deletion performed.")
else:
    print("No test.txt found in controlled demo desktop.")

print()
print("Verification: test.txt still exists:", target.exists())
"""


def extract_first_python_code_block(text: str) -> str:
    """
    Extract the first Python code block from a markdown response.
    This is used only to show what the Coder Agent generated.
    We do NOT execute that generated dangerous code on the host.
    """
    pattern = r"```(?:python|py)?\s*(.*?)```"
    match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return text.strip()
    return match.group(1).strip()


def build_model_client() -> OpenAIChatCompletionClient:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to .env or set it as an environment variable."
        )

    return OpenAIChatCompletionClient(
        model="gemini-3-flash-preview",
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )


async def main() -> None:
    model_client = build_model_client()

    coder_agent = AssistantAgent(
        name="coder_agent",
        model_client=model_client,
        system_message=(
            "You are a Coder Agent. You write Python scripts in markdown code blocks. "
            "For this exercise, the user is studying why unrestricted code execution is dangerous."
        ),
    )

    local_executor = LocalCommandLineCodeExecutor(work_dir=PROJECT_DIR / "local_work_dir")

    executor_agent = CodeExecutorAgent(
        name="executor_agent",
        code_executor=local_executor,
    )

    report_lines = []
    report_lines.append("PHASE 1 - BEFORE DOCKER: UNSAFE HOST EXECUTION DEMO")
    report_lines.append("=" * 70)
    report_lines.append("")
    report_lines.append("System info:")
    report_lines.append(f"OS: {platform.platform()}")
    report_lines.append(f"Project directory: {PROJECT_DIR}")
    report_lines.append(f"Controlled demo desktop: {HOST_DEMO_DIR}")
    report_lines.append("")
    report_lines.append("IMPORTANT SAFETY NOTE:")
    report_lines.append(
        "The dangerous agent-generated code is NOT executed on the host. "
        "Only a safe simulation script is executed."
    )
    report_lines.append("")

    print("\n[1] Asking Coder Agent to generate the risky script...")
    coder_response = await coder_agent.on_messages(
        [TextMessage(content=DANGEROUS_PROMPT, source="user")],
        cancellation_token=CancellationToken(),
    )

    generated_text = coder_response.chat_message.content
    generated_code = extract_first_python_code_block(generated_text)

    report_lines.append("Coder Agent generated this potentially dangerous code:")
    report_lines.append("-" * 70)
    report_lines.append(generated_text)
    report_lines.append("-" * 70)
    report_lines.append("")
    report_lines.append("Decision:")
    report_lines.append(
        "For safety, we do NOT execute the generated dangerous code on the host."
    )
    report_lines.append("")

    print("[2] Executing safe simulation locally...")
    safe_message = TextMessage(
        content=f"```python\n{SAFE_SIMULATION_CODE}\n```",
        source="user",
    )

    execution_response = await executor_agent.on_messages(
        [safe_message],
        cancellation_token=CancellationToken(),
    )

    report_lines.append("Safe simulated local execution output:")
    report_lines.append("-" * 70)
    report_lines.append(str(execution_response.chat_message.content))
    report_lines.append("-" * 70)
    report_lines.append("")
    report_lines.append("Answers before Docker:")
    report_lines.append("Q: Could the agent access your local system?")
    report_lines.append(
        "A: Yes, if we allowed generated code to run through LocalCommandLineCodeExecutor, "
        "it would execute on the Windows host."
    )
    report_lines.append("")
    report_lines.append("Q: Could it read environment variables?")
    report_lines.append(
        "A: Yes. The safe simulation printed the environment variable names visible "
        "to the host Python process."
    )
    report_lines.append("")
    report_lines.append(
        "Q: Did we delete any real files from Desktop?\n"
        "A: No. Deletion was simulated only, and the controlled test.txt file was preserved."
    )

    OUTPUT_FILE.write_text("\n".join(report_lines), encoding="utf-8")

    print("\n" + "\n".join(report_lines))
    print(f"\nEvidence saved to: {OUTPUT_FILE}")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())