import os
import yaml
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from crewai import Agent, Task, Crew, Process, LLM
from crewai.flow.flow import Flow, start, listen, router
from crewai_tools import SerperDevTool

from tools.unreliable_tool import UnreliableResearchTool


load_dotenv()


CONFIG_DIR = Path("config")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class ResearchDepartmentState(BaseModel):
    """
    Structured state for the CrewAI Flow.

    This stores intermediate outputs from each step so that later steps
    do not depend on unstructured text passing only.
    """

    topic: str = "Benefits and risks of using AI agents in software development"

    research_output: str = ""
    fact_check_output: str = ""
    final_report: str = ""

    fact_check_decision: str = "UNKNOWN"

    revision_count: int = 0
    max_revision_cycles: int = 2

    tool_failure_observed: bool = False
    flow_status: str = "CREATED"

    error_message: Optional[str] = None


def get_gemini_llm() -> LLM:
    """
    Gemini model configuration for CrewAI.

    Use a cheaper Gemini model for development.
    """

    return LLM(
        model="gemini/gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )



def get_llm() -> LLM:
    """
    Central model selector.

    Since you said you are using Gemini, this returns Gemini by default.
    """

    return get_gemini_llm()


def load_yaml(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_log(run_label: str, content: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = LOG_DIR / f"phase3_{run_label}_{timestamp}.md"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(f"# PHASE 3 FLOW LOG - {run_label.upper()}\n\n")
        file.write(f"Generated at: {timestamp}\n\n")
        file.write("---\n\n")
        file.write(content)

    print(f"\nLog saved to: {file_path}")


def create_agents_from_yaml(llm: LLM) -> Dict[str, Agent]:
    """
    Reuses config/agents.yaml from Phase 2.

    Tools are assigned in Python because YAML cannot directly instantiate
    Python objects like SerperDevTool or UnreliableResearchTool.
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


def run_single_agent_task(agent: Agent, description: str, expected_output: str) -> str:
    """
    Helper function that runs one CrewAI task with one agent.

    In the Flow, each step runs a small crew so that the Flow controls
    the event order and branching logic.
    """

    task = Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)


class ResearchDepartmentFlow(Flow[ResearchDepartmentState]):
    """
    Event-driven CrewAI Flow for the autonomous research department.

    Flow path:
    1. Researcher creates research notes.
    2. Fact-Checker reviews notes.
    3. Router checks Fact-Checker decision.
    4. If APPROVED, Writer creates final report.
    5. If NEEDS_REVISION, Researcher revises.
    6. Guardrail prevents infinite revision loops.
    """

    def __init__(self):
        super().__init__()
        self.llm = get_llm()
        self.agents = create_agents_from_yaml(self.llm)

    @start()
    def start_research(self):
        """
        First event in the Flow.

        This runs the Researcher and stores the result in structured state.
        """

        self.state.flow_status = "RESEARCH_STARTED"

        description = f"""
        Research the topic: "{self.state.topic}".

        You must try to use both SerperDevTool and the Unreliable Research Tool.

        If a tool fails, clearly mention:
        TOOL_FAILURE_OBSERVED: YES

        If no tool fails, mention:
        TOOL_FAILURE_OBSERVED: NO

        Return 5-7 bullet points covering:
        - benefits
        - risks
        - practical examples
        - tool failure observation
        """

        expected_output = """
        A research brief with 5-7 bullet points.

        Must include exactly one of:
        TOOL_FAILURE_OBSERVED: YES
        TOOL_FAILURE_OBSERVED: NO
        """

        output = run_single_agent_task(
            agent=self.agents["researcher"],
            description=description,
            expected_output=expected_output,
        )

        self.state.research_output = output
        self.state.tool_failure_observed = "TOOL_FAILURE_OBSERVED: YES" in output
        self.state.flow_status = "RESEARCH_COMPLETED"

        return output

    @listen(start_research)
    def fact_check_research(self, research_output):
        """
        Fact-Checker reviews the research.

        The important part:
        It must return either DECISION: APPROVED or DECISION: NEEDS_REVISION.
        """

        self.state.flow_status = "FACT_CHECK_STARTED"

        description = f"""
        Review the following research output:

        {research_output}

        Your job:
        - identify unsupported claims
        - identify contradictions
        - check whether the research is good enough for a final student report
        - decide whether it should be approved or revised

        You must return exactly one decision line:

        DECISION: APPROVED

        or

        DECISION: NEEDS_REVISION

        Choose NEEDS_REVISION if the research is too vague, incomplete,
        contradictory, or missing important risk/benefit details.

        Choose APPROVED if the research is good enough for the Writer.
        """

        expected_output = """
        A fact-check report with:
        1. Verified points
        2. Questionable points
        3. Corrections needed
        4. Final reliability rating
        5. Exactly one decision line:
           DECISION: APPROVED
           or
           DECISION: NEEDS_REVISION
        """

        output = run_single_agent_task(
            agent=self.agents["fact_checker"],
            description=description,
            expected_output=expected_output,
        )

        self.state.fact_check_output = output

        if "DECISION: NEEDS_REVISION" in output:
            self.state.fact_check_decision = "NEEDS_REVISION"
        elif "DECISION: APPROVED" in output:
            self.state.fact_check_decision = "APPROVED"
        else:
            self.state.fact_check_decision = "UNKNOWN"

        self.state.flow_status = "FACT_CHECK_COMPLETED"

        return output

    @router(fact_check_research)
    def decide_next_step(self):
        """
        Router that decides what happens after fact-checking.

        This is the core event-driven logic.
        """

        if self.state.fact_check_decision == "APPROVED":
            return "approved"

        if self.state.revision_count >= self.state.max_revision_cycles:
            return "max_revisions_reached"

        return "revise"

    @listen("revise")
    def revise_research(self):
        """
        Researcher revises the research based on Fact-Checker feedback.

        Guardrail:
        revision_count increases every time this path runs.
        """

        self.state.flow_status = "REVISION_STARTED"
        self.state.revision_count += 1

        description = f"""
        Revise the research brief for the topic:

        "{self.state.topic}"

        Previous research output:
        {self.state.research_output}

        Fact-checker feedback:
        {self.state.fact_check_output}

        Improve the research based on the fact-checker feedback.
        Do not repeat unsupported claims.
        Add missing context.
        Keep the answer concise.

        This is revision cycle {self.state.revision_count}
        out of maximum {self.state.max_revision_cycles}.
        """

        expected_output = """
        A revised research brief with stronger, clearer, and better-supported
        points. Include benefits, risks, examples, and note whether tool
        failure affected the result.
        """

        output = run_single_agent_task(
            agent=self.agents["researcher"],
            description=description,
            expected_output=expected_output,
        )

        self.state.research_output = output
        self.state.flow_status = "REVISION_COMPLETED"

        return output

    @listen(revise_research)
    def fact_check_revised_research(self, revised_research_output):
        """
        Fact-checks revised research.

        This creates a loop:
        revise_research -> fact_check_revised_research -> route_after_revision

        The loop is controlled by max_revision_cycles.
        """

        self.state.flow_status = "REVISED_FACT_CHECK_STARTED"

        description = f"""
        Review the revised research output:

        {revised_research_output}

        Previous fact-check feedback was:

        {self.state.fact_check_output}

        Decide whether the revised research is now good enough.

        You must return exactly one decision line:

        DECISION: APPROVED

        or

        DECISION: NEEDS_REVISION
        """

        expected_output = """
        A revised fact-check report with:
        1. Improved points
        2. Remaining issues
        3. Final reliability rating
        4. Exactly one decision line:
           DECISION: APPROVED
           or
           DECISION: NEEDS_REVISION
        """

        output = run_single_agent_task(
            agent=self.agents["fact_checker"],
            description=description,
            expected_output=expected_output,
        )

        self.state.fact_check_output = output

        if "DECISION: NEEDS_REVISION" in output:
            self.state.fact_check_decision = "NEEDS_REVISION"
        elif "DECISION: APPROVED" in output:
            self.state.fact_check_decision = "APPROVED"
        else:
            self.state.fact_check_decision = "UNKNOWN"

        self.state.flow_status = "REVISED_FACT_CHECK_COMPLETED"

        return output

    @router(fact_check_revised_research)
    def route_after_revision(self):
        """
        Router after revised fact-check.

        If approved, write final report.
        If still not approved but revision limit remains, revise again.
        If revision limit is reached, write final report with limitations.
        """

        if self.state.fact_check_decision == "APPROVED":
            return "approved"

        if self.state.revision_count >= self.state.max_revision_cycles:
            return "max_revisions_reached"

        return "revise"

    @listen("approved")
    def write_final_report(self):
        """
        Writer creates final report when Fact-Checker approves.
        """

        self.state.flow_status = "WRITING_APPROVED_REPORT"

        description = f"""
        Write the final student report using the approved research and
        fact-check report.

        Topic:
        {self.state.topic}

        Research:
        {self.state.research_output}

        Fact-check:
        {self.state.fact_check_output}

        The report should include:
        1. Title
        2. Introduction
        3. Benefits
        4. Risks
        5. Tool failure observation
        6. State/flow observation
        7. Conclusion

        Mention that the Fact-Checker approved the research.
        """

        expected_output = """
        A structured final student report of 300-400 words.
        """

        output = run_single_agent_task(
            agent=self.agents["writer"],
            description=description,
            expected_output=expected_output,
        )

        self.state.final_report = output
        self.state.flow_status = "COMPLETED_APPROVED"

        return output

    @listen("max_revisions_reached")
    def write_report_with_limitations(self):
        """
        Writer creates final report even when Fact-Checker is not fully satisfied.

        This is the guardrail path. It prevents endless Researcher ↔ Fact-Checker
        loops.
        """

        self.state.flow_status = "WRITING_LIMITED_REPORT"

        description = f"""
        Write the final student report using the best available research,
        but clearly mention that the maximum revision limit was reached.

        Topic:
        {self.state.topic}

        Latest research:
        {self.state.research_output}

        Latest fact-check:
        {self.state.fact_check_output}

        Revision cycles used:
        {self.state.revision_count}

        Maximum revision cycles allowed:
        {self.state.max_revision_cycles}

        The report should include:
        1. Title
        2. Introduction
        3. Benefits
        4. Risks
        5. Tool failure observation
        6. Limitation that max revision cycles were reached
        7. Conclusion
        """

        expected_output = """
        A structured final student report of 300-400 words that clearly
        mentions limitations and the revision guardrail.
        """

        output = run_single_agent_task(
            agent=self.agents["writer"],
            description=description,
            expected_output=expected_output,
        )

        self.state.final_report = output
        self.state.flow_status = "COMPLETED_WITH_LIMITATIONS"

        return output


def run_phase3_flow():
    print("\n" + "=" * 80)
    print("RUNNING PHASE 3 CREWAI FLOW")
    print("=" * 80)

    flow = ResearchDepartmentFlow()

    try:
        result = flow.kickoff()

        summary = f"""
                    # Final Flow Result

                    {result}

                    ---

                    # Final Structured State

                    Topic: {flow.state.topic}

                    Flow Status: {flow.state.flow_status}

                    Fact-Check Decision: {flow.state.fact_check_decision}

                    Revision Count: {flow.state.revision_count}

                    Max Revision Cycles: {flow.state.max_revision_cycles}

                    Tool Failure Observed: {flow.state.tool_failure_observed}

                    ---

                    # Research Output

                    {flow.state.research_output}

                    ---

                    # Fact-Check Output

                    {flow.state.fact_check_output}

                    ---

                    # Final Report

                    {flow.state.final_report}
                """

        print("\n" + "=" * 80)
        print("PHASE 3 FLOW RESULT")
        print("=" * 80)
        print(summary)

        save_log("flow_run", summary)

        try:
            flow.plot("phase3_research_department_flow")
            print("Flow plot saved as phase3_research_department_flow.html")
        except Exception as plot_error:
            print(f"Flow plot could not be generated: {plot_error}")

        return result

    except Exception as error:
        error_log = (
            "Phase 3 flow failed.\n\n"
            f"Error type: {type(error).__name__}\n"
            f"Error message: {error}\n\n"
            "Traceback:\n"
            f"{traceback.format_exc()}"
        )

        print(error_log)
        save_log("flow_error", error_log)

        return None


if __name__ == "__main__":
    run_phase3_flow()