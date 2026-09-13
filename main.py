"""Entrypoint: read the brief from INSTRUCTIONS.md and run the SDD crew."""
from __future__ import annotations

import re
import sys

from config.settings import settings
from crew import SpecKitFactory
from services.guardrails import GuardrailValidationError


def load_brief() -> str:
    """Read INSTRUCTIONS.md and strip HTML comment guidance."""
    path = settings.instructions_path
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Add your problem statement there before running."
        )
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text.strip()


def main() -> int:
    print("=== CrewAI Engineering Factory ===")
    if not settings.api_key:
        print("ANTHROPIC_API_KEY is not set. Export it before running.", file=sys.stderr)
        return 1

    try:
        brief = load_brief()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    settings.ensure_directories()
    factory = SpecKitFactory(brief)

    try:
        sign_off = factory.run()
    except GuardrailValidationError as exc:
        print(f"Delivery blocked by guardrails: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface provider/runtime failures
        print(f"Unexpected failure: {exc}", file=sys.stderr)
        return 3

    print("\n=== Delivery Confirmation ===")
    print(sign_off)
    print("\nArtifacts written to:")
    print(f"  kickoff instruction: {settings.kickoff_path}")
    print(f"  plan:                {settings.plan_path}")
    print(f"  prd:                 {settings.prd_path}")
    for service in factory.services:
        print(f"  {service.name}: {service.output_path} (port {service.port})")
    print("\nQuick-start (framework-dependent, see sign-off above for the exact "
          "command):")
    for service in factory.services:
        print(f"  {service.name}:")
        print(f"    Streamlit -> streamlit run \"{service.output_path}\"")
        print(f"    FastAPI   -> uvicorn <module-for-{service.output_path.name}>:app "
              f"--reload --port {service.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
