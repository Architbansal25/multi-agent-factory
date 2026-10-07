"""Bridge between the Streamlit UI and the human-gated factory.

The factory already persists every decision under <project>/memory, and its gates
are resumable, so the UI never holds a run open while waiting for a person. Each
UI action launches one worker process (services/ui_worker.py) that resumes the
project from disk, applies at most one queued human answer, and exits when it
reaches the next gate, finishes or fails. The UI then reads the same disk state.

UI bookkeeping lives in <project>/.ui, never in memory/: everything under memory/
is sent to the agents on every invocation.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from services.orchestration import State
from tasks.speckit_tasks import ARCHITECTURE_PLAN, DEVELOPMENT, IMPLEMENTATION_PLAN, PACKAGING, build_tasks

UI_DIR = ".ui"
# A live worker refreshes its status this often; one silent for much longer is dead.
HEARTBEAT_SECONDS = 5
STALE_AFTER_SECONDS = 45

BUILD_NOW = "build-now"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:60]


class ProjectRun:
    """Files one project's UI and worker share."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.ui = root / UI_DIR
        self.status_path = self.ui / "run.json"
        self.answer_path = self.ui / "answer.json"
        self.stop_path = self.ui / "stop"
        self.log_path = self.ui / "run.log"
        self.brief_path = self.ui / "brief.md"
        self.memory = root / "memory"
        self.context_path = self.memory / "context.json"

    # ---- disk state ----------------------------------------------------------
    @property
    def exists(self) -> bool:
        return self.context_path.exists()

    def context(self) -> dict:
        try:
            return json.loads(self.context_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def brief(self) -> str:
        for path in (self.memory / "00_brief.md", self.brief_path):
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""

    def events(self) -> list[dict]:
        path = self.memory / "04_task_log.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def log_tail(self, max_chars: int = 20000) -> str:
        if not self.log_path.exists():
            return ""
        with self.log_path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_chars))
            text = handle.read().decode("utf-8", errors="replace")
        return strip_ansi(text)

    # ---- worker status -------------------------------------------------------
    def write_status(self, **status: object) -> None:
        self.ui.mkdir(parents=True, exist_ok=True)
        temporary = self.status_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(status, indent=2), encoding="utf-8")
        temporary.replace(self.status_path)

    def status(self) -> dict:
        try:
            status = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"state": "idle"}
        if status.get("state") == "running":
            beat = status.get("heartbeat_at") or status.get("started_at")
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(beat)).total_seconds()
            except (TypeError, ValueError):
                age = STALE_AFTER_SECONDS + 1
            if age > STALE_AFTER_SECONDS:
                status = {**status, "state": "crashed",
                          "message": "The worker stopped responding. Check the agent log, then resume."}
        return status

    def is_running(self) -> bool:
        return self.status().get("state") == "running"

    # ---- human answers -------------------------------------------------------
    def queue_answer(self, item: str, gate: str, response: str) -> None:
        self.ui.mkdir(parents=True, exist_ok=True)
        self.answer_path.write_text(json.dumps({"item": item, "gate": gate, "response": response,
                                                "queued_at": now()}), encoding="utf-8")

    def take_answer(self, item: str, gate: str) -> str | None:
        """Hand the queued answer to the gate it was given for, exactly once."""
        try:
            answer = json.loads(self.answer_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if answer.get("item") != item or answer.get("gate") != gate:
            # Given for a gate that is no longer pending; never apply it elsewhere.
            return None
        self.answer_path.unlink(missing_ok=True)
        return str(answer.get("response", ""))

    def request_stop(self) -> None:
        self.ui.mkdir(parents=True, exist_ok=True)
        self.stop_path.write_text(now(), encoding="utf-8")

    # ---- launching -----------------------------------------------------------
    def launch(self, base_dir: Path, api_key: str = "", reopen: str | None = None,
               feedback: str | None = None) -> None:
        if self.is_running():
            raise RuntimeError("A run is already in progress for this project.")
        self.ui.mkdir(parents=True, exist_ok=True)
        self.stop_path.unlink(missing_ok=True)
        command = [sys.executable, "-u", "-m", "services.ui_worker", "--output", str(self.root)]
        if reopen:
            command += ["--reopen", reopen, "--feedback", feedback or ""]
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
               "NO_COLOR": "1", "TERM": "dumb"}
        if api_key:
            env["ANTHROPIC_API_KEY"] = api_key
        # Marked running before the process starts so a quick rerun cannot launch twice.
        self.write_status(state="running", started_at=now(), heartbeat_at=now(),
                          message="Starting the agents...")
        log = self.log_path.open("a", encoding="utf-8")
        log.write(f"\n===== run started {now()} =====\n")
        log.flush()
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            subprocess.Popen(command, cwd=base_dir, stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env, **kwargs)
        except OSError as exc:
            self.write_status(state="failed", finished_at=now(), message=f"Could not start worker: {exc}")
            raise
        finally:
            log.close()


