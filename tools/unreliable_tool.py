import random
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class UnreliableResearchInput(BaseModel):
    """Input schema for the unreliable research tool."""

    query: str = Field(
        ...,
        description="The research query to process."
    )


class UnreliableResearchTool(BaseTool):
    name: str = "Unreliable Research Tool"
    description: str = (
        "A simulated research tool that sometimes fails with a TimeoutError. "
        "Use this to test how the crew handles unreliable external tools."
    )
    args_schema: Type[BaseModel] = UnreliableResearchInput

    def _run(self, query: str) -> str:
        """
        This tool randomly fails 50% of the time.

        Purpose:
        - Simulate an unreliable API.
        - Force the CrewAI workflow to deal with tool failure.
        """

        should_fail = random.choice([True, False])

        if should_fail:
            raise TimeoutError(
                f"Simulated timeout while researching query: {query}"
            )

        return (
            f"Simulated reliable result for query: {query}. "
            "AI agents can improve productivity by automating research, "
            "summarization, and review workflows, but they also introduce "
            "risks such as hallucination, tool failure, and higher API costs."
        )