"""Standard-library tests. No installs, network, Docker or model downloads."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
for directory in (ROOT / "src", ROOT / "tests"):
    for file in directory.rglob("*.py"):
        ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
