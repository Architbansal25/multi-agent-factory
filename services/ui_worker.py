"""One background run of the factory on behalf of the Streamlit UI.

Resumes the project from disk, answers at most one gate with the answer the UI
queued for it, and exits at the next gate instead of prompting on a terminal.
Run by services.ui_runner.ProjectRun.launch; not meant to be started by hand.
"""
from __future__ import annotations

import argparse
import os
import threading
import traceback
from pathlib import Path

from config.settings import Settings
from services.guardrails import GuardrailValidationError
from services.orchestration import ApprovalPaused, Invoke
from services.ui_runner import HEARTBEAT_SECONDS, ProjectRun, now


class AwaitingHuman(ApprovalPaused):
    """The run reached a gate the UI has not answered yet."""


def ui_approval(run: ProjectRun):
    def approve(item: str, gate: str, content: str) -> str:
        answer = run.take_answer(item, gate)
        if answer is None:
            raise AwaitingHuman(f"Waiting for your decision on {item} ({gate}).")
        print(f"\n>>> Human answer for {item} ({gate}): {answer}\n", flush=True)
        return answer
    return approve


def heartbeat(run: ProjectRun, started_at: str, done: threading.Event, lock: threading.Lock) -> None:
    ticks = 0
    # Check for a stop request every second; refresh the heartbeat less often.
    while not done.wait(1):
        ticks += 1
        with lock:
            if done.is_set():
                return
            if run.stop_path.exists():
                run.stop_path.unlink(missing_ok=True)
                run.write_status(state="stopped", started_at=started_at, finished_at=now(),
                                 message="Stopped by you. Resume to continue from the last saved step.")
                print("\n>>> Stopped from the UI.\n", flush=True)
                os._exit(5)
            if ticks % HEARTBEAT_SECONDS == 0:
                run.write_status(state="running", started_at=started_at, heartbeat_at=now(),
                                 message="Agents are working...")


def execute(root: Path, reopen: str | None = None, feedback: str | None = None,
            invoke: Invoke | None = None) -> dict:
    """Run until the next gate or the end; returns the final status written."""
    from crew import SpecKitFactory

    run = ProjectRun(root)
    started_at = now()
    run.write_status(state="running", started_at=started_at, heartbeat_at=started_at,
                     message="Agents are working...")
    done, lock = threading.Event(), threading.Lock()
    threading.Thread(target=heartbeat, args=(run, started_at, done, lock), daemon=True).start()
    settings = Settings(project_dir=root)
    try:
        if not settings.api_key and invoke is None:
            raise ValueError("ANTHROPIC_API_KEY is not set. Enter it in the sidebar.")
        brief = run.brief()
        if not brief.strip():
            raise ValueError("The engineering brief is empty.")
        factory = SpecKitFactory(brief, settings, ui_approval(run), invoke)
        if reopen:
            factory.reopen(reopen, feedback or "")
        sign_off = factory.run()
        status = {"state": "done", "message": "Delivery complete.", "sign_off": sign_off}
    except AwaitingHuman as exc:
        status = {"state": "waiting", "message": str(exc)}
    except ApprovalPaused as exc:
        status = {"state": "paused", "message": str(exc)}
    except GuardrailValidationError as exc:
        status = {"state": "failed", "message": f"Delivery blocked by guardrails: {exc}"}
    except (OSError, ValueError) as exc:
        status = {"state": "failed", "message": f"Delivery blocked: {exc}"}
    except Exception as exc:  # noqa: BLE001 - surface provider/runtime failures to the UI
        traceback.print_exc()
        status = {"state": "failed", "message": f"Unexpected failure: {exc}"}
    status.update(started_at=started_at, finished_at=now())
    # Under the lock, so a heartbeat already in flight cannot mark the run live again.
    with lock:
        done.set()
        run.write_status(**status)
    print(f"\n>>> {status['state'].upper()}: {status['message']}\n", flush=True)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reopen")
    parser.add_argument("--feedback")
    args = parser.parse_args()
    status = execute(args.output.resolve(), args.reopen, args.feedback)
    return 0 if status["state"] in {"done", "waiting", "paused"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
