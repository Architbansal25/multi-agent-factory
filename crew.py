"""Assembles the engineering team and the manager-led delivery loop into a Crew."""
from __future__ import annotations

from crewai import Crew, Process

from agents.engineering_team import EngineeringTeam
from config.settings import Settings, settings as default_settings
from services.guardrails import check_python_implementation, sanitize
from services.service_planner import ServiceSpec, detect_services
from tasks.speckit_tasks import build_tasks


class SpecKitFactory:
    """A CrewAI crew that runs the manager-led delivery loop."""

    def __init__(self, brief: str, config: Settings | None = None) -> None:
        self._settings = config or default_settings
        self._settings.ensure_directories()
        self._brief = brief

        self._services: list[ServiceSpec] = detect_services(brief, self._settings)
        for service in self._services:
            service.output_path.parent.mkdir(parents=True, exist_ok=True)

        team = EngineeringTeam(self._settings)
        self._manager = team.manager()
        self._architect = team.architect()
        self._developer = team.developer()

        self._plan = build_tasks(
            manager=self._manager,
            architect=self._architect,
            developer=self._developer,
            services=self._services,
            config=self._settings,
        )

        self._crew = Crew(
            agents=[self._manager, self._architect, self._developer],
            tasks=self._plan.tasks,
            process=Process.sequential,
            verbose=True,
        )

    @property
    def services(self) -> list[ServiceSpec]:
        return self._services

    def run(self) -> str:
        """Kick off the crew and persist every generated service.

        Returns the manager's final readiness message.
        """
        result = self._crew.kickoff(inputs={"brief": self._brief})

        for task, service in self._plan.implement_tasks:
            if task.output is not None:
                code = sanitize(task.output.raw)
                validated = check_python_implementation(code)
                service.output_path.parent.mkdir(parents=True, exist_ok=True)
                service.output_path.write_text(validated, encoding="utf-8")

        return str(result)
