import tempfile
import unittest
from pathlib import Path

from services.orchestration import ApprovalPaused, HumanGatedRunner, MemoryStore


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.memory = MemoryStore(Path(self.directory.name))
        self.memory.initialize("Original brief\n", "test")
        self.calls = []
        self.published = []

    def invoke(self, agent, phase, instruction):
        self.calls.append(phase)
        return "proposal" if phase == "proposal" else "deliverable"

    def run_item(self, responses):
        answers = iter(responses)
        runner = HumanGatedRunner(self.memory, self.invoke, lambda *args: next(answers))
        return runner.run_item("prd", "requirements", "architect", "Build PRD", lambda raw: None, self.published.append)

    def test_quit_blocks_execution_and_resume_keeps_proposal(self):
        with self.assertRaises(ApprovalPaused):
            self.run_item(["quit"])
        self.assertEqual(self.calls, ["proposal"])
        self.assertEqual(self.published, [])
        self.run_item(["approve", "approve"])
        self.assertEqual(self.calls, ["proposal", "execute"])
        self.assertEqual(self.published, ["deliverable"])

    def test_output_requires_separate_approval(self):
        with self.assertRaises(ApprovalPaused):
            self.run_item(["approve", "quit"])
        self.assertEqual(self.published, [])
        self.run_item(["approve"])
        self.assertEqual(self.published, ["deliverable"])

    def test_revisions_are_verbatim_and_resolved_per_gate(self):
        self.run_item(["revise Keep ALL constraints.\nDo not omit ports.", "approve", "revise Add tests.", "approve"])
        self.assertEqual(self.calls, ["proposal", "proposal", "execute", "execute"])
        revisions = self.memory.read()["open_revisions"]
        self.assertEqual(revisions[0]["feedback"], "Keep ALL constraints.\nDo not omit ports.")
        self.assertTrue(all(revision["resolved"] for revision in revisions))
        self.assertIn("Add tests.", self.memory.snapshot())

    def test_invalid_answer_is_not_approval(self):
        with self.assertRaises(ApprovalPaused):
            self.run_item(["yes", "", "quit"])
        self.assertEqual(self.calls, ["proposal"])

    def test_completed_item_is_not_executed_again(self):
        self.run_item(["approve", "approve"])
        self.run_item([])
        self.assertEqual(self.calls, ["proposal", "execute"])

    def test_new_brief_cannot_reuse_approved_memory(self):
        with self.assertRaises(ValueError):
            self.memory.initialize("Different brief", "test")

    def test_invalid_output_is_retried_but_never_published(self):
        attempts = []
        def reject(raw):
            attempts.append(raw)
            raise ValueError("Missing required artifact")
        runner = HumanGatedRunner(self.memory, self.invoke, lambda *args: "approve")
        with self.assertRaisesRegex(ValueError, "three times"):
            runner.run_item("prd", "requirements", "architect", "Write PRD", reject, self.published.append)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(self.published, [])
        self.assertEqual(self.memory.read()["completed_items"], {})
        self.assertIn("Missing required artifact", self.memory.snapshot())


    def test_rejection_reason_is_quoted_back_to_the_agent(self):
        instructions = []

        def invoke(agent, phase, instruction):
            instructions.append(instruction)
            return "proposal" if phase == "proposal" else "deliverable"

        def reject(raw):
            raise ValueError("Return a valid JSON object")

        runner = HumanGatedRunner(self.memory, invoke, lambda *args: "approve")
        with self.assertRaisesRegex(ValueError, "three times"):
            runner.run_item("prd", "requirements", "architect", "Write PRD", reject, self.published.append)
        executions = [text for text in instructions if "REJECTED" in text]
        self.assertEqual(len(executions), 2)
        self.assertIn("Return a valid JSON object", executions[0])
        self.assertIn("attempt 2 of 3", executions[0])
        self.assertIn("attempt 3 of 3", executions[1])

    def test_resuming_restores_the_retry_budget(self):
        failures = []

        def reject(raw):
            failures.append(raw)
            raise ValueError("Missing required artifact")

        runner = HumanGatedRunner(self.memory, self.invoke, lambda *args: "approve")
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, "three times"):
                runner.run_item("prd", "requirements", "architect", "Write PRD", reject, self.published.append)
        self.assertEqual(len(failures), 6)
        self.assertEqual(self.published, [])

    def test_run_plan_stops_once_and_keeps_the_approved_text(self):
        gates = []

        def approve(item, gate, content):
            gates.append((item, gate))
            return "approve"

        runner = HumanGatedRunner(self.memory, self.invoke, approve)
        result = runner.run_plan("architecture-plan", "requirements", "architect", "Plan it", self.published.append)
        self.assertEqual(gates, [("architecture-plan", "proposal")])
        self.assertEqual(self.calls, ["proposal"])
        self.assertEqual(result, "proposal")
        self.assertEqual(self.published, ["proposal"])

    def test_quit_at_a_plan_gate_resumes_without_redrafting(self):
        answers = iter(["quit", "approve"])
        runner = HumanGatedRunner(self.memory, self.invoke, lambda *args: next(answers))
        with self.assertRaises(ApprovalPaused):
            runner.run_plan("architecture-plan", "requirements", "architect", "Plan it", self.published.append)
        self.assertEqual(self.published, [])
        runner.run_plan("architecture-plan", "requirements", "architect", "Plan it", self.published.append)
        self.assertEqual(self.calls, ["proposal"])
        self.assertEqual(self.published, ["proposal"])

    def test_run_step_never_asks_the_human(self):
        gates = []

        def approve(*args):
            gates.append(args)
            return "approve"

        runner = HumanGatedRunner(self.memory, self.invoke, approve)
        result = runner.run_step("prd", "requirements", "architect", "Write PRD", lambda raw: None, self.published.append)
        self.assertEqual(gates, [])
        self.assertEqual(self.calls, ["execute"])
        self.assertEqual(result, "deliverable")
        self.assertEqual(self.published, ["deliverable"])

    def test_ungated_steps_still_fail_closed_on_invalid_output(self):
        def reject(raw):
            raise ValueError("Missing required artifact")

        runner = HumanGatedRunner(self.memory, self.invoke, lambda *args: "approve")
        with self.assertRaisesRegex(ValueError, "three times"):
            runner.run_step("prd", "requirements", "architect", "Write PRD", reject, self.published.append)
        self.assertEqual(self.calls, ["execute", "execute", "execute"])
        self.assertEqual(self.published, [])
        self.assertEqual(self.memory.read()["completed_items"], {})


if __name__ == "__main__":
    unittest.main()