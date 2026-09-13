"""The virtual engineering team, modeled as CrewAI agents.

Three roles run a manager-led delivery loop:
    Manager -> instructs the Architect
    Architect -> plans + writes PRD steps for the Developer
    Developer -> implements + self-tests, confirms readiness to the Architect
    Architect -> checks acceptance criteria, confirms readiness to the Manager
    Manager -> confirms delivery to the stakeholder
"""
from __future__ import annotations

import json

from crewai import LLM, Agent, Crew, Process, Task

from config.settings import Settings, settings as default_settings
from config.agent_models import load_agent_config
from agents.prompts import ARCHITECT, DEVELOPER, MANAGER, MEMORY_PROTOCOL, STACK_CONSTRAINT
from services.orchestration import MemoryStore


def build_llm(agent_name: str, config: Settings | None = None) -> LLM:
    """Resolve the selected agent's model from project configuration."""
    cfg = config or default_settings
    entry = load_agent_config(cfg.model_config_path)[agent_name]
    return LLM(model=entry["model"], api_key=cfg.api_key, temperature=cfg.temperature)


class EngineeringTeam:
    """Factory for the three roles that run the manager-led delivery loop."""

    def __init__(self, config: Settings | None = None) -> None:
        self._settings = config or default_settings
        load_agent_config(self._settings.model_config_path)

    def create(self, name: str, memory: MemoryStore) -> Agent:
        entry = load_agent_config(self._settings.model_config_path)[name]
        context = memory.read()
        stack = context["locked_stack"]
        constraint = STACK_CONSTRAINT.format(locked_stack=json.dumps(stack)) if stack else (
            "The stack is not locked yet. Extract explicit choices from the brief; "
            "surface missing or ambiguous values for human resolution, never invent defaults."
        )
        prompt = {"manager": MANAGER, "architect": ARCHITECT, "senior_developer": DEVELOPER}[name]
        return Agent(
            role=entry["role"],
            goal="Complete only the current approved action under the two-gate protocol.",
            backstory=prompt + "\n" + MEMORY_PROTOCOL + "\n" + constraint,
            llm=build_llm(name, self._settings),
            allow_delegation=False,
            respect_context_window=False,
            verbose=True,
        )

    def invoke(self, memory: MemoryStore, name: str, phase: str, instruction: str) -> str:
        agent = self.create(name, memory)
        if phase == "proposal":
            protocol = (
                "Write ONLY the plan document described below, in markdown, not the "
                "deliverable it covers. This plan is a human approval gate and the last "
                "chance the human gets to redirect the work it describes, so be complete "
                "and specific rather than brief: anything you leave vague is decided "
                "without them. Ground it in memory/context.json and the decisions already "
                "approved. Restate the locked stack explicitly, and surface open choices "
                "for the human instead of settling them yourself. Apply every item in this "
                "item's proposal revision log verbatim - the human raised each one."
            )
        else:
            protocol = (
                "The human has approved the plan covering this work; the controller has "
                "recorded it under memory/reviews/ as approved_plan.md. Execute exactly "
                "what that plan specifies and apply all revision feedback. Do not add "
                "scope, paths or technology the approved plan does not contain, and do "
                "not revisit a choice the human already settled there. "
                "Return ONLY the requested JSON object, no markdown fences. "
                "The controller validates the result; do not mark it approved."
            )
        task = Task(description=protocol + "\n\n" + instruction + "\n\nDISK MEMORY:\n" + memory.snapshot(),
                    expected_output="A scoped proposal" if phase == "proposal" else "The requested JSON deliverable",
                    agent=agent)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, memory=False, verbose=True)
        return str(crew.kickoff())

    def manager(self, memory: MemoryStore) -> Agent:
        return self.create("manager", memory)

    def architect(self, memory: MemoryStore) -> Agent:
        return self.create("architect", memory)

    def developer(self, memory: MemoryStore) -> Agent:
        return self.create("senior_developer", memory)

