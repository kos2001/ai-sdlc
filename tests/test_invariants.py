"""Repository invariants. Each one exists because the mistake it prevents actually happened (see lessons/ledger.json)."""

import re
import socket
import tempfile
import unittest
from pathlib import Path

from sdlc import cli

ROOT = Path(__file__).resolve().parent.parent
MAX_FILE = 12 * 1024


class InvariantTest(unittest.TestCase):
    def test_package_files_fit_input_size_gate(self):
        """L-003: sdlc/cli.py grew to 12.2 KB and failed lls-kit's input-size gate once vendored."""
        paths = [*ROOT.glob("sdlc/*.py"), *[p for p in ROOT.glob("sdlc/webapp/*") if p.suffix in {".js", ".css", ".html"}]]
        too_big = [f"{p.relative_to(ROOT)} {p.stat().st_size}" for p in paths if p.stat().st_size > MAX_FILE]
        self.assertEqual(too_big, [])

    def test_pages_declare_utf8(self):
        """L-007: without <meta charset>, the Korean site rendered as mojibake when served locally."""
        for rel in ("web/index.html", "sdlc/webapp/index.html"):
            head = (ROOT / rel).read_text(encoding="utf-8")[:600].lower()
            self.assertIn('<meta charset="utf-8">', head, rel)

    def test_frontmatter_descriptions_with_colons_are_quoted(self):
        """L-008: an unquoted description containing ': ' is invalid YAML for Claude Code's parser."""
        files = [*ROOT.glob(".claude/agents/*.md"), *ROOT.glob(".claude/skills/*/SKILL.md")]
        self.assertTrue(files)
        for path in files:
            line = next(l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("description:"))
            value = line.split(":", 1)[1].strip()
            if ": " in value:
                self.assertTrue(value.startswith('"') and value.endswith('"'), path.name)

    def test_site_brand_mark_has_all_six_arcs(self):
        """L-009: a regex expected stroke-width="7" while the SVG said "7.0", so the logo shipped with no arcs."""
        site = (ROOT / "web/index.html").read_text(encoding="utf-8")
        for stage in ("plan", "design", "build", "test", "deploy", "maintain"):
            self.assertGreaterEqual(site.count(f'stroke="var(--st-{stage})" stroke-width="7'), 2, stage)

    def test_no_element_template_repeats_the_style_attribute(self):
        """L-010: a pipeline link had two style attributes; browsers silently drop the second."""
        twice = re.compile(r"<[a-z][^<>]*\sstyle=[^<>]*\sstyle=")
        for path in ROOT.glob("sdlc/webapp/*.js"):
            self.assertIsNone(twice.search(path.read_text(encoding="utf-8")), path.name)

    def test_serve_reports_a_busy_port_instead_of_crashing(self):
        """L-006: `sdlc serve` died with an OSError traceback when the port was taken."""
        with socket.socket() as busy, tempfile.TemporaryDirectory() as tmp:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            port = busy.getsockname()[1]
            self.assertEqual(cli.main(["--root", tmp, "serve", "--port", str(port)]), 1)


if __name__ == "__main__":
    unittest.main()
