"""Shared fixtures: a throwaway git repo carrying this project's templates and policy."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


class RepoTestCase(unittest.TestCase):
    human = "Dana Park <dana@example.com>"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for name in ("templates", "policy"):
            if (PROJECT / name).is_dir():
                shutil.copytree(PROJECT / name, self.root / name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Dana Park")
        git(self.root, "config", "user.email", "dana@example.com")
        git(self.root, "config", "commit.gpgsign", "false")
        self.commit("init")

    def tearDown(self):
        self._tmp.cleanup()

    def commit(self, message: str) -> None:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", message)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def fill_intent(self, path: Path) -> None:
        text = path.read_text()
        text = text.replace("sources: []", "sources:\n  - kind: ticket\n    ref: SUP-1")
        text = text.replace("## Problem\n", "## Problem\nCheckout is slow for EU users.\n")
        text = text.replace("## Desired outcome\n", "## Desired outcome\np95 < 800ms.\n")
        path.write_text(text)

    def fill_spec(self, path: Path) -> None:
        text = path.read_text().replace(
            "## Acceptance criteria\n", "## Acceptance criteria\n- AC-1 p95 under 800ms\n- AC-2 no regression\n")
        path.write_text(text)

    def fill_plan(self, path: Path, checked: bool = False) -> None:
        box = "x" if checked else " "
        text = path.read_text().replace("- [ ] \n", f"- [{box}] add cache\n- [{box}] add test\n")
        path.write_text(text)
