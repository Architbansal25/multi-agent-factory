"""Controller-driven artifact pipeline with two mandatory human approval gates.

The human approves the Architect's plan, then the Developer's implementation plan.
Between and after those gates the artifacts are executed under an already-approved
plan and held to the programmatic guardrails, so the run stops for a person twice
rather than once per document.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import replace
from pathlib import PurePosixPath

from config.settings import Settings, settings as default_settings
from services.guardrails import (
    GuardrailValidationError, is_test_path, parse_bundle, safe_path, source_extensions,
    validate_files, validate_implementation, validate_stack, validate_tree,
)
from services.orchestration import ApprovalPaused, Approve, HumanGatedRunner, Invoke, MemoryStore, timestamp
from tasks.speckit_tasks import (
    ARCHITECTURE_PLAN, BUILD_NOW_NOTE, DEVELOPMENT, FILE_TREE_INSTRUCTION, IMPLEMENTATION_PLAN,
    PACKAGING, STACK_INSTRUCTION, StageTask, adr_task, build_tasks,
)

# Saying "approve build-now" at gate 1 skips the PRD, FR, NFR, HLD and ADRs and
# builds straight from the approved architecture plan.
BUILD_NOW = "build-now"


PLANS = {plan.name: plan for plan in (ARCHITECTURE_PLAN, IMPLEMENTATION_PLAN)}

# What approving each plan actually commits the human to, said plainly at the gate,
# and the answers that gate accepts.
PLAN_GATES = {
    ARCHITECTURE_PLAN.name: (
        "HUMAN GATE 1 of 2 - ARCHITECTURE PLAN",
        "Approving locks the stack, the requirements and the file tree.",
        [f"{'approve':<20} write the PRD, FR, NFR, HLD and ADRs from this plan, then build",
         f"{'approve ' + BUILD_NOW:<20} build the app straight from this plan - no PRD, FR, NFR, HLD,",
         f"{'':<20} ADRs or tests. Roughly a fifth of the cost, and nothing but the",
         f"{'':<20} structural guardrails checks the result. Prototypes, not upkeep.",
         f"{'revise <feedback>':<20} send it back with your changes",
         f"{'quit':<20} pause here; rerun the same command to resume"],
    ),
    IMPLEMENTATION_PLAN.name: (
        "HUMAN GATE 2 of 2 - IMPLEMENTATION PLAN",
        "Approving builds the code exactly as described here. This is the last gate: the "
        "generated code is checked by the guardrails, not shown to you for approval.",
        None,
    ),
}


def console_approval(item: str, gate: str, content: str) -> str:
    heading, commitment, options = PLAN_GATES.get(
        item, (f"{item}: {gate.upper()} APPROVAL", "", None))
    print(f"\n=== {heading} ===")
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        document = None
    if isinstance(document, dict) and isinstance(document.get("files"), dict):
        for path, text in document["files"].items():
            print(f"\n--- {path} ---\n{text}")
        print(json.dumps({key: value for key, value in document.items() if key != "files"}, indent=2))
    else:
        print(content)
    if commitment:
        print(f"\n{commitment}")
    if options:
        print("\n".join(["", *options]))
    else:
        print("Enter 'approve', 'revise <feedback>', or 'quit'.")
    try:
        return input("> ")
    except (EOFError, KeyboardInterrupt) as exc:
        raise ApprovalPaused("Approval interrupted; run the same command to resume.") from exc


class SpecKitFactory:
    """Only this controller may publish agent output or advance a stage."""

    def __init__(self, brief: str, config: Settings | None = None,
                 approve: Approve = console_approval, invoke: Invoke | None = None) -> None:
        self._settings = config or default_settings
        self._settings.ensure_directories()
        self.memory = MemoryStore(self._settings.output_dir)
        self.memory.initialize(brief, self._settings.output_dir.name)
        if invoke is None:
            from agents.engineering_team import EngineeringTeam
            team = EngineeringTeam(self._settings)
            invoke = lambda name, phase, instruction: team.invoke(self.memory, name, phase, instruction)
        self._invoke_agent = invoke
        self.runner = HumanGatedRunner(self.memory, self._invoke, approve)

    def _invoke(self, name: str, phase: str, instruction: str) -> str:
        raw = self._invoke_agent(name, phase, instruction)
        try:
            document = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(document, dict) and document.get("blocked_reason"):
            reason = str(document["blocked_reason"])
            self.memory.record("blocked", agent=name, reason=reason)
            raise ApprovalPaused(f"Manager escalation: {reason} Use --reopen <item> --feedback <reason> to reopen an approved decision.")
        return raw

    def _build_now(self) -> bool:
        """Did the human approve gate 1 with build-now?"""
        return self.memory.read().get("approval_modes", {}).get(ARCHITECTURE_PLAN.name) == BUILD_NOW

    def _validate_stack_lock(self, raw: str, tree: bool = False) -> None:
        bundle = parse_bundle(raw)
        stack = bundle.get("locked_stack")
        fields = {"language", "framework", "database", "infra"}
        if not isinstance(stack, dict) or set(stack) != fields:
            raise GuardrailValidationError("Stack lock requires language, framework, database and infra.")
        for value in stack.values():
            if not isinstance(value, str) or not value.strip() or re.search(r"\b(unknown|unspecified|tbd|or)\b|[<>]", value, re.I):
                raise GuardrailValidationError("Missing or ambiguous stack. Ask the human to specify exact choices in proposal feedback.")
        source_extensions(stack)
        constraints = bundle.get("global_constraints")
        brief = (self.memory.folder / "00_brief.md").read_text(encoding="utf-8")
        if not isinstance(constraints, list):
            raise GuardrailValidationError("global_constraints must be a JSON array of strings copied from the brief.")
        paraphrased = [value for value in constraints
                       if not isinstance(value, str) or not value.strip() or value not in brief]
        if paraphrased:
            raise GuardrailValidationError(
                "Every global_constraints entry must appear character-for-character in "
                "memory/00_brief.md. Copy the source line instead of rewording it, keeping table "
                f"pipes and trailing punctuation. These do not match: {paraphrased}")
        clean = re.sub(r"<!--.*?-->", "", brief, flags=re.DOTALL)
        sections = re.findall(r"^## [^\n]*Constraints[^\n]*\n(.*?)(?=^## |\Z)", clean, re.M | re.S | re.I)
        required = []
        for section in sections:
            for line in section.splitlines():
                line = line.strip()
                if not line or re.fullmatch(r"\|[- |:]+\|", line) or line.lower() == "| constraint | rule |":
                    continue
                required.append(line[2:] if line.startswith("- ") else line)
        missing = [line for line in required if line not in constraints]
        if missing:
            raise GuardrailValidationError(
                "Preserve every constraints-section bullet, table row and paragraph verbatim in "
                f"global_constraints. Missing: {missing}")
        conflicts = bundle.get("conflicts")
        if conflicts != []:
            open_items = ", ".join(
                str(conflict.get("type", conflict)) if isinstance(conflict, dict) else str(conflict)
                for conflict in conflicts
            ) if isinstance(conflicts, list) else repr(conflicts)
            raise GuardrailValidationError(
                f"The stack cannot be locked while these conflicts are open: {open_items}. "
                "Do not invent a default and do not drop them: return a blocked_reason naming "
                "the open choices so the human can decide. The human resolves them by answering "
                "at the stack-lock proposal gate with 'revise <the exact choices>'."
            )
        if any(re.search(r"\bsingle[ -]file\b", constraint, re.I) for constraint in constraints):
            raise GuardrailValidationError("The single-file brief conflicts with modular output. Update the brief and start a new project.")
        if tree:
            # No HLD is written on the build-now path, so the tree is held to the same
            # standard here that validate_tree would have applied to the HLD's - except
            # that build-now deliberately ships no tests, so it cannot require them.
            validate_tree(bundle.get("file_tree"), self.memory.root, stack, require_tests=False)

    def _publish_stack(self, raw: str, tree: bool = False) -> None:
        bundle = parse_bundle(raw)
        context = self.memory.read()
        context["locked_stack"] = {**bundle["locked_stack"], "locked_at_stage": ARCHITECTURE_PLAN.stage,
                                   "locked_by": "human_approved"}
        context["global_constraints"] = bundle["global_constraints"]
        if tree:
            # The human chose to skip tests, so drop any the agent still transcribed
            # rather than trusting the prompt: a test file left in the tree is one the
            # Developer must write and the human is billed for.
            approved = [path for path in bundle["file_tree"] if not is_test_path(path)]
            dropped = [path for path in bundle["file_tree"] if is_test_path(path)]
            if dropped:
                self.memory.record("tests_skipped", item="stack-lock", mode=BUILD_NOW, paths=dropped)
            context["approved_tree"] = approved
            context["approved_adrs"] = []
        self.memory.save(context)

    def _validate_artifact(self, task: StageTask, raw: str) -> None:
        bundle = parse_bundle(raw)
        context = self.memory.read()
        validate_stack(bundle, context["locked_stack"])
        if task.name == "development":
            validate_implementation(bundle, self.memory.root, context["locked_stack"],
                                    context["approved_tree"], require_tests=not self._build_now())
            verification = bundle.get("verification")
            if not isinstance(verification, dict) or verification.get("status") != "not_run":
                raise GuardrailValidationError("Verification must explicitly state status: not_run.")
            commands = verification.get("commands")
            if not isinstance(commands, list) or not commands or not all(isinstance(command, str) and command.strip() for command in commands):
                raise GuardrailValidationError(
                    "Supply the exact commands the human runs to install and start the app, "
                    "plus the test command when this run generated tests.")
            return
        files = validate_files(bundle, [task.path], self.memory.root, "memory")
        content = files[task.path]
        headings = {
            "fr": ["# Functional Requirements", "| ID | Requirement | Priority | Notes |"],
            "nfr": ["# Non-Functional Requirements", "Performance", "Scalability", "Security", "Availability", "Maintainability"],
            "hld": ["# High-Level Design", "## Component Diagram", "```mermaid", "## Module / File Tree", "## Key Flows", "sequenceDiagram"],
        }.get(task.name, [])
        if task.template == "adr.md":
            headings = ["# ADR-", "## Context", "## Decision", "## Alternatives Considered", "## Consequences"]
        if any(heading not in content for heading in headings):
            raise GuardrailValidationError(f"{task.name} is missing required template sections: {headings}")
        if task.name == "hld":
            tree = validate_tree(bundle.get("file_tree"), self.memory.root, context["locked_stack"])
            adrs = bundle.get("adrs")
            if not isinstance(adrs, list) or not adrs or not all(
                isinstance(path, str) and re.fullmatch(r"memory/03_architecture/tradeoffs/\d{4}-[a-z0-9-]+\.md", path) for path in adrs
            ) or len(set(adrs)) != len(adrs):
                raise GuardrailValidationError("List distinct numbered ADR paths, one for each significant decision.")
            for path in [*tree, *adrs]:
                if path not in content:
                    raise GuardrailValidationError(f"HLD must explicitly show the approved path: {path}")

    def _publish_artifact(self, task: StageTask, raw: str) -> None:
        bundle = parse_bundle(raw)
        self._validate_artifact(task, raw)
        prefix = "src" if task.name == "development" else "memory"
        for relative, content in bundle["files"].items():
            path = safe_path(self.memory.root, relative, prefix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if task.name == "hld":
            context = self.memory.read()
            context["approved_tree"] = bundle["file_tree"]
            context["approved_adrs"] = bundle["adrs"]
            self.memory.save(context)

    def _artifacts_of(self, completed: str) -> dict[str, str]:
        """The files an approved item produced, keyed by project-relative path.

        An artifact item records a JSON bundle whose files object says what was
        written; a plan item records the approved markdown itself, which the
        controller wrote to the plan's own path.
        """
        record = (self.memory.folder / completed).read_text(encoding="utf-8")
        item = PurePosixPath(completed).parts[1]
        if item in PLANS:
            return {PLANS[item].path: record}
        return parse_bundle(record).get("files", {})

    def _run_plan(self, plan: StageTask, modes: tuple[str, ...] = ()) -> str:
        """Stop for the human, then keep the approved words as the plan of record."""
        def publish(approved: str) -> None:
            path = safe_path(self.memory.root, plan.path, "memory")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(approved, encoding="utf-8")

        return self.runner.run_plan(plan.name, plan.stage, plan.agent, plan.instruction,
                                    publish, modes)

    def _run_artifact(self, task: StageTask) -> str:
        """Execute one artifact under the plan the human already approved."""
        instruction = task.instruction + (
            "\nReturn JSON with stack (exact copy of context.json.locked_stack) and files "
            "(object mapping each requested project-relative path to its complete text). "
        )
        if task.path:
            instruction += f"The files object must contain only {task.path}."
        if task.template:
            template = self._settings.base_dir / "templates" / "architecture" / task.template
            instruction += "\nRequired template (replace examples with project-specific content):\n" + template.read_text(encoding="utf-8")
        return self.runner.run_step(task.name, task.stage, task.agent, instruction,
                                    lambda raw: self._validate_artifact(task, raw),
                                    lambda raw: self._publish_artifact(task, raw))

    def reopen(self, item: str, feedback: str) -> None:
        context = self.memory.read()
        if context.get("pending_reopen"):
            pending = context["pending_reopen"]
            if pending["target"] != item or pending["feedback"] != feedback:
                raise ValueError("Resume the pending reopen with its original target and feedback.")
        else:
            if item not in context["completed_items"] or not feedback.strip():
                raise ValueError("Reopen requires an approved item and nonempty human feedback.")
            order = [ARCHITECTURE_PLAN.name, "stack-lock", *[task.name for task in build_tasks()],
                     *[adr_task(path).name for path in context.get("approved_adrs", [])],
                     IMPLEMENTATION_PLAN.name, DEVELOPMENT.name, PACKAGING.name]
            affected = order[order.index(item):]
            pending = {"target": item, "feedback": feedback, "affected": affected,
                       "id": "reopen-" + str(len(context["approved_decisions"])) + "-" + item,
                       "suspended_item": context["active_item"]}
            context["pending_reopen"] = pending
            context["active_item"] = None
            self.memory.save(context)
            self.memory.record("reopen_requested", **pending)
        path = f"memory/reopen/{pending['id']}.md"
        instruction = (
            f"The human explicitly requests reopening {item}. Feedback (verbatim): {feedback}\n"
            f"Propose rerouting to {item} and invalidating only these downstream items: {pending['affected']}. "
            "Explain impacts on stack, decisions, code and approval history. Do not author replacement "
            "requirements, architecture or code. After proposal approval return JSON with files "
            f"containing only {path}, plus reopen_target: {item!r} and invalidated_items: "
            f"{pending['affected']}. Both gates must complete before any prior approval is invalidated."
        )

        def validate(raw: str) -> None:
            bundle = parse_bundle(raw)
            validate_files(bundle, [path], self.memory.root, "memory")
            if bundle.get("reopen_target") != item or bundle.get("invalidated_items") != pending["affected"]:
                raise GuardrailValidationError("Reopen output must match the exact requested target and invalidation list.")

        def publish(raw: str) -> None:
            destination = safe_path(self.memory.root, path, "memory")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(parse_bundle(raw)["files"][path], encoding="utf-8")

        self.runner.run_item(pending["id"], context["stage"], "manager", instruction, validate, publish)
        context = self.memory.read()
        archive = self.memory.folder / "superseded" / pending["id"]
        archive.mkdir(parents=True, exist_ok=True)
        for affected in pending["affected"]:
            completed = context["completed_items"].get(affected)
            if completed:
                for relative, approved_content in self._artifacts_of(completed).items():
                    prefix = "src" if relative.startswith("src/") else "memory"
                    existing = safe_path(self.memory.root, relative, prefix)
                    if existing.exists() and existing.read_text(encoding="utf-8") != approved_content:
                        raise ValueError(f"{relative} was edited outside the factory; preserve it elsewhere before reopening.")
        for affected in pending["affected"]:
            completed = context["completed_items"].pop(affected, None)
            if completed:
                for relative in self._artifacts_of(completed):
                    existing = self.memory.root / relative
                    if existing.exists():
                        destination = archive / "artifacts" / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(existing), str(destination))
            review = self.memory.folder / "reviews" / affected
            if review.exists():
                destination = archive / "reviews" / affected
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(review), str(destination))
            for decision in context["approved_decisions"]:
                if decision["decision"].startswith(f"Approved {affected};") and "reopened_at" not in decision:
                    decision.update(reopened_at=timestamp(), reopened_by="human_approved", superseded_path=str(archive.relative_to(self.memory.root)))
        if "stack-lock" in pending["affected"]:
            context["locked_stack"] = {}
            context["global_constraints"] = []
        if "hld" in pending["affected"]:
            context.pop("approved_tree", None)
            context.pop("approved_adrs", None)
        stages = {ARCHITECTURE_PLAN.name: ARCHITECTURE_PLAN.stage, "stack-lock": ARCHITECTURE_PLAN.stage,
                  IMPLEMENTATION_PLAN.name: IMPLEMENTATION_PLAN.stage,
                  DEVELOPMENT.name: DEVELOPMENT.stage, PACKAGING.name: PACKAGING.stage,
                  **{task.name: task.stage for task in build_tasks()}}
        revision = {"item": item, "stage": stages.get(item, context["stage"]),
                    "gate": "proposal", "feedback": feedback, "raised_at": timestamp(), "resolved": False}
        context["open_revisions"].append(revision)
        review = self.memory.folder / "reviews" / item
        review.mkdir(parents=True, exist_ok=True)
        with (review / "proposal_revisions.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(revision) + "\n")
        context["active_item"] = None
        context.pop("pending_reopen", None)
        self.memory.save(context)
        self.memory.record("decisions_reopened", target=item, affected=pending["affected"], feedback=feedback)

    def run(self) -> str:
        """Resume approved disk state and stop at the two human plan gates."""
        pending = self.memory.read().get("pending_reopen")
        if pending:
            self.reopen(pending["target"], pending["feedback"])

        # Gate 1: the Architect plans the whole requirements and architecture phase.
        # The human either approves it, or approves it with BUILD_NOW to skip the
        # specification documents and build straight from the plan.
        self._run_plan(ARCHITECTURE_PLAN, (BUILD_NOW,))
        build_now = self._build_now()

        self.runner.run_step("stack-lock", ARCHITECTURE_PLAN.stage, ARCHITECTURE_PLAN.agent,
                             STACK_INSTRUCTION + (FILE_TREE_INSTRUCTION if build_now else ""),
                             lambda raw: self._validate_stack_lock(raw, build_now),
                             lambda raw: self._publish_stack(raw, build_now))
        if not build_now:
            for task in build_tasks():
                self._run_artifact(task)
            for path in self.memory.read()["approved_adrs"]:
                self._run_artifact(adr_task(path))

        # Gate 2: the Developer plans the build against the approved tree.
        self._run_plan(self._for_mode(IMPLEMENTATION_PLAN, build_now))
        self._run_artifact(self._for_mode(DEVELOPMENT, build_now))
        result = self._run_artifact(PACKAGING)
        return parse_bundle(result)["files"][PACKAGING.path]

    @staticmethod
    def _for_mode(task: StageTask, build_now: bool) -> StageTask:
        """Tell the Developer which specification actually exists in this run."""
        return replace(task, instruction=task.instruction + BUILD_NOW_NOTE) if build_now else task
