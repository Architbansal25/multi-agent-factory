"""Disk-backed, fail-closed human approval gates."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class State(str, Enum):
    DRAFTING_PROPOSAL = "DRAFTING_PROPOSAL"
    AWAITING_PROPOSAL_APPROVAL = "AWAITING_PROPOSAL_APPROVAL"
    PROPOSAL_REVISION = "PROPOSAL_REVISION"
    EXECUTING = "EXECUTING"
    AWAITING_OUTPUT_APPROVAL = "AWAITING_OUTPUT_APPROVAL"
    OUTPUT_REVISION = "OUTPUT_REVISION"
    STAGE_COMPLETE = "STAGE_COMPLETE"


class ApprovalPaused(Exception):
    """The human stopped at a gate; disk state can be resumed."""


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.folder = root / "memory"
        self.context_path = self.folder / "context.json"

    def initialize(self, brief: str, project_name: str) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        if self.context_path.exists():
            if (self.folder / "00_brief.md").read_text(encoding="utf-8") != brief:
                raise ValueError("Brief changed. Use a new output directory for a new project.")
            return
        (self.folder / "00_brief.md").write_text(brief, encoding="utf-8")
        self.save({
            "project_name": project_name,
            "stage": "requirements",
            "current_agent": "manager",
            "locked_stack": {},
            "global_constraints": [],
            "approved_decisions": [],
            "open_revisions": [],
            "completed_items": {},
            "approval_modes": {},
            "active_item": None,
        })
        self.record("initialized", brief_path="memory/00_brief.md")

    def read(self) -> dict:
        return json.loads(self.context_path.read_text(encoding="utf-8"))

    def save(self, context: dict) -> None:
        temporary = self.context_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(context, indent=2), encoding="utf-8")
        # Windows denies the rename outright while a virus scanner or indexer has
        # either file open for a moment. The swap is still the atomic one we want,
        # it just has to wait its turn rather than lose the whole run's state.
        for delay in (0.01, 0.05, 0.1, 0.25, 0.5, None):
            try:
                temporary.replace(self.context_path)
                return
            except PermissionError:
                if delay is None:
                    raise
                time.sleep(delay)

    def record(self, event: str, **details: object) -> None:
        with (self.folder / "04_task_log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": timestamp(), "event": event, **details}) + "\n")

    def snapshot(self) -> str:
        sections = ["memory/context.json\n" + self.context_path.read_text(encoding="utf-8")]
        for path in sorted(self.folder.rglob("*")):
            if path.is_file() and path != self.context_path and path.suffix in {".md", ".json", ".jsonl"}:
                sections.append(f"{path.relative_to(self.root).as_posix()}\n{path.read_text(encoding='utf-8')}")
        return "\n\n".join(sections)


Invoke = Callable[[str, str, str], str]
Approve = Callable[[str, str, str], str]


def rejection_note(active: dict) -> str:
    """Quote the controller's own rejection back to the agent.

    Nothing else tells the agent why its last deliverable was thrown away, so a
    retry otherwise reproduces the rejected output verbatim until the attempt
    budget runs out.
    """
    rejection = active.get("last_rejection")
    if not rejection:
        return ""
    return (
        "\n\nThe controller REJECTED your previous output for this item "
        f"(this is attempt {active['validation_failures'] + 1} of 3): {rejection}\n"
        "Correct exactly that problem and return the whole deliverable again. "
        "Emit the raw JSON object and nothing else: no code fence, no commentary "
        "before or after it."
    )


class HumanGatedRunner:
    """Drives items through the persisted, resumable approval state machine.

    Approval is per PHASE, not per artifact: the human approves one plan, and the
    artifacts produced under it are checked by the programmatic guardrails instead
    of by another round of prompts.
    """

    def __init__(self, memory: MemoryStore, invoke: Invoke, approve: Approve) -> None:
        self.memory = memory
        self.invoke = invoke
        self.approve = approve

    def run_plan(
        self,
        item: str,
        stage: str,
        agent: str,
        instruction: str,
        publish: Callable[[str], None],
        modes: tuple[str, ...] = (),
    ) -> str:
        """One human gate. The plan the human approves is itself the artifact.

        Nothing is executed afterwards, so the approved words are the record -
        re-asking the agent to restate its own plan as JSON would only invite drift.

        `modes` are extra ways to say yes, answered as "approve <mode>". The chosen
        one is recorded in context.approval_modes so the caller can branch on it -
        a decision the human makes at a gate they are already stopped at, rather
        than another prompt or another model call.
        """
        return self._run(item, stage, agent, instruction, lambda raw: None, publish,
                         plan_gate=True, execute=False, output_gate=False, modes=modes)

    def run_step(
        self,
        item: str,
        stage: str,
        agent: str,
        instruction: str,
        validate: Callable[[str], None],
        publish: Callable[[str], None],
    ) -> str:
        """No human gate: carries out work an approved plan already covers."""
        return self._run(item, stage, agent, instruction, validate, publish,
                         plan_gate=False, execute=True, output_gate=False)

    def run_item(
        self,
        item: str,
        stage: str,
        agent: str,
        instruction: str,
        validate: Callable[[str], None],
        publish: Callable[[str], None],
    ) -> str:
        """Both gates: the human approves the proposal and then the deliverable."""
        return self._run(item, stage, agent, instruction, validate, publish,
                         plan_gate=True, execute=True, output_gate=True)

    def _run(
        self,
        item: str,
        stage: str,
        agent: str,
        instruction: str,
        validate: Callable[[str], None],
        publish: Callable[[str], None],
        *,
        plan_gate: bool,
        execute: bool,
        output_gate: bool,
        modes: tuple[str, ...] = (),
    ) -> str:
        context = self.memory.read()
        if item in context["completed_items"]:
            return (self.memory.folder / context["completed_items"][item]).read_text(encoding="utf-8")
        active = context["active_item"]
        if active and active["id"] != item:
            raise ValueError(f"Finish pending item {active['id']} before starting {item}.")
        review = self.memory.folder / "reviews" / item
        review.mkdir(parents=True, exist_ok=True)
        if not active:
            context.update(stage=stage, current_agent=agent, active_item={
                "id": item,
                "state": (State.DRAFTING_PROPOSAL if plan_gate else State.EXECUTING).value,
                "validation_failures": 0,
            })
        else:
            # Resuming is a deliberate human retry: give the item a fresh attempt
            # budget instead of failing on a count left over from an earlier run.
            active["validation_failures"] = 0
        self.memory.save(context)
        proposal_path = review / "proposal.md"
        output_path = review / ("output.json" if execute else "approved_plan.md")
        while True:
            context = self.memory.read()
            active = context["active_item"]
            state = State(active["state"])
            if state in {State.DRAFTING_PROPOSAL, State.PROPOSAL_REVISION}:
                proposal = self.invoke(agent, "proposal", instruction)
                if not proposal.strip():
                    raise ValueError("Empty proposal; execution blocked.")
                proposal_path.write_text(proposal, encoding="utf-8")
                self.memory.record("proposal", item=item, content=proposal)
                active["state"] = State.AWAITING_PROPOSAL_APPROVAL.value
            elif state in {State.EXECUTING, State.OUTPUT_REVISION}:
                output = self.invoke(agent, "execute", instruction + rejection_note(active))
                output_path.write_text(output, encoding="utf-8")
                self.memory.record("output", item=item, content=output)
                try:
                    validate(output)
                except ValueError as exc:
                    active["validation_failures"] += 1
                    active["last_rejection"] = str(exc)
                    self.memory.record("validation_rejected", item=item, feedback=str(exc))
                    active["state"] = State.OUTPUT_REVISION.value
                    self.memory.save(context)
                    if active["validation_failures"] >= 3:
                        raise ValueError(f"{item}: validation failed three times: {exc}") from exc
                    continue
                active.pop("last_rejection", None)
                active["state"] = (State.AWAITING_OUTPUT_APPROVAL if output_gate
                                   else State.STAGE_COMPLETE).value
            elif state in {State.AWAITING_PROPOSAL_APPROVAL, State.AWAITING_OUTPUT_APPROVAL}:
                gate = "proposal" if state == State.AWAITING_PROPOSAL_APPROVAL else "output"
                candidate = (proposal_path if gate == "proposal" else output_path).read_text(encoding="utf-8")
                if gate == "output":
                    validate(candidate)
                response = self.approve(item, gate, candidate)
                if response.strip().lower() == "quit":
                    self.memory.record("paused", item=item, gate=gate)
                    raise ApprovalPaused("Paused. Run the same command to resume this gate.")
                verb, _, chosen = response.strip().partition(" ")
                chosen = chosen.strip().lower()
                # "approve" alone, or "approve <mode>" for a mode this gate offers.
                # An unrecognised word is not an approval - it is a typo, and a typo
                # must never be read as consent to build.
                if verb.lower() == "approve" and (not chosen or chosen in modes):
                    self.memory.record("approved", item=item, gate=gate, mode=chosen or None, content=candidate)
                    for revision in context["open_revisions"]:
                        if revision["item"] == item and revision["gate"] == gate:
                            revision["resolved"] = True
                    if chosen:
                        context.setdefault("approval_modes", {})[item] = chosen
                    if gate == "proposal" and not execute:
                        output_path.write_text(candidate, encoding="utf-8")
                    active["state"] = (State.EXECUTING if gate == "proposal" and execute
                                       else State.STAGE_COMPLETE).value
                elif response.lower().startswith("revise ") and response[7:].strip():
                    feedback = response[7:]
                    revision = {"item": item, "stage": stage, "gate": gate, "feedback": feedback,
                                "raised_at": timestamp(), "resolved": False}
                    context["open_revisions"].append(revision)
                    self.memory.record("revision", **revision)
                    with (review / f"{gate}_revisions.jsonl").open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(revision) + "\n")
                    active["state"] = (State.PROPOSAL_REVISION if gate == "proposal" else State.OUTPUT_REVISION).value
                else:
                    self.memory.record("invalid_approval", item=item, gate=gate)
                    continue
            elif state == State.STAGE_COMPLETE:
                output = output_path.read_text(encoding="utf-8")
                validate(output)
                publish(output)
                context = self.memory.read()
                # An ungated item never passes through the approve branch, so its
                # reopen feedback is only discharged here, on completion.
                for revision in context["open_revisions"]:
                    if revision["item"] == item:
                        revision["resolved"] = True
                record = output_path.relative_to(self.memory.folder).as_posix()
                context["completed_items"][item] = record
                context["approved_decisions"].append({
                    "stage": stage, "decision": f"Approved {item}; see memory/{record}",
                    "approved_at": timestamp(),
                })
                context["active_item"] = None
                self.memory.save(context)
                self.memory.record("stage_complete", item=item, stage=stage)
                with (self.memory.folder / "05_handoff_log.md").open("a", encoding="utf-8") as handle:
                    handle.write(f"\n## {timestamp()} - {stage}: {item}\nApproved output: memory/reviews/{item}/output.json\n")
                return output
            self.memory.save(context)