import os
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

from tools.unreliable_tool import UnreliableResearchTool

load_dotenv()


LOG_FILE = "crew_outputs.log"


class TeeStream:
    """
    Duplicates writes to the original stream and a log file stream.
    """

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def setup_logging() -> logging.Logger:
    """
    Configures a dedicated file logger for crew outputs.
    """

    logger = logging.getLogger("crew_outputs")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )

    logger.addHandler(file_handler)
    return logger


def log_and_print(message: str) -> None:
    """
    Writes a message to stdout.
    """

    print(message)


def get_gemini_llm() -> LLM:
    """
    Creates the Gemini LLM configuration for CrewAI.

    For development, use a cheaper/faster Gemini model.
    You can change the model name depending on what is available in your account.
    """

    return LLM(
        model="gemini/gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )
    # return LLM(
    #     model="gpt-4.1-nano",
    #     api_key=os.getenv("OPENAI_API_KEY"),
    #     temperature=0.2,
    # )


def create_agents(llm: LLM):
    """
    Creates the three required agents:
    1. Researcher
    2. Fact-Checker
    3. Writer
    """

    search_tool = SerperDevTool()
    unreliable_tool = UnreliableResearchTool()

    researcher = Agent(
        role="Researcher",
        goal=(
            "Research the assigned topic using available tools and produce "
            "clear notes with useful points, risks, and examples."
        ),
        backstory=(
            "You are a careful research analyst. You know how to gather "
            "information from search tools and experimental internal tools. "
            "You continue working even if one source is unavailable."
        ),
        tools=[search_tool, unreliable_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    fact_checker = Agent(
        role="Fact-Checker",
        goal=(
            "Review the research notes, identify questionable claims, "
            "and produce a corrected, credibility-focused version."
        ),
        backstory=(
            "You are a strict fact-checker. You look for unsupported claims, "
            "contradictions, and vague reasoning. You prefer cautious, "
            "accurate statements."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Writer",
        goal=(
            "Write a concise final report based on the fact-checked notes."
        ),
        backstory=(
            "You are a technical writer who converts research and review notes "
            "into clear, structured, beginner-friendly reports."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    return researcher, fact_checker, writer


def create_tasks(researcher: Agent, fact_checker: Agent, writer: Agent):
    """
    Creates the three tasks for the agents.

    The tasks are intentionally connected:
    - Research task creates raw findings.
    - Fact-check task reviews those findings.
    - Writing task creates the final report.
    """

    research_task = Task(
        description=(
            "Research the topic: 'Benefits and risks of using AI agents in "
            "software development'.\n\n"
            "Use the available tools. You must try to use both the SerperDevTool "
            "and the Unreliable Research Tool. If a tool fails, clearly mention "
            "the failure and continue with the best available information.\n\n"
            "Return 5-7 bullet points covering benefits, risks, and practical "
            "examples."
        ),
        expected_output=(
            "A bullet-point research brief with benefits, risks, examples, "
            "and a short note about whether any tool failed."
        ),
        agent=researcher,
    )

    fact_check_task = Task(
        description=(
            "Review the research brief created by the Researcher.\n\n"
            "Check for unsupported claims, exaggerations, missing context, "
            "or contradictions. Rewrite the notes into a more reliable version."
        ),
        expected_output=(
            "A fact-check report containing: verified points, questionable "
            "points, corrections, and a final reliability rating."
        ),
        agent=fact_checker,
        context=[research_task],
    )

    writing_task = Task(
        description=(
            "Using the fact-check report, write a concise final report for a "
            "student submission.\n\n"
            "The report should explain the benefits and risks of AI agents in "
            "software development. Keep it structured and easy to understand."
        ),
        expected_output=(
            "A final report with a title, short introduction, benefits section, "
            "risks section, and conclusion."
        ),
        agent=writer,
        context=[fact_check_task],
    )

    return research_task, fact_check_task, writing_task


def run_sequential_crew():
    """
    Runs the system using Sequential process.

    In this mode, tasks run in order:
    Researcher -> Fact-Checker -> Writer
    """

    log_and_print("\n" + "=" * 80)
    log_and_print("RUNNING SEQUENTIAL CREW")
    log_and_print("=" * 80)

    llm = get_gemini_llm()
    researcher, fact_checker, writer = create_agents(llm)
    research_task, fact_check_task, writing_task = create_tasks(
        researcher,
        fact_checker,
        writer,
    )

    crew = Crew(
        agents=[researcher, fact_checker, writer],
        tasks=[research_task, fact_check_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    log_and_print("\n" + "=" * 80)
    log_and_print("SEQUENTIAL RESULT")
    log_and_print("=" * 80)
    log_and_print(str(result))

    return result


def run_hierarchical_crew():
    """
    Runs the system using Hierarchical process.

    In this mode, a manager LLM coordinates the agents.
    """

    log_and_print("\n" + "=" * 80)
    log_and_print("RUNNING HIERARCHICAL CREW")
    log_and_print("=" * 80)

    llm = get_gemini_llm()
    manager_llm = get_gemini_llm()

    researcher, fact_checker, writer = create_agents(llm)
    research_task, fact_check_task, writing_task = create_tasks(
        researcher,
        fact_checker,
        writer,
    )

    crew = Crew(
        agents=[researcher, fact_checker, writer],
        tasks=[research_task, fact_check_task, writing_task],
        process=Process.hierarchical,
        manager_llm=manager_llm,
        verbose=True,
    )

    result = crew.kickoff()

    log_and_print("\n" + "=" * 80)
    log_and_print("HIERARCHICAL RESULT")
    log_and_print("=" * 80)
    log_and_print(str(result))

    return result


if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Starting crew runs. Output file: %s", LOG_FILE)

    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        stdout_tee = TeeStream(sys.stdout, log_file)
        stderr_tee = TeeStream(sys.stderr, log_file)

        with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
            run_sequential_crew()
            run_hierarchical_crew()
