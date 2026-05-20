import ast
import unittest
from pathlib import Path


VIEW_PY = Path(__file__).parents[1] / "galley" / "view.py"


class ViewImportTests(unittest.TestCase):
    def test_view_imports_queue_class(self):
        module = ast.parse(VIEW_PY.read_text(encoding="utf-8"))
        queue_imports = {
            alias.name
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module == "queue"
            for alias in node.names
        }

        self.assertIn("Queue", queue_imports)
        self.assertIn("Empty", queue_imports)
        self.assertNotIn("Query", queue_imports)
