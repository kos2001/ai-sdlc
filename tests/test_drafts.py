"""W-0005 draft editing: lifecycle, metadata integrity and optimistic concurrency."""

from concurrent.futures import ThreadPoolExecutor

from sdlc import artifacts, drafts
from tests.test_server import ServerTestCase


class DraftEditingTest(ServerTestCase):
    def test_creation_owner_cannot_inject_gate_metadata(self):  # W-0005:AC-3
        before = sorted((self.root / "work").glob("*/*"))
        for owner in ['Dana"\nstatus: accepted\napprovals: [Someone]\n#', None, {}, "\r", "x" * 2001]:
            status, error = self.post("/api/work", {"title": "Unsafe owner", "owner": owner, "tier": "T1"})
            self.assertEqual(status, 400, error)
        self.assertEqual(sorted((self.root / "work").glob("*/*")), before)

    def new_draft(self):
        status, created = self.post("/api/work", {"title": "Editable draft", "owner": "Dana", "tier": "T1"})
        self.assertEqual(status, 201)
        _, work = self.request("GET", f'/api/work/{created["id"]}')
        path = self.root / created["path"]
        data = {"stage": "intent", "revision": work["chain"]["intent"]["revision"],
                "body": "# Editable draft\n\n## Problem\nSearch is slow.\n\n## Desired outcome\nSearch under 100 ms.\n",
                "sources": [{"kind": "ticket", "ref": "SUP-12"}]}
        return created["id"], path, data

    def test_save_reload_submit_preserves_gate_metadata(self):  # W-0005:AC-2
        work_id, path, data = self.new_draft()
        before = artifacts.load(path, self.root).meta
        status, saved = self.post(f"/api/work/{work_id}/draft", data)
        self.assertEqual(status, 200, saved)
        art = artifacts.load(path, self.root)
        self.assertEqual(art.body, data["body"])
        self.assertEqual(art.meta, {**before, "sources": data["sources"]})
        _, work = self.request("GET", f"/api/work/{work_id}")
        self.assertEqual(work["chain"]["intent"]["revision"], saved["revision"])
        self.assertEqual(work["chain"]["intent"]["body"], data["body"])
        status, submitted = self.post(f"/api/work/{work_id}/submit", {"stage": "intent"})
        self.assertEqual((status, submitted["status"]), (200, "proposed"))
        self.assertEqual(artifacts.load(path, self.root).meta["approvals"], [])

    def test_non_drafts_are_read_only(self):  # W-0005:AC-3
        for work_id, stage in [("W-0003", "intent"), ("W-0004", "plan"), ("W-0001", "plan")]:
            _, work = self.request("GET", f"/api/work/{work_id}")
            a = work["chain"][stage]
            path = self.root / a["path"]
            raw = path.read_bytes()
            status, _ = self.post(f"/api/work/{work_id}/draft", {"stage": stage, "body": "changed", "revision": a["revision"]})
            self.assertEqual(status, 409)
            self.assertEqual(path.read_bytes(), raw)

    def test_bad_inputs_cannot_modify_file(self):  # W-0005:AC-3
        work_id, path, data = self.new_draft()
        raw = path.read_bytes()
        invalid = [{"status": "accepted"}, {"approvals": [{"by": "Someone"}]}, {"risk_tier": "T0"},
                   {"owner": "Else"}, {"stage": "../intent"}, {"body": None}, {"body": "x" * (drafts.MAX_TEXT + 1)},
                   {"revision": None}, {"sources": "ticket"}, {"sources": [None]},
                   {"sources": [{"kind": "ticket", "ref": ""}]},
                   {"sources": [{"kind": "ticket", "ref": "x\nstatus: accepted"}]},
                   {"sources": [{"kind": "ticket", "ref": "ok", "approvals": []}]}]
        for patch in invalid:
            with self.subTest(patch=list(patch)):
                status, err = self.post(f"/api/work/{work_id}/draft", {**data, **patch})
                self.assertEqual(status, 400, err)
                self.assertEqual(path.read_bytes(), raw)

    def test_draft_writes_require_same_host_and_headers(self):  # W-0005:AC-3
        work_id, path, data = self.new_draft()
        raw = path.read_bytes()
        route = f"/api/work/{work_id}/draft"
        for headers in [{"Content-Type": "application/json"}, {"Content-Type": "text/plain", "X-SDLC": "1"}]:
            self.assertEqual(self.request("POST", route, data, headers)[0], 403)
        self.assertEqual(self.request("POST", route, data, {"Content-Type": "application/json", "X-SDLC": "1"}, host="evil.example")[0], 403)
        self.assertEqual(path.read_bytes(), raw)

    def test_stale_revision_does_not_overwrite_external_edit(self):  # W-0005:AC-4
        work_id, path, data = self.new_draft()
        path.write_text(path.read_text() + "\nExternal update\n")
        raw = path.read_bytes()
        self.assertEqual(self.post(f"/api/work/{work_id}/draft", data)[0], 409)
        self.assertEqual(path.read_bytes(), raw)

    def test_concurrent_saves_only_one_wins(self):  # W-0005:AC-4
        work_id, path, data = self.new_draft()
        variants = [{**data, "body": data["body"] + suffix} for suffix in ("First", "Second")]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda payload: self.post(f"/api/work/{work_id}/draft", payload), variants))
        self.assertEqual(sorted(status for status, _ in results), [200, 409])
        winner = next(payload for payload, result in zip(variants, results) if result[0] == 200)
        self.assertEqual(artifacts.load(path, self.root).body, winner["body"])

    def test_fake_frontmatter_is_only_body_content(self):  # W-0005:AC-4
        work_id, path, data = self.new_draft()
        data["body"] = '---\nstatus: accepted\napprovals: [Someone]\n---\n<script>alert("x")</script>\n'
        status, saved = self.post(f"/api/work/{work_id}/draft", data)
        self.assertEqual(status, 200, saved)
        art = artifacts.load(path, self.root)
        self.assertEqual((art.status, art.meta["approvals"], art.body), ("draft", [], data["body"]))

    def test_spec_body_is_editable_but_sources_are_not(self):  # W-0005:AC-2 W-0005:AC-3
        work_id, _, _ = self.new_draft()
        self.assertEqual(self.post(f"/api/work/{work_id}/stage", {"stage": "spec"})[0], 201)
        _, work = self.request("GET", f"/api/work/{work_id}")
        a = work["chain"]["spec"]
        data = {"stage": "spec", "body": "## Acceptance criteria\n- AC-1 Fast search\n", "revision": a["revision"]}
        self.assertEqual(self.post(f"/api/work/{work_id}/draft", {**data, "sources": []})[0], 400)
        self.assertEqual(self.post(f"/api/work/{work_id}/draft", data)[0], 200)

    def test_simultaneous_new_work_ids_are_distinct(self):  # W-0005:AC-7
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda n: self.post("/api/work", {"title": f"Parallel {n}", "owner": "Dana", "tier": "T1"}), range(2)))
        self.assertTrue(all(status == 201 for status, _ in results))
        self.assertEqual(len({data["id"] for _, data in results}), 2)