def bullets(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    return [line[2:].strip() if line.startswith(("- ", "* ")) else line for line in lines if line]


def compose_brief(problem: str, constraints: str, stack_rows, criteria: str) -> str:
    """Write the guided form in the same layout as INSTRUCTIONS.md.

    The stack-lock guardrail reads every '## ... Constraints' section of the brief
    line by line, so the headings and the table header must stay exactly like this.
    """
    parts = ["# Engineering Team Brief", "", "## Problem Statement", "", problem.strip(), ""]
    items = bullets(constraints)
    if items:
        parts += ["## System Constraints", "", *[f"- {item}" for item in items], ""]
    if hasattr(stack_rows, "to_dict"):  # a DataFrame, depending on the Streamlit version
        stack_rows = stack_rows.to_dict("records")
    rows = [(str(row.get("Constraint") or "").strip(), str(row.get("Rule") or "").strip())
            for row in stack_rows]
    rows = [(name, rule) for name, rule in rows if name and rule]
    if rows:
        parts += ["## Mandatory Tech Stack & Constraints", "| Constraint | Rule |", "|---|---|",
                  *[f"| {name.replace('|', '/')} | {rule.replace('|', '/')} |" for name, rule in rows], ""]
    items = bullets(criteria)
    if items:
        parts += ["## Acceptance Criteria", "", *[f"- {item}" for item in items], ""]
    return "\n".join(parts)


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)


def list_projects(base_dir: Path, projects_dir: Path) -> list[Path]:
    """Every project root the UI can open: its own projects plus CLI output folders."""
    candidates = []
    if projects_dir.exists():
        candidates += [path for path in projects_dir.iterdir() if path.is_dir()]
    candidates += [path for path in base_dir.glob("generated*") if path.is_dir()]
    found = [path for path in candidates if (path / "memory" / "context.json").exists()]
    return sorted(set(found), key=lambda path: (path / "memory" / "context.json").stat().st_mtime,
                  reverse=True)


def pending_gate(context: dict) -> tuple[str, str] | None:
    """The (item, gate) waiting on the human, if the run is stopped at one."""
    active = context.get("active_item") or {}
    state = active.get("state")
    if state == State.AWAITING_PROPOSAL_APPROVAL.value:
        return active["id"], "proposal"
    if state == State.AWAITING_OUTPUT_APPROVAL.value:
        return active["id"], "output"
    return None


def pipeline(context: dict) -> list[dict]:
    """Ordered steps with their status: done, active, waiting, skipped or pending."""
    completed = context.get("completed_items", {})
    active = (context.get("active_item") or {}).get("id")
    build_now = context.get("approval_modes", {}).get(ARCHITECTURE_PLAN.name) == BUILD_NOW
    adrs = context.get("approved_adrs") or []
    gate = pending_gate(context)

    steps = [
        (ARCHITECTURE_PLAN.name, "Architecture plan", "architect", True),
        ("stack-lock", "Stack lock", "architect", False),
        *[(task.name, task.name.upper(), task.agent, False) for task in build_tasks()],
    ]
    if adrs:
        steps += [(path.rsplit("/", 1)[-1][:-3], f"ADR {path.rsplit('/', 1)[-1][:-3]}", "architect", False)
                  for path in adrs]
    else:
        steps.append(("__adrs__", "ADRs", "architect", False))
    steps += [
        (IMPLEMENTATION_PLAN.name, "Implementation plan", "senior_developer", True),
        (DEVELOPMENT.name, "Source code", "senior_developer", False),
        (PACKAGING.name, "Delivery package", "manager", False),
    ]
    spec_items = {"prd", "fr", "nfr", "hld", "__adrs__"}
    result = []
    for item, label, agent, is_gate in steps:
        if item in completed:
            status = "done"
        elif item == active:
            status = "waiting" if gate and gate[0] == item else "active"
        elif build_now and item in spec_items:
            status = "skipped"
        else:
            status = "pending"
        result.append({"item": item, "label": label, "agent": agent, "gate": is_gate, "status": status})
    return result
