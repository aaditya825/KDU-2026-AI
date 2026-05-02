import asyncio
import os
import re
import platform
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor


PROJECT_DIR = Path(__file__).parent.resolve()
EVIDENCE_DIR = PROJECT_DIR / "evidence"
DOCKER_WORK_DIR = PROJECT_DIR / "phase2_docker_work_dir"

EVIDENCE_DIR.mkdir(exist_ok=True)
DOCKER_WORK_DIR.mkdir(exist_ok=True)


TASK = """
Write a Python script for a secure Docker sandbox lab.

The script must:
1. Print whether /.dockerenv exists.
2. Print OS and current working directory.
3. List files in the current working directory.
4. Check whether these host paths are visible:
   - C:/Users/Dell/Desktop
   - /mnt/c/Users/Dell/Desktop
   - /Users/Dell/Desktop
5. Create test.txt only in the current working directory.
6. Delete only that local test.txt.
7. Print whether test.txt exists before and after deletion.
8. Do not access the real Desktop.
9. Do not delete anything outside the current working directory.

Return only one Python markdown code block.
"""


AUDIT_NOTES = """
You are acting as the Web Surfer / Audit Agent.

Use these documentation-based rules:
- Code must run through DockerCommandLineCodeExecutor.
- Code must not run on the host OS.
- Human approval is required before execution.
- Code must not access the real Windows Desktop.
- Deletion must be limited to local test.txt inside the Docker working directory.

Audit and improve the generated code.
Return a short audit summary and one final Python markdown code block.
"""


FALLBACK_CODE = """
import os
import platform
from pathlib import Path

print("=== PHASE 2: HITL + AUDIT + DOCKER SANDBOX ===")
print("Docker flag /.dockerenv exists:", Path("/.dockerenv").exists())
print("Platform:", platform.platform())
print("Current working directory:", os.getcwd())

print("\\nFiles in current working directory:")
for item in sorted(Path(".").iterdir()):
    print(" -", item.name)

print("\\nChecking host Desktop paths from inside container:")
for path in ["C:/Users/Dell/Desktop", "/mnt/c/Users/Dell/Desktop", "/Users/Dell/Desktop"]:
    print(f"{path} exists inside container:", Path(path).exists())

target = Path("test.txt")
target.write_text("container-only test file", encoding="utf-8")

print("\\nCreated:", target.resolve())
print("test.txt exists before deletion:", target.exists())

target.unlink()

print("Deleted container-local test.txt.")
print("test.txt exists after deletion:", target.exists())
print("\\nConclusion: Approved code ran only inside Docker.")
"""


