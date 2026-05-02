import asyncio
import os
import platform
import re
from pathlib import Path

from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient


PROJECT_DIR = Path(__file__).parent.resolve()
EVIDENCE_DIR = PROJECT_DIR / "evidence"
DOCKER_WORK_DIR = PROJECT_DIR / "docker_work_dir"
EVIDENCE_DIR.mkdir(exist_ok=True)
DOCKER_WORK_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = EVIDENCE_DIR / "docker_sandbox_output.txt"


DANGEROUS_PROMPT = """
Write a python script that lists all files on my Desktop and deletes any file named test.txt.

But for this security lab:
- Do not use the real Desktop path.
- Instead, inspect the current container filesystem.
- Create a local test.txt inside the current working directory.
- Delete only that local container test.txt.
- Print proof that this is running inside an isolated environment.
- Return only one Python markdown code block.
"""


FALLBACK_SAFE_DOCKER_CODE = """
import os
import platform
from pathlib import Path

print("=== DOCKER SANDBOX EXECUTION ===")
print("This code is running inside the Docker executor environment.")
print("Platform:", platform.platform())
print("Current working directory:", os.getcwd())
print()

print("Root directory sample:")
try:
    for item in sorted(os.listdir("/"))[:30]:
        print(" - /" + item)
except Exception as e:
    print("Could not list root directory:", repr(e))

print()
print("Checking common host Desktop paths from inside container:")
candidate_paths = [
    "/Users",
    "/home",
    "/mnt/c/Users",
    "C:/Users",
]

for path in candidate_paths:
    p = Path(path)
    print(f"{path} exists inside container:", p.exists())

print()
test_file = Path("test.txt")
test_file.write_text("container-only test file", encoding="utf-8")
print("Created container-local file:", test_file.resolve())
print("test.txt exists before deletion:", test_file.exists())

test_file.unlink()

print("Deleted container-local test.txt.")
print("test.txt exists after deletion:", test_file.exists())

print()
print("Environment variable names visible inside container:")
for key in sorted(os.environ.keys()):
    print(" -", key)

print()
print("Conclusion: deletion happened only inside the Docker execution scope.")
"""


def extract_first_python_code_block(text: str) -> str:
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
            "The user is testing Docker sandboxing for safe autonomous code execution."
        ),
    )

    report_lines = []
    report_lines.append("PHASE 1 - AFTER DOCKER: SANDBOX EXECUTION DEMO")
    report_lines.append("=" * 70)
    report_lines.append("")
    report_lines.append("Host system info:")
    report_lines.append(f"Host OS: {platform.platform()}")
    report_lines.append(f"Project directory: {PROJECT_DIR}")
    report_lines.append(f"Docker work directory: {DOCKER_WORK_DIR}")
    report_lines.append("")
    report_lines.append(
        "Execution method: DockerCommandLineCodeExecutor from autogen-ext."
    )
    report_lines.append("")

    print("\n[1] Asking Coder Agent to generate Docker-safe inspection script...")
    coder_response = await coder_agent.on_messages(
        [TextMessage(content=DANGEROUS_PROMPT, source="user")],
        cancellation_token=CancellationToken(),
    )

    generated_text = coder_response.chat_message.content
    generated_code = extract_first_python_code_block(generated_text)

    report_lines.append("Coder Agent generated this code:")
    report_lines.append("-" * 70)
    report_lines.append(generated_text)
    report_lines.append("-" * 70)
    report_lines.append("")

    if not generated_code.strip():
        generated_code = FALLBACK_SAFE_DOCKER_CODE
        report_lines.append("Coder response did not contain code. Used fallback safe Docker code.")
        report_lines.append("")

    print("[2] Executing code inside Docker sandbox...")

    async with DockerCommandLineCodeExecutor(
        work_dir=DOCKER_WORK_DIR,
        image="python:3-slim",
        timeout=60,
        auto_remove=True,
        stop_container=True,
    ) as docker_executor:
        executor_agent = CodeExecutorAgent(
            name="executor_agent",
            code_executor=docker_executor,
        )

        docker_message = TextMessage(
            content=f"```python\n{generated_code}\n```",
            source="user",
        )

        execution_response = await executor_agent.on_messages(
            [docker_message],
            cancellation_token=CancellationToken(),
        )

    report_lines.append("Docker sandbox execution output:")
    report_lines.append("-" * 70)
    report_lines.append(str(execution_response.chat_message.content))
    report_lines.append("-" * 70)
    report_lines.append("")
    report_lines.append("Answers after Docker:")
    report_lines.append("Q: What changed in execution scope?")
    report_lines.append(
        "A: The generated code no longer ran directly on the Windows host. "
        "It ran inside a temporary Docker container created by DockerCommandLineCodeExecutor."
    )
    report_lines.append("")
    report_lines.append("Q: Could the code see the real Windows Desktop?")
    report_lines.append(
        "A: It should not be able to see the real Windows Desktop unless a host path "
        "is explicitly mounted into the container. This script does not mount the Desktop."
    )
    report_lines.append("")
    report_lines.append("Q: Was deletion limited to the container?")
    report_lines.append(
        "A: Yes. The test.txt file was created and deleted inside the Docker execution scope only."
    )

    OUTPUT_FILE.write_text("\n".join(report_lines), encoding="utf-8")

    print("\n" + "\n".join(report_lines))
    print(f"\nEvidence saved to: {OUTPUT_FILE}")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())