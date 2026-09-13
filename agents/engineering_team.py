"""The virtual engineering team, modeled as CrewAI agents.

Three roles run a manager-led delivery loop:
    Manager -> instructs the Architect
    Architect -> plans + writes PRD steps for the Developer
    Developer -> implements + self-tests, confirms readiness to the Architect
    Architect -> checks acceptance criteria, confirms readiness to the Manager
    Manager -> confirms delivery to the stakeholder
"""
from __future__ import annotations

from crewai import LLM, Agent

from config.settings import Settings, settings as default_settings


def build_llm(config: Settings | None = None) -> LLM:
    """Create the shared Claude-backed LLM used by every agent."""
    cfg = config or default_settings
    return LLM(model=cfg.model, api_key=cfg.api_key, temperature=cfg.temperature)


class EngineeringTeam:
    """Factory for the three roles that run the manager-led delivery loop."""

    def __init__(self, config: Settings | None = None) -> None:
        self._llm = build_llm(config)

    def manager(self) -> Agent:
        return Agent(
            role="Engineering Manager",
            goal=(
                "Turn the raw brief into a clear build instruction for the "
                "Architect, then, once the Architect confirms the work is "
                "accepted, confirm final delivery to the stakeholder with exact "
                "run instructions."
            ),
            backstory=(
                "The team's manager. You kick off every delivery by instructing "
                "the Architect on what to build and why. You never write code or "
                "plans yourself, and you only announce delivery after the "
                "Architect explicitly confirms the application is ready."
            ),
            llm=self._llm,
            allow_delegation=False,
            verbose=True,
        )

    def architect(self) -> Agent:
        return Agent(
            role="Software Architect",
            goal=(
                "Turn the Manager's instruction into a lightweight technical plan "
                "and a PRD-style, ordered set of build steps for the Developer. "
                "After the Developer confirms an implementation is ready, check "
                "it against the acceptance criteria and confirm to the Manager."
            ),
            backstory=(
                "A hands-on architect who is the single point of contact between "
                "the Manager and the Developer. You pick the simplest technology "
                "that works, document it as clear PRD steps, and you are the one "
                "who signs off on acceptance criteria before telling the Manager "
                "the work is ready."
            ),
            llm=self._llm,
            allow_delegation=False,
            verbose=True,
        )

    def developer(self) -> Agent:
        return Agent(
            role="Senior Developer",
            goal=(
                "Implement exactly what the Architect's PRD describes, then test "
                "the implementation and confirm readiness back to the Architect."
            ),
            backstory=(
                "A meticulous engineer who takes instructions only from the "
                "Architect. You write complete, syntactically valid code, verify "
                "it works, and explicitly report back to the Architect when it is "
                "ready for acceptance review."
            ),
            llm=self._llm,
            allow_delegation=False,
            verbose=True,
        )

