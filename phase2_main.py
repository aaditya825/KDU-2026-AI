import os
import yaml
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

from tools.unreliable_tool import UnreliableResearchTool

load_dotenv()


CONFIG_DIR = Path("config")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def get_gemini_llm() -> LLM:
    """
    Creates the Gemini LLM configuration for CrewAI.

    Use a cheaper Gemini model for development.
    Change the model if your Gemini account supports a different one.
    """

    return LLM(
        model="gemini/gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )


def get_llm() -> LLM:
    """
    Central model selector for Gemini-only execution.
    """

    return get_gemini_llm()


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """
    Loads a YAML configuration file and returns it as a dictionary.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_log(run_label: str, content: str) -> None:
    """
    Saves output or error logs into logs/ folder.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = LOG_DIR / f"phase2_{run_label}_{timestamp}.md"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(f"# PHASE 2 LOG - {run_label.upper()}\n\n")
        file.write(f"Generated at: {timestamp}\n\n")
        file.write("---\n\n")
        file.write(content)

    print(f"\nLog saved to: {file_path}")


def create_agents_from_yaml(llm: LLM) -> Dict[str, Agent]:
    """
    Creates CrewAI agents from config/agents.yaml.

    Tools are still assigned in Python because YAML cannot directly create
    Python tool objects.
    """

    agents_config = load_yaml(CONFIG_DIR / "agents.yaml")

    search_tool = SerperDevTool()
    unreliable_tool = UnreliableResearchTool()

    agents = {}

    for agent_name, config in agents_config.items():
        tools = []

        if agent_name == "researcher":
            tools = [search_tool, unreliable_tool]

        agents[agent_name] = Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            tools=tools,
            llm=llm,
            verbose=config.get("verbose", True),
            allow_delegation=config.get("allow_delegation", False),
        )

    return agents


def create_tasks_from_yaml(agents: Dict[str, Agent], inputs: Dict[str, str]) -> List[Task]:
    """
    Creates CrewAI tasks from config/tasks.yaml.

    This function also connects task context dependencies.

    Example:
    fact_check_task depends on research_task.
    writing_task depends on fact_check_task.
    """

    tasks_config = load_yaml(CONFIG_DIR / "tasks.yaml")

    created_tasks: Dict[str, Task] = {}

    for task_name, config in tasks_config.items():
        agent_key = config["agent"]

        description = config["description"].format(**inputs)
        expected_output = config["expected_output"].format(**inputs)

        context_task_names = config.get("context", [])
        context_tasks = [
            created_tasks[context_task_name]
            for context_task_name in context_task_names
        ]

        task = Task(
            description=description,
            expected_output=expected_output,
            agent=agents[agent_key],
            context=context_tasks,
        )

        created_tasks[task_name] = task

    return list(created_tasks.values())


def run_memory_enabled_crew(run_label: str, topic: str):
    """
    Runs the YAML-configured crew with memory=True.

    This is the main Phase 2 experiment.
    Run it multiple times to observe memory behavior.
    """

    print("\n" + "=" * 80)
    print(f"RUNNING PHASE 2 CREW: {run_label}")
    print("=" * 80)

    llm = get_llm()

    agents = create_agents_from_yaml(llm)

    inputs = {
        "topic": topic,
        "run_label": run_label,
    }

    tasks = create_tasks_from_yaml(agents, inputs)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        memory=True,
        verbose=True,
    )

    try:
        result = crew.kickoff()

        print("\n" + "=" * 80)
        print(f"PHASE 2 RESULT: {run_label}")
        print("=" * 80)
        print(result)

        save_log(run_label, str(result))

        return result

    except Exception as error:
        error_log = (
            f"Phase 2 crew failed during {run_label}.\n\n"
            f"Error type: {type(error).__name__}\n"
            f"Error message: {error}\n\n"
            "Traceback:\n"
            f"{traceback.format_exc()}"
        )

        print(error_log)
        save_log(f"{run_label}_error", error_log)

        return None


if __name__ == "__main__":
    topic = "Benefits and risks of using AI agents in software development"

    day_1_result = run_memory_enabled_crew(
        run_label="day_1",
        topic=topic,
    )

    day_2_result = run_memory_enabled_crew(
        run_label="day_2",
        topic=topic,
    )

    print("\n" + "=" * 80)
    print("PHASE 2 SUMMARY")
    print("=" * 80)

    if day_1_result is not None:
        print("Day 1 run completed successfully.")
    else:
        print("Day 1 run failed. Check logs/ for details.")

    if day_2_result is not None:
        print("Day 2 run completed successfully.")
    else:
        print("Day 2 run failed. Check logs/ for details.")

    print(
        "\nNow compare the logs. In Day 2, check whether the agents mention "
        "or reuse anything learned from Day 1."
    )
