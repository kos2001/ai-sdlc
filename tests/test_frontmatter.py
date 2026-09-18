import unittest

from sdlc import frontmatter


class FrontmatterTest(unittest.TestCase):
    def test_round_trip_all_supported_shapes(self):
        text = (
            "---\n"
            "id: W-0001\n"
            'owner: "Dana <d@x.com>"  # comment\n'
            "skills: [a, b]\n"
            "empty: []\n"
            "sources:\n"
            "  - kind: ticket\n"
            "    ref: SUP-1\n"
            "  - plain\n"
            "---\n"
            "# Body\n"
        )
        meta, body = frontmatter.load(text)
        self.assertEqual(meta["owner"], "Dana <d@x.com>")
        self.assertEqual(meta["skills"], ["a", "b"])
        self.assertEqual(meta["empty"], [])
        self.assertEqual(meta["sources"], [{"kind": "ticket", "ref": "SUP-1"}, "plain"])
        self.assertEqual(body, "# Body\n")
        again, again_body = frontmatter.load(frontmatter.render(meta, body))
        self.assertEqual(again, meta)
        self.assertEqual(again_body, body)

    def test_hash_inside_quotes_is_not_a_comment(self):
        meta, _ = frontmatter.load('---\nmetric: "p95 # ms"\n---\n')
        self.assertEqual(meta["metric"], "p95 # ms")

    def test_missing_fence_is_an_error(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.load("id: x\n")
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.load("---\nid: x\n")

    def test_unsupported_nesting_is_rejected_not_guessed(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.load("---\na: 1\n  b: 2\n---\n")

    def test_dump_quotes_values_that_would_reparse_differently(self):
        meta = {"x": "a: b", "y": "[not a list]", "z": ""}
        parsed, _ = frontmatter.load(frontmatter.render(meta, ""))
        self.assertEqual(parsed, meta)


if __name__ == "__main__":
    unittest.main()
