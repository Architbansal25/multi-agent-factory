"""Programmatic guardrails wired into CrewAI task validation."""
# NOTE: no `from __future__ import annotations` here - CrewAI inspects the
# real `Tuple[bool, Any]` return-annotation object on `code_guardrail`, and
# postponed evaluation would turn it into an unusable string at runtime.
import re
from typing import Any, Tuple

# UI framework imports the developer output must reference.
REQUIRED_UI_IMPORTS = ["streamlit", "fastapi", "flask"]

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*|\s*```\s*$", re.MULTILINE)


class GuardrailValidationError(Exception):
    """Raised when generated code fails a programmatic guardrail check."""


def sanitize(text: str) -> str:
    """Strip markdown code-fence wrappers and surrounding whitespace."""
    return _FENCE_RE.sub("", text).strip()


def check_python_implementation(
    code: str, required_imports: list[str] | None = None
) -> str:
    """Validate syntax with ``compile()`` and verify a UI framework import."""
    required = required_imports or REQUIRED_UI_IMPORTS
    if not code.strip():
        raise GuardrailValidationError("Developer produced empty output.")

    try:
        compile(code, "<generated app.py>", "exec")
    except SyntaxError as exc:
        raise GuardrailValidationError(
            f"Generated code failed the Python syntax check: {exc}"
        ) from exc

    lowered = code.lower()
    if not any(token.lower() in lowered for token in required):
        raise GuardrailValidationError(
            "Generated code does not reference any expected UI framework import "
            f"({', '.join(required)})."
        )
    return code


def code_guardrail(output: Any) -> Tuple[bool, Any]:
    """CrewAI task guardrail: sanitize + validate the developer's output.

    Returns ``(True, cleaned_code)`` on success so the task output is the
    validated source, or ``(False, error_message)`` to trigger a CrewAI retry.
    """
    raw = getattr(output, "raw", None) or str(output)
    try:
        cleaned = sanitize(raw)
        validated = check_python_implementation(cleaned)
    except GuardrailValidationError as exc:
        return (False, f"Guardrail rejected implementation: {exc}")
    return (True, validated)
