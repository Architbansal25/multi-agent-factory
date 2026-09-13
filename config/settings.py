"""Configuration for the CrewAI engineering factory."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Immutable settings sourced from the environment."""

    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))

    temperature: float = 0.4

    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    project_dir: Path | None = None
    agents_config: Path | None = None
    brief_path: Path | None = None

    @property
    def model_config_path(self) -> Path:
        if self.agents_config is not None:
            return self.agents_config
        project_config = self.output_dir / "agents.config.yaml"
        return project_config if project_config.exists() else self.base_dir / "agents.config.yaml"

    @property
    def instructions_path(self) -> Path:
        return self.brief_path or self.base_dir / "INSTRUCTIONS.md"

    @property
    def output_dir(self) -> Path:
        return self.project_dir or self.base_dir / "generated"

    # Manager-led delivery loop artifact locations.
    @property
    def memory_dir(self) -> Path:
        return self.output_dir / "memory"

    @property
    def specs_dir(self) -> Path:
        return self.output_dir / "specs"

    @property
    def src_dir(self) -> Path:
        return self.output_dir / "src"

    @property
    def kickoff_path(self) -> Path:
        """Manager's build instruction to the Architect."""
        return self.memory_dir / "02_kickoff_plan.md"

    @property
    def plan_path(self) -> Path:
        """Architect's technical implementation plan."""
        return self.memory_dir / "03_architecture" / "hld.md"

    @property
    def prd_path(self) -> Path:
        """Architect's PRD-style, ordered build steps for the Developer."""
        return self.memory_dir / "01_prd.md"

    @property
    def app_path(self) -> Path:
        return self.src_dir / "app.py"

    def service_path(self, slug: str) -> Path:
        """Output path for a named microservice (used in multi-service mode)."""
        return self.src_dir / slug / "app.py"

    def ensure_directories(self) -> None:
        for directory in (self.memory_dir / "03_architecture" / "tradeoffs", self.src_dir):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
