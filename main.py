"""CLI for the human-gated engineering factory."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config.settings import Settings
from crew import SpecKitFactory
from services.guardrails import GuardrailValidationError
from services.orchestration import ApprovalPaused


def load_brief(config: Settings | None = None) -> str:
    """Preserve the original input verbatim in shared memory."""
    path = (config or Settings()).instructions_path
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Add your problem statement there before running."
        )
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("The engineering brief is empty.")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a modular app with mandatory human approvals.")
    parser.add_argument("--instructions", type=Path, help="Brief path (default: INSTRUCTIONS.md)")
    parser.add_argument("--output", type=Path, help="Project root (default: generated/); reuse it to resume")
    parser.add_argument("--agents-config", type=Path, help="Override the per-project agent YAML configuration")
    parser.add_argument("--reopen", help="Reopen an approved item through a Manager proposal and output gate")
    parser.add_argument("--feedback", help="Verbatim reason/change request for --reopen")
    args = parser.parse_args()
    if bool(args.reopen) != bool(args.feedback):
        parser.error("--reopen and --feedback must be supplied together")
    settings = Settings(
        brief_path=args.instructions.resolve() if args.instructions else None,
        project_dir=args.output.resolve() if args.output else None,
        agents_config=args.agents_config.resolve() if args.agents_config else None,
    )
    print("=== CrewAI Engineering Factory ===")
    if not settings.api_key:
        print("ANTHROPIC_API_KEY is not set. Export it before running.", file=sys.stderr)
        return 1

    try:
        brief = load_brief(settings)
        factory = SpecKitFactory(brief, settings)
        if args.reopen:
            factory.reopen(args.reopen, args.feedback)
        sign_off = factory.run()
    except ApprovalPaused as exc:
        print(str(exc))
        return 4
    except GuardrailValidationError as exc:
        print(f"Delivery blocked by guardrails: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Delivery blocked: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Paused; run the same command to resume.")
        return 4
    except Exception as exc:  # noqa: BLE001 - surface provider/runtime failures
        print(f"Unexpected failure: {exc}", file=sys.stderr)
        return 3

    print("\n=== Delivery Confirmation ===")
    print(sign_off)
    print(f"\nShared memory: {settings.memory_dir}")
    print(f"Application source: {settings.src_dir}")
    print("Generated tests have not been executed. Review the delivery commands before running them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
