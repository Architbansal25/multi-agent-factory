"""Programmatic guardrails wired into CrewAI task validation."""
# NOTE: no `from __future__ import annotations` here - CrewAI inspects the
# real `Tuple[bool, Any]` return-annotation object on `code_guardrail`, and
# postponed evaluation would turn it into an unusable string at runtime.
import re
import ast
import json
from pathlib import Path, PurePosixPath
from typing import Any, Tuple

# UI framework imports the developer output must reference.
REQUIRED_UI_IMPORTS = ["streamlit", "fastapi", "flask"]

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*|\s*```\s*$", re.MULTILINE)

# Matches a fenced block wrapping the WHOLE response, so fences inside file
# contents (mermaid blocks in hld.md, for example) are left untouched.
_WRAPPING_FENCE_RE = re.compile(
    r"\A```[a-zA-Z0-9_-]*[ \t]*\r?\n(?P<body>.*?)\r?\n?[ \t]*```\Z", re.DOTALL
)


class GuardrailValidationError(ValueError):
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


def json_candidates(raw: str):
    """Yield the deliverable as sent, then unwrapped progressively.

    Models keep wrapping the JSON in a ```json fence or a sentence of prose even
    when told not to, and a retry loop cannot argue them out of it. Peeling the
    outermost wrapper here keeps that formatting habit from burning an item's
    whole retry budget on unparseable output.
    """
    text = raw.strip()
    yield text
    match = _WRAPPING_FENCE_RE.match(text)
    if match:
        text = match.group("body").strip()
        yield text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start and (start, end) != (0, len(text) - 1):
        yield text[start:end + 1]


def parse_bundle(raw: str) -> dict:
    if not isinstance(raw, str):
        raise GuardrailValidationError(f"Return a valid JSON object: got {type(raw).__name__}.")
    failure = None
    for candidate in json_candidates(raw):
        try:
            bundle = json.loads(candidate)
        except json.JSONDecodeError as exc:
            failure = failure or exc
            continue
        if not isinstance(bundle, dict):
            raise GuardrailValidationError("The deliverable must be a JSON object.")
        return bundle
    raise GuardrailValidationError(f"Return a valid JSON object: {failure}")


def safe_path(root: Path, relative: str, prefix: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise GuardrailValidationError(f"Invalid artifact path: {relative!r}")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} or part.rstrip(". ") != part for part in parts):
        raise GuardrailValidationError(f"Unsafe artifact path: {relative}")
    reserved = {"CON", "PRN", "AUX", "NUL", *[f"COM{number}" for number in range(1, 10)],
                *[f"LPT{number}" for number in range(1, 10)]}
    if any(part.split(".")[0].upper() in reserved or any(char in part for char in '*?<>|"') for part in parts):
        raise GuardrailValidationError(f"Invalid cross-platform path: {relative}")
    if not relative.startswith(prefix + "/") or PurePosixPath(relative).is_absolute():
        hint = ""
        if prefix == "src" and not PurePosixPath(relative).is_absolute():
            # Overwhelmingly this is a conventional project layout (package.json,
            # tests/, public/) written relative to the project root. Say what the
            # path should have been instead of restating the rule.
            hint = (f" {prefix}/ is the generated project's root directory, so every path "
                    f"belongs inside it - write {prefix}/{relative} instead. Relocating it "
                    "that way is not a design change; do not rename or drop the file.")
        raise GuardrailValidationError(f"Artifact must be under {prefix}/: {relative}.{hint}")
    candidate = root.joinpath(*parts)
    if not candidate.resolve().is_relative_to((root / prefix).resolve()):
        raise GuardrailValidationError(f"Path escapes the output directory: {relative}")
    for parent in [candidate, *candidate.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise GuardrailValidationError(f"Linked artifact paths are not allowed: {relative}")
    return candidate


def validate_files(bundle: dict, expected: list[str], root: Path, prefix: str) -> dict[str, str]:
    files = bundle.get("files")
    if not isinstance(files, dict) or set(files) != set(expected):
        raise GuardrailValidationError(f"Output must contain exactly these files: {expected}")
    if len({path.casefold() for path in files}) != len(files):
        raise GuardrailValidationError("Case-insensitive path collision.")
    for relative, content in files.items():
        safe_path(root, relative, prefix)
        if not isinstance(content, str):
            raise GuardrailValidationError(f"File content must be text: {relative}")
        if not content.strip() and not relative.endswith("__init__.py"):
            raise GuardrailValidationError(f"Empty deliverable: {relative}")
    return files


def validate_stack(bundle: dict, locked: dict) -> None:
    if bundle.get("stack") != locked:
        raise GuardrailValidationError("Deliverable stack must exactly match context.json.locked_stack.")


LANGUAGE_EXTENSIONS = {
    "python": {".py"}, "typescript": {".ts", ".tsx"}, "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "java": {".java"}, "kotlin": {".kt", ".kts"}, "c#": {".cs"}, "csharp": {".cs"},
    "go": {".go"}, "golang": {".go"}, "rust": {".rs"}, "ruby": {".rb"}, "php": {".php"},
    "swift": {".swift"}, "dart": {".dart"}, "c++": {".cpp", ".hpp", ".cc", ".h"}, "c": {".c", ".h"},
}


def source_extensions(locked: dict) -> set[str]:
    language = locked["language"].lower()
    extensions: set[str] = set()
    for name, suffixes in LANGUAGE_EXTENSIONS.items():
        if re.search(r"(?<![a-z+#])" + re.escape(name) + r"(?![a-z+#])", language):
            extensions.update(suffixes)
    if not extensions:
        raise GuardrailValidationError(f"No language validator for {language!r}; add one before generating code.")
    return extensions


def is_test_path(path: str) -> bool:
    return any(part in {"test", "tests", "__tests__"} for part in path.split("/")) or bool(
        re.search(r"(^|/)(test_.*|.*_test\.[^/]+|.*\.(test|spec)\.[^/]+)$", path)
    )


def validate_tree(tree: object, root: Path, locked: dict, require_tests: bool = True) -> list[str]:
    if not isinstance(tree, list) or not tree or not all(isinstance(path, str) for path in tree):
        raise GuardrailValidationError("HLD file_tree must be a nonempty list of file paths.")
    if len({path.casefold() for path in tree}) != len(tree):
        raise GuardrailValidationError("Duplicate or case-colliding paths in approved tree.")
    extensions = source_extensions(locked)
    known_extensions = set().union(*LANGUAGE_EXTENSIONS.values())
    modules = []
    for relative in tree:
        safe_path(root, relative, "src")
        if any(other.startswith(relative.casefold() + "/") for other in [path.casefold() for path in tree]):
            raise GuardrailValidationError(f"File/directory collision: {relative}")
        suffix = PurePosixPath(relative).suffix
        if suffix in known_extensions and suffix not in extensions:
            if not (".ts" in extensions and suffix in {".js", ".mjs", ".cjs"} and ".config." in relative):
                raise GuardrailValidationError(f"File language contradicts the locked stack: {relative}")
        if suffix in extensions and not is_test_path(relative) and not relative.endswith("__init__.py"):
            modules.append(relative)
    if len(modules) < 2:
        raise GuardrailValidationError("Approve at least two application source modules, not a single-file script.")
    if require_tests and not any(
        is_test_path(path) and PurePosixPath(path).suffix in extensions for path in tree
    ):
        raise GuardrailValidationError("The approved tree must include tests in the locked language.")
    return tree


def validate_implementation(bundle: dict, root: Path, locked: dict, tree: list[str],
                            require_tests: bool = True) -> None:
    validate_stack(bundle, locked)
    validate_tree(tree, root, locked, require_tests)
    files = validate_files(bundle, tree, root, "src")
    python_imports: set[str] = set()
    dependencies: set[str] = set()
    for relative, content in files.items():
        if relative.endswith(".py"):
            try:
                parsed = ast.parse(content, filename=relative)
                compile(parsed, relative, "exec")
            except (SyntaxError, ValueError) as exc:
                raise GuardrailValidationError(f"Invalid Python in {relative}: {exc}") from exc
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    python_imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    python_imports.add(node.module.split(".")[0])
        if relative.endswith("package.json"):
            package = parse_bundle(content)
            for key in ("dependencies", "devDependencies"):
                entries = package.get(key, {})
                if not isinstance(entries, dict):
                    raise GuardrailValidationError(f"{relative}: {key} must be an object.")
                dependencies.update(entries)
    framework = locked["framework"].lower()
    for name in ("fastapi", "streamlit", "flask", "django"):
        if re.search(r"\b" + name + r"\b", framework) and name not in python_imports:
            raise GuardrailValidationError(f"Locked framework {name} must have an actual Python import.")
    for name, package_name in {"react": "react", "next.js": "next", "nextjs": "next", "vue": "vue",
                               "express": "express", "angular": "@angular/core", "svelte": "svelte"}.items():
        if name in framework and package_name not in dependencies:
            raise GuardrailValidationError(f"Locked framework requires {package_name} in package.json.")
