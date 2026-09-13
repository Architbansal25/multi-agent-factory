import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import Settings
from main import load_brief, main


class CliTests(unittest.TestCase):
    def test_brief_is_preserved_verbatim(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "instructions.md"
            content = "<!-- guidance -->\n\nJavaScript brief\n"
            path.write_text(content, encoding="utf-8")
            self.assertEqual(load_brief(Settings(brief_path=path)), content)

    def test_empty_brief_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "instructions.md"
            path.write_text("  \n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_brief(Settings(brief_path=path))

    @patch("sys.argv", ["main.py"])
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""})
    def test_missing_key_does_not_invoke_agents(self):
        with patch("main.SpecKitFactory") as factory:
            self.assertEqual(main(), 1)
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()