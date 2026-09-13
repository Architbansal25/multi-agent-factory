import json
import tempfile
import unittest
from pathlib import Path

from services.guardrails import (
    GuardrailValidationError, parse_bundle, safe_path, validate_implementation, validate_tree,
)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.stack = {"language": "TypeScript", "framework": "React", "database": "none", "infra": "local",
                      "locked_at_stage": "kickoff", "locked_by": "human_approved"}
        self.files = {"src/app.tsx": "export const App = () => null;",
                      "src/services/client.ts": "export const message = 'hello';",
                      "src/tests/app.test.ts": "export const testResult = true;",
                      "src/package.json": json.dumps({"dependencies": {"react": "^19.0.0"}})}

    def test_accepts_modular_non_python_stack(self):
        validate_implementation({"files": self.files, "stack": self.stack}, self.root, self.stack, list(self.files))

    def test_conventional_project_layout_is_rejected_with_the_fix_named(self):
        """Agents propose package.json/tests/public at the project root every time.

        The tree is fine; only the prefix is wrong, so the rejection has to say which
        path to write instead - otherwise the agent resends the same tree until its
        retry budget is gone, which is exactly what happened on three real runs.
        """
        stack = {"language": "JavaScript", "framework": "Express.js",
                 "database": "JSON file", "infra": "Node.js"}
        conventional = ["src/server.js", "src/routes/books.js", "public/index.html",
                        "tests/unit/book.test.js", "package.json"]
        with self.assertRaises(GuardrailValidationError) as caught:
            validate_tree(conventional, self.root, stack)
        self.assertIn("src/public/index.html", str(caught.exception))

        prefixed = [p if p.startswith("src/") else "src/" + p for p in conventional]
        self.assertEqual(validate_tree(prefixed, self.root, stack), prefixed)

    def test_rejects_language_substitution(self):
        with self.assertRaises(GuardrailValidationError):
            validate_tree([*self.files, "src/server.py"], self.root, self.stack)

    def test_rejects_unapproved_files(self):
        with self.assertRaises(GuardrailValidationError):
            validate_implementation({"files": {**self.files, "src/extra.ts": "export {};"}, "stack": self.stack},
                                    self.root, self.stack, list(self.files))

    def test_rejects_single_file_and_missing_tests(self):
        for tree in (["src/app.tsx"], ["src/app.tsx", "src/client.ts"]):
            with self.assertRaises(GuardrailValidationError):
                validate_tree(tree, self.root, self.stack)

    def test_rejects_paths_outside_src_and_windows_aliases(self):
        for path in ("src/../key.txt", "C:/key.txt", "/src/app.py", "src\\app.py", "src/NUL.txt", "src/foo. ", "src//app.py"):
            with self.subTest(path=path), self.assertRaises(GuardrailValidationError):
                safe_path(self.root, path, "src")

    def test_requires_framework_dependency(self):
        self.files["src/package.json"] = "{}"
        with self.assertRaises(GuardrailValidationError):
            validate_implementation({"files": self.files, "stack": self.stack}, self.root, self.stack, list(self.files))

    def test_python_framework_name_in_comment_is_not_an_import(self):
        stack = {**self.stack, "language": "Python", "framework": "FastAPI"}
        files = {"src/app.py": "# fastapi\nvalue = 1", "src/service.py": "value = 2", "src/tests/test_app.py": "assert True"}
        with self.assertRaises(GuardrailValidationError):
            validate_implementation({"files": files, "stack": stack}, self.root, stack, list(files))



class BundleParsingTests(unittest.TestCase):
    """Agents wrap the deliverable in a ```json fence no matter what the prompt says."""

    def setUp(self):
        self.bundle = {"locked_stack": {"language": "JavaScript"}, "conflicts": []}

    def test_accepts_a_fenced_deliverable(self):
        raw = "```json\n" + json.dumps(self.bundle, indent=2) + "\n```"
        self.assertEqual(parse_bundle(raw), self.bundle)

    def test_accepts_a_deliverable_surrounded_by_prose(self):
        raw = "Here it is:\n" + json.dumps(self.bundle) + "\nLet me know."
        self.assertEqual(parse_bundle(raw), self.bundle)

    def test_fences_inside_file_contents_are_preserved(self):
        hld = {"files": {"memory/03_architecture/hld.md": "# High-Level Design\n```mermaid\ngraph TD\nA-->B\n```\n"}}
        for raw in (json.dumps(hld), "```json\n" + json.dumps(hld, indent=2) + "\n```"):
            self.assertEqual(parse_bundle(raw), hld)

    def test_non_objects_are_still_rejected(self):
        for raw in ("prose only", "[1, 2]", "", None):
            with self.assertRaises(GuardrailValidationError):
                parse_bundle(raw)


if __name__ == "__main__":
    unittest.main()