def get_model_client():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")

    return OpenAIChatCompletionClient(
        model="gemini-2.5-flash",
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={
            "vision": True,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python|py)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def code_block(code: str) -> str:
    return f"```python\n{code.strip()}\n```"


def is_code_safe(code: str) -> tuple[bool, list[str]]:
    risky_patterns = [
        "Path.home()",
        "expanduser(",
        "Desktop",
        "Documents",
        "Downloads",
        "C:/",
        "C:\\",
        "/mnt/c",
        "shutil.rmtree",
        "subprocess",
        "os.system",
        "Popen",
        "requests.",
        "urllib.",
        "socket.",
    ]

    problems = [p for p in risky_patterns if p in code]

    if problems:
        return False, problems

    return True, []


async def ask_approval(timeout_seconds: int = 120) -> tuple[bool, str]:
    try:
        answer = await asyncio.wait_for(
            asyncio.to_thread(input, "\nExecute this code? (Y/N): "),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return False, "TIMEOUT"

    return answer.strip().lower() in {"y", "yes"}, answer


async def main():
    model_client = get_model_client()

    report = [
        "PHASE 2 - HITL + WEB SURFER / AUDIT + DOCKER EXECUTION",
        "=" * 70,
        f"Timestamp: {datetime.now()}",
        f"Host OS: {platform.platform()}",
        f"Project directory: {PROJECT_DIR}",
        f"Docker work directory: {DOCKER_WORK_DIR}",
        "",
    ]

    coder = AssistantAgent(
        name="coder_agent",
        model_client=model_client,
        system_message="You are the Coder Agent. Generate safe Python code for Docker execution only.",
    )

    auditor = AssistantAgent(
        name="web_surfer_audit_agent",
        model_client=model_client,
        system_message="You are the Web Surfer / Audit Agent. Review code for safety before execution.",
    )

    print("\n[1] Coder Agent generating code...")
    coder_response = await coder.on_messages(
        [TextMessage(content=TASK, source="user")],
        cancellation_token=CancellationToken(),
    )

    generated_text = coder_response.chat_message.content
    generated_code = extract_code(generated_text)

    report += [
        "Coder Agent output:",
        "-" * 70,
        generated_text,
        "-" * 70,
        "",
    ]

    print("[2] Audit Agent reviewing code...")
    audit_prompt = f"{AUDIT_NOTES}\n\nGenerated code:\n{code_block(generated_code)}"

    audit_response = await auditor.on_messages(
        [TextMessage(content=audit_prompt, source="user")],
        cancellation_token=CancellationToken(),
    )

    audited_text = audit_response.chat_message.content
    audited_code = extract_code(audited_text) or FALLBACK_CODE

    report += [
        "Audit Agent output:",
        "-" * 70,
        audited_text,
        "-" * 70,
        "",
    ]

    safe, problems = is_code_safe(audited_code)

    if not safe:
        print("[Safety] Risky patterns found. Using fallback safe code.")
        report += [
            "Safety validation failed.",
            f"Risky patterns found: {problems}",
            "Fallback safe code selected.",
            "",
        ]
        audited_code = FALLBACK_CODE
    else:
        report += ["Safety validation passed.", ""]

    print("\n[3] Final code proposed for execution:")
    print("=" * 70)
    print(code_block(audited_code))
    print("=" * 70)

    report += [
        "Final code shown to human:",
        "-" * 70,
        code_block(audited_code),
        "-" * 70,
        "",
    ]

    print("\n[4] Human approval required.")
    approved, answer = await ask_approval()

    report += [
        "HITL approval:",
        "Prompt: Execute this code? (Y/N)",
        f"Human response: {answer}",
        f"Approved: {approved}",
        "",
    ]

    if not approved:
        print("\nExecution rejected. No code was executed.")

        report += [
            "Execution skipped.",
            "Docker executor was not called.",
            "",
            "Phase 2 answers:",
            "HITL was implemented using an explicit Y/N approval gate before Docker execution.",
            "The program waits for human input before calling the Executor Agent.",
            "If input times out, execution is rejected by default.",
            "If the user rejects execution, no code runs.",
        ]

        output_file = EVIDENCE_DIR / "phase2_hitl_rejected_output.txt"
        output_file.write_text("\n".join(report), encoding="utf-8")

        print(f"Evidence saved to: {output_file}")
        await model_client.close()
        return

    print("\n[5] Approved. Running code inside Docker...")

    async with DockerCommandLineCodeExecutor(
        work_dir=DOCKER_WORK_DIR,
        image="python:3-slim",
        timeout=60,
        auto_remove=True,
        stop_container=True,
    ) as docker_executor:
        executor = CodeExecutorAgent(
            name="executor_agent",
            code_executor=docker_executor,
        )

        execution_response = await executor.on_messages(
            [TextMessage(content=code_block(audited_code), source="user")],
            cancellation_token=CancellationToken(),
        )

    execution_output = str(execution_response.chat_message.content)

    print("\n[6] Docker execution output:")
    print("=" * 70)
    print(execution_output)
    print("=" * 70)

    report += [
        "Docker execution output:",
        "-" * 70,
        execution_output,
        "-" * 70,
        "",
        "Phase 2 answers:",
        "HITL was implemented using an explicit Y/N approval gate before Docker execution.",
        "The program waits for human input before calling the Executor Agent.",
        "If input times out, execution is rejected by default.",
        "If the user rejects execution, no code runs.",
        "If the user approves execution, the code runs inside DockerCommandLineCodeExecutor.",
    ]

    output_file = EVIDENCE_DIR / "phase2_hitl_approved_output.txt"
    output_file.write_text("\n".join(report), encoding="utf-8")

    print(f"Evidence saved to: {output_file}")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())