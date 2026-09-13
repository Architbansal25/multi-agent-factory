import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.engineering_team import EngineeringTeam
from agents.prompts import STACK_CONSTRAINT
from config.agent_models import load_agent_config
from config.settings import Settings
from services.orchestration import MemoryStore


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.settings = Settings(project_dir=self.root, api_key="test-placeholder-not-a-real-key")
        self.memory = MemoryStore(self.root)
        self.memory.initialize("JavaScript Express app", "test")
        context = self.memory.read()
        context["locked_stack"] = {"language": "JavaScript", "framework": "Express", "database": "JSON file", "infra": "local",
                                   "locked_at_stage": "kickoff", "locked_by": "human_approved"}
        self.memory.save(context)

    def test_agents_use_separate_models_and_exact_stack_prompt(self):
        team = EngineeringTeam(self.settings)
        agents = load_agent_config(self.settings.model_config_path)
        for name in ("manager", "architect", "senior_developer"):
            with self.subTest(agent=name):
                agent = team.create(name, self.memory)
                self.assertEqual(agent.llm.model, agents[name]["model"].removeprefix("anthropic/"))
                self.assertIn(STACK_CONSTRAINT.format(locked_stack=json.dumps(self.memory.read()["locked_stack"])), agent.backstory)
                self.assertIn("memory/context.json", agent.backstory)
                self.assertFalse(agent.allow_delegation)
                self.assertFalse(agent.respect_context_window)

    def test_project_configuration_override(self):
        override = self.root / "agents.config.yaml"
        source = self.settings.model_config_path.read_text(encoding="utf-8")
        override.write_text(source.replace("claude-haiku-4-5-20251001", "claude-sonnet-4-5-20250929"), encoding="utf-8")
        self.assertEqual(self.settings.model_config_path, override)
        self.assertIn("sonnet", load_agent_config(override)["manager"]["model"])

    def test_no_missing_agent_fallback(self):
        path = self.root / "invalid.yaml"
        path.write_text("agents: {}", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_agent_config(path)

    def test_every_invocation_reads_fresh_disk_context(self):
        team = EngineeringTeam(self.settings)
        with patch("agents.engineering_team.Crew") as crew:
            crew.return_value.kickoff.return_value = "Proposal"
            team.invoke(self.memory, "architect", "proposal", "Write FR")
            first = crew.call_args.kwargs["tasks"][0].description
            self.memory.record("revision", feedback="Keep exact REST endpoints.")
            team.invoke(self.memory, "architect", "proposal", "Write FR")
            second = crew.call_args.kwargs["tasks"][0].description
            self.assertNotIn("Keep exact REST endpoints.", first)
            self.assertIn("Keep exact REST endpoints.", second)


if __name__ == "__main__":
    unittest.main()