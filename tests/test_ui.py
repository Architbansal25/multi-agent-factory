import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.ui_runner import ProjectRun, compose_brief, pending_gate, pipeline
from services.ui_worker import execute
from tasks.speckit_tasks import ARCHITECTURE_PLAN, IMPLEMENTATION_PLAN, build_tasks

BASE = Path(__file__).resolve().parent.parent
STACK = {"language": "TypeScript", "framework": "React", "database": "none", "infra": "local"}
SOURCE = {"src/app.tsx": "export const App = () => null;",
          "src/services/message.ts": "export const message = 'hello';",
          "src/tests/app.test.ts": "export const result = true;",
          "src/package.json": '{"dependencies":{"react":"^19.0.0"}}'}
ADRS = ["memory/03_architecture/tradeoffs/0001-ui.md"]


def fake_team(root: Path, calls: list):
    """Scripted agents that produce valid deliverables, so no API key is needed."""
    def invoke(agent, phase, instruction):
        context = json.loads((root / "memory/context.json").read_text(encoding="utf-8"))
        item = context["active_item"]["id"]
        calls.append((item, phase))
        if phase == "proposal":
            return f"# Plan for {item}"
        if item == "stack-lock":
            bundle = {"locked_stack": STACK, "global_constraints": [], "conflicts": []}
            if context.get("approval_modes", {}).get(ARCHITECTURE_PLAN.name):
                bundle["file_tree"] = list(SOURCE)
            return json.dumps(bundle)
        bundle = {"stack": context["locked_stack"]}
        if item == "development":
            bundle.update(files={path: SOURCE[path] for path in context["approved_tree"]},
                          verification={"status": "not_run", "commands": ["npm test"]})
        elif item == "packaging":
            bundle["files"] = {"memory/06_delivery.md": "Delivery. Tests NOT RUN."}
        elif item.startswith("000"):
            bundle["files"] = {ADRS[0]: (BASE / "templates/architecture/adr.md").read_text(encoding="utf-8")}
        else:
            task = next(task for task in build_tasks() if task.name == item)
            content = "Project document"
            if task.template:
                content = (BASE / "templates/architecture" / task.template).read_text(encoding="utf-8")
            if item == "hld":
                content += "\n```mermaid\nsequenceDiagram\nA->>B: go\n```\n" + "\n".join([*SOURCE, *ADRS])
                bundle.update(file_tree=list(SOURCE), adrs=ADRS)
            bundle["files"] = {task.path: content}
        return json.dumps(bundle)
    return invoke


class UiWorkerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "project"
        self.run = ProjectRun(self.root)
        self.run.ui.mkdir(parents=True)
        self.run.brief_path.write_text("TypeScript React app\n", encoding="utf-8")
        self.calls = []

    def step(self):
        return execute(self.root, invoke=fake_team(self.root, self.calls))

    def test_each_gate_is_answered_from_the_ui_and_the_run_finishes(self):
        status = self.step()
        self.assertEqual(status["state"], "waiting")
        self.assertEqual(pending_gate(self.run.context()), (ARCHITECTURE_PLAN.name, "proposal"))
        self.assertEqual(self.run.status()["state"], "waiting")

        self.run.queue_answer(ARCHITECTURE_PLAN.name, "proposal", "revise Add a persistence module.")
        self.assertEqual(self.step()["state"], "waiting")
        drafts = [call for call in self.calls if call == (ARCHITECTURE_PLAN.name, "proposal")]
        self.assertEqual(len(drafts), 2)

        self.run.queue_answer(ARCHITECTURE_PLAN.name, "proposal", "approve")
        self.assertEqual(self.step()["state"], "waiting")
        self.assertEqual(pending_gate(self.run.context()), (IMPLEMENTATION_PLAN.name, "proposal"))
        self.assertFalse((self.root / "src/app.tsx").exists())

        self.run.queue_answer(IMPLEMENTATION_PLAN.name, "proposal", "approve")
        status = self.step()
        self.assertEqual(status["state"], "done")
        self.assertIn("NOT RUN", status["sign_off"])
        self.assertEqual((self.root / "src/app.tsx").read_text(), SOURCE["src/app.tsx"])
        self.assertTrue(all(step["status"] == "done" for step in pipeline(self.run.context())))

    def test_an_answer_for_another_gate_is_never_applied(self):
        self.step()
        self.run.queue_answer(IMPLEMENTATION_PLAN.name, "proposal", "approve")
        self.assertEqual(self.step()["state"], "waiting")
        self.assertEqual(pending_gate(self.run.context()), (ARCHITECTURE_PLAN.name, "proposal"))
        self.assertTrue(self.run.answer_path.exists())

    def test_build_now_marks_the_specification_steps_skipped(self):
        self.step()
        self.run.queue_answer(ARCHITECTURE_PLAN.name, "proposal", "approve build-now")
        self.step()
        statuses = {step["item"]: step["status"] for step in pipeline(self.run.context())}
        self.assertEqual(statuses["prd"], "skipped")
        self.assertEqual(statuses["stack-lock"], "done")
        self.assertEqual(statuses[IMPLEMENTATION_PLAN.name], "waiting")

    def test_missing_key_fails_without_calling_agents(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            status = execute(self.root)
        self.assertEqual(status["state"], "failed")
        self.assertIn("ANTHROPIC_API_KEY", status["message"])

    def test_silent_worker_is_reported_as_crashed(self):
        old = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        self.run.write_status(state="running", started_at=old, heartbeat_at=old)
        self.assertEqual(self.run.status()["state"], "crashed")


class ComposeBriefTests(unittest.TestCase):
    def test_guided_form_keeps_the_layout_the_stack_lock_reads(self):
        brief = compose_brief("Build a todo app.", "- Must use Express.\nJSON file store",
                              [{"Constraint": "Runtime", "Rule": "Node.js"},
                               {"Constraint": "Frontend", "Rule": ""}], "Serves a page")
        self.assertIn("## System Constraints\n\n- Must use Express.\n- JSON file store", brief)
        self.assertIn("| Constraint | Rule |\n|---|---|\n| Runtime | Node.js |", brief)
        self.assertNotIn("Frontend", brief)
        sections = re.findall(r"^## [^\n]*Constraints[^\n]*\n", brief, re.M)
        self.assertEqual(len(sections), 2)


if __name__ == "__main__":
    unittest.main()
