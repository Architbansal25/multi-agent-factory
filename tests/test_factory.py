import json
import tempfile
import unittest
from pathlib import Path

from config.settings import Settings
from crew import BUILD_NOW, SpecKitFactory
from services.orchestration import ApprovalPaused
from tasks.speckit_tasks import ARCHITECTURE_PLAN, IMPLEMENTATION_PLAN, build_tasks


class FactoryTests(unittest.TestCase):
    # Everything the architecture plan governs; the rest is governed by the
    # implementation plan.
    UNDER_ARCHITECTURE_PLAN = {"stack-lock", "prd", "fr", "nfr", "hld", "0001-ui", "0002-state"}

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.config = Settings(project_dir=self.root)
        self.gates = []
        self.calls = []
        self.stack = {"language": "TypeScript", "framework": "React", "database": "none", "infra": "local"}
        self.source = {"src/app.tsx": "export const App = () => null;",
                       "src/services/message.ts": "export const message = 'hello';",
                       "src/tests/app.test.ts": "export const result = true;",
                       "src/package.json": '{"dependencies":{"react":"^19.0.0"}}'}
        self.adrs = ["memory/03_architecture/tradeoffs/0001-ui.md", "memory/03_architecture/tradeoffs/0002-state.md"]
        self.factory = SpecKitFactory("TypeScript React app\n", self.config, self.approve, self.invoke)

    def approve(self, item, gate, content):
        self.gates.append((item, gate))
        if item == IMPLEMENTATION_PLAN.name:
            # Nothing reaches src/ until the human has approved the build plan.
            self.assertFalse((self.root / "src/app.tsx").exists())
        return "approve"

    def answering(self, *responses):
        """Scripted human, still recording which gates it was actually shown."""
        answers = iter(responses)

        def approve(item, gate, content):
            self.gates.append((item, gate))
            return next(answers)

        return approve

    def invoke(self, agent, phase, instruction):
        context = self.factory.memory.read()
        item = context["active_item"]["id"]
        self.calls.append((item, phase))
        if phase == "proposal":
            return f"Plan for {item}: {self.stack}"
        governing = ARCHITECTURE_PLAN if item in self.UNDER_ARCHITECTURE_PLAN else IMPLEMENTATION_PLAN
        self.assertIn((governing.name, "proposal"), self.gates)
        if item == "stack-lock":
            bundle = {"locked_stack": self.stack, "global_constraints": [], "conflicts": []}
            if context.get("approval_modes", {}).get(ARCHITECTURE_PLAN.name) == BUILD_NOW:
                # No HLD will run, so the tree is transcribed from the approved plan here.
                bundle["file_tree"] = list(self.source)
            return json.dumps(bundle)
        bundle = {"stack": context["locked_stack"]}
        if item == "development":
            # The Developer must emit exactly the approved tree, nothing more.
            files = {path: self.source[path] for path in context["approved_tree"]}
            bundle.update(files=files, verification={"status": "not_run", "commands": ["npm test"]})
        elif item == "packaging":
            bundle["files"] = {"memory/06_delivery.md": "Approved delivery. Tests NOT RUN."}
        elif item.startswith("000"):
            path = next(path for path in self.adrs if item in path)
            bundle["files"] = {path: (self.config.base_dir / "templates/architecture/adr.md").read_text(encoding="utf-8")}
        else:
            task = next(task for task in build_tasks() if task.name == item)
            content = "Approved project-specific document"
            if task.template:
                content = (self.config.base_dir / "templates/architecture" / task.template).read_text(encoding="utf-8")
            if item == "hld":
                content += "\n```mermaid\nsequenceDiagram\nBrowser->>App: open\n```\n" + "\n".join([*self.source, *self.adrs])
                bundle.update(file_tree=list(self.source), adrs=self.adrs)
            bundle["files"] = {task.path: content}
        return json.dumps(bundle)

    def test_run_stops_at_exactly_two_human_gates(self):
        result = self.factory.run()
        self.assertIn("NOT RUN", result)
        self.assertEqual(self.gates, [(ARCHITECTURE_PLAN.name, "proposal"), (IMPLEMENTATION_PLAN.name, "proposal")])
        self.assertEqual(self.calls, [
            (ARCHITECTURE_PLAN.name, "proposal"),
            ("stack-lock", "execute"), ("prd", "execute"), ("fr", "execute"),
            ("nfr", "execute"), ("hld", "execute"), ("0001-ui", "execute"), ("0002-state", "execute"),
            (IMPLEMENTATION_PLAN.name, "proposal"),
            ("development", "execute"), ("packaging", "execute"),
        ])
        self.assertEqual((self.root / "src/app.tsx").read_text(), self.source["src/app.tsx"])
        context = self.factory.memory.read()
        self.assertEqual(context["locked_stack"]["locked_by"], "human_approved")
        self.assertEqual(context["approved_tree"], list(self.source))
        before = list(self.calls)
        self.factory.run()
        self.assertEqual(before, self.calls)

    def test_approved_plans_are_kept_as_the_plan_of_record(self):
        self.factory.run()
        for plan in (ARCHITECTURE_PLAN, IMPLEMENTATION_PLAN):
            self.assertIn(f"Plan for {plan.name}", (self.root / plan.path).read_text(encoding="utf-8"))
            self.assertIn(plan.name, self.factory.memory.read()["completed_items"])

    def test_plan_feedback_loops_until_the_human_approves(self):
        self.factory.runner.approve = self.answering(
            "revise Split persistence out.", "revise And name the test files.", "approve", "approve")
        self.factory.run()
        drafts = [call for call in self.calls if call == (ARCHITECTURE_PLAN.name, "proposal")]
        self.assertEqual(len(drafts), 3)
        feedback = [revision["feedback"] for revision in self.factory.memory.read()["open_revisions"]]
        self.assertEqual(feedback, ["Split persistence out.", "And name the test files."])
        self.assertTrue(all(revision["resolved"] for revision in self.factory.memory.read()["open_revisions"]))

    def test_build_now_skips_the_specification_documents_and_still_builds(self):
        self.factory.runner.approve = self.answering(f"approve {BUILD_NOW}", "approve")
        result = self.factory.run()
        self.assertIn("NOT RUN", result)
        self.assertEqual(self.calls, [
            (ARCHITECTURE_PLAN.name, "proposal"), ("stack-lock", "execute"),
            (IMPLEMENTATION_PLAN.name, "proposal"), ("development", "execute"), ("packaging", "execute"),
        ])
        # The app is still built, from the tree the approved plan named.
        self.assertEqual((self.root / "src/app.tsx").read_text(), self.source["src/app.tsx"])
        context = self.factory.memory.read()
        self.assertEqual(context["approved_adrs"], [])
        self.assertEqual(context["locked_stack"]["locked_by"], "human_approved")
        for skipped in ("prd", "fr", "nfr", "hld"):
            self.assertNotIn(skipped, context["completed_items"])
        self.assertFalse((self.root / "memory/03_architecture/hld.md").exists())

    def test_build_now_generates_no_tests_even_if_the_agent_asks_for_them(self):
        self.factory.runner.approve = self.answering(f"approve {BUILD_NOW}", "approve")
        self.factory.run()
        # stack-lock transcribed src/tests/app.test.ts from the plan; the controller
        # drops it rather than billing the human for a test they opted out of.
        context = self.factory.memory.read()
        self.assertEqual(context["approved_tree"],
                         [path for path in self.source if "tests" not in path])
        self.assertFalse((self.root / "src/tests/app.test.ts").exists())
        self.assertTrue((self.root / "src/app.tsx").exists())
        self.assertIn("tests_skipped", (self.root / "memory/04_task_log.jsonl").read_text())

    def test_build_now_still_holds_the_tree_to_the_guardrails(self):
        self.factory.runner.approve = self.answering(f"approve {BUILD_NOW}", "approve")
        # Skipping tests does not relax the rest: still no single-file scripts.
        self.source = {"src/app.tsx": "export const App = () => null;"}
        with self.assertRaisesRegex(ValueError, "two application source modules"):
            self.factory.run()
        self.assertEqual(self.factory.memory.read()["locked_stack"], {})

    def test_a_run_started_before_modes_existed_still_resumes(self):
        # A context.json written by an earlier version has no approval_modes key.
        context = self.factory.memory.read()
        context.pop("approval_modes", None)
        self.factory.memory.save(context)
        self.factory.run()
        self.assertIn("development", self.factory.memory.read()["completed_items"])

    def test_a_mistyped_mode_is_not_an_approval(self):
        answers = self.answering("approve buildnow", "approve nonsense", "quit")
        self.factory.runner.approve = answers
        with self.assertRaises(ApprovalPaused):
            self.factory.run()
        # Three answers consumed at the one gate; nothing was drafted twice and
        # nothing advanced.
        self.assertEqual(self.calls, [(ARCHITECTURE_PLAN.name, "proposal")])
        self.assertEqual(self.factory.memory.read()["completed_items"], {})

    def test_blocked_agent_cannot_advance(self):
        self.factory._invoke_agent = lambda *args: '{"blocked_reason":"Need a stack decision"}'
        with self.assertRaises(ApprovalPaused):
            self.factory.run()
        self.assertEqual(self.factory.memory.read()["completed_items"], {})

    def test_nothing_is_locked_until_the_architecture_plan_is_approved(self):
        self.factory.runner.approve = self.answering("quit")
        with self.assertRaises(ApprovalPaused):
            self.factory.run()
        self.assertEqual(self.factory.memory.read()["locked_stack"], {})
        self.assertEqual(self.calls, [(ARCHITECTURE_PLAN.name, "proposal")])

    def test_no_code_is_written_until_the_implementation_plan_is_approved(self):
        self.factory.runner.approve = self.answering("approve", "quit")
        with self.assertRaises(ApprovalPaused):
            self.factory.run()
        context = self.factory.memory.read()
        self.assertIn("hld", context["completed_items"])
        self.assertNotIn("development", context["completed_items"])
        self.assertFalse((self.root / "src/app.tsx").exists())

    def test_missing_and_ambiguous_stack_are_blocked(self):
        for stack in ({"language": "JavaScript"}, {**self.stack, "framework": "React or Vue"}):
            with self.assertRaises(ValueError):
                self.factory._validate_stack_lock(json.dumps({"locked_stack": stack, "global_constraints": [], "conflicts": []}))

    def test_constraints_table_cannot_be_dropped(self):
        brief = "## Mandatory Tech Stack & Constraints\n| Constraint | Rule |\n|---|---|\n| Runtime | Node.js |\n"
        factory = SpecKitFactory(brief, Settings(project_dir=self.root / "table"), invoke=lambda *args: "unused")
        bundle = {"locked_stack": self.stack, "global_constraints": [], "conflicts": []}
        with self.assertRaisesRegex(ValueError, "table row"):
            factory._validate_stack_lock(json.dumps(bundle))
        bundle["global_constraints"] = ["| Runtime | Node.js |"]
        factory._validate_stack_lock(json.dumps(bundle))

    def test_reopen_requires_both_manager_gates_and_preserves_history(self):
        self.factory.run()
        def reopen_invoke(agent, phase, instruction):
            self.assertEqual(agent, "manager")
            pending = self.factory.memory.read()["pending_reopen"]
            if phase == "proposal":
                return "Propose reopening the HLD and downstream work."
            return json.dumps({"files": {f"memory/reopen/{pending['id']}.md": "Approved reroute to HLD."},
                               "reopen_target": "hld", "invalidated_items": pending["affected"]})
        self.factory._invoke_agent = reopen_invoke
        responses = iter(["approve", "quit"])
        self.factory.runner.approve = lambda *args: next(responses)
        with self.assertRaises(ApprovalPaused):
            self.factory.reopen("hld", "Add a separate persistence module.")
        self.assertIn("hld", self.factory.memory.read()["completed_items"])
        self.assertTrue((self.root / "src/app.tsx").exists())
        self.factory.runner.approve = lambda *args: "approve"
        self.factory.reopen("hld", "Add a separate persistence module.")
        context = self.factory.memory.read()
        self.assertNotIn("hld", context["completed_items"])
        self.assertNotIn("development", context["completed_items"])
        self.assertIn("prd", context["completed_items"])
        self.assertFalse((self.root / "src/app.tsx").exists())
        self.assertTrue(list((self.root / "memory/superseded").rglob("app.tsx")))
        self.assertTrue(any("reopened_at" in decision for decision in context["approved_decisions"]))
        self.assertEqual(context["open_revisions"][-1]["feedback"], "Add a separate persistence module.")

    def test_reopening_the_architecture_plan_invalidates_everything_after_it(self):
        self.factory.run()
        self.factory._invoke_agent = lambda agent, phase, instruction: (
            "Propose reopening the plan." if phase == "proposal" else json.dumps({
                "files": {f"memory/reopen/{self.factory.memory.read()['pending_reopen']['id']}.md": "Reroute."},
                "reopen_target": ARCHITECTURE_PLAN.name,
                "invalidated_items": self.factory.memory.read()["pending_reopen"]["affected"],
            })
        )
        self.factory.runner.approve = lambda *args: "approve"
        self.factory.reopen(ARCHITECTURE_PLAN.name, "Use a different persistence approach.")
        context = self.factory.memory.read()
        pipeline = [item for item in context["completed_items"] if not item.startswith("reopen-")]
        self.assertEqual(pipeline, [])
        self.assertEqual(context["locked_stack"], {})
        self.assertFalse((self.root / "src/app.tsx").exists())
        self.assertTrue(list((self.root / "memory/superseded").rglob("02_architecture_plan.md")))


if __name__ == "__main__":
    unittest.main()
