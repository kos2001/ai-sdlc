"""Web app backend: read model over the demo repository, write safety, and the absent approve route."""

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from sdlc import api, demo, server


class ServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = demo.build(Path(cls._tmp.name) / "demo-shop")
        cls.httpd = server.serve(cls.root, port=0)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls._tmp.cleanup()

    def request(self, method, path, body=None, headers=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": host or f"127.0.0.1:{self.port}", **(headers or {})}
        data = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=data, headers=hdrs)
        res = conn.getresponse()
        raw = res.read()
        conn.close()
        ctype = res.getheader("Content-Type") or ""
        return res.status, (json.loads(raw) if ctype.startswith("application/json") else raw.decode())

    def post(self, path, body):
        return self.request("POST", path, body, {"Content-Type": "application/json", "X-SDLC": "1"})


class ReadModelTest(ServerTestCase):
    def test_workspace_identity_is_stable_and_separates_same_named_roots(self):  # W-0005:AC-1
        status, first = self.request("GET", "/api/overview")
        self.assertEqual(status, 200)
        self.assertRegex(first["workspace_id"], r"^[a-f0-9]{64}$")
        self.assertEqual(first["workspace_id"], api.overview(self.root / ".")["workspace_id"])
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / self.root.name
            other.mkdir()
            second = api.overview(other)
        self.assertEqual(first["repo"], second["repo"])
        self.assertNotEqual(first["workspace_id"], second["workspace_id"])
        self.assertNotIn(str(self.root), json.dumps(first))

    def test_overview_counts_the_demo(self):
        status, o = self.request("GET", "/api/overview")
        self.assertEqual(status, 200)
        self.assertEqual(o["by_stage"].get("done"), 1)
        self.assertEqual(o["by_stage"].get("build"), 1)
        waiting = {(w["id"], w["kind"]): (w["have"], w["needed"]) for w in o["waiting"]}
        self.assertEqual(waiting[("W-0002", "spec")], (1, 2))  # T3 spec needs a second approver
        self.assertIn(("W-0003", "intent"), waiting)
        self.assertEqual(o["incidents_open"], 1)
        self.assertEqual(o["gate_wait_hours"]["count"], 7)  # accepted gates in the demo history
        self.assertEqual(o["issues"], 0)

    def test_work_item_audit_trail_comes_from_git(self):
        status, w = self.request("GET", "/api/work/W-0001")
        self.assertEqual(status, 200)
        self.assertEqual(w["stage"], "done")
        self.assertEqual(w["trace"]["covered"], ["AC-1", "AC-2"])
        intent_history = w["chain"]["intent"]["history"]
        self.assertEqual([h["status"] for h in intent_history], ["proposed", "accepted"])
        self.assertIn("Claude", intent_history[0]["author"])
        self.assertIn("Dana Park", intent_history[1]["author"])

    def test_branch_check_runs_the_ci_gates(self):
        status, b = self.request("GET", "/api/branch")
        self.assertEqual(status, 200)
        self.assertEqual((b["branch"], b["base"]), ("feature/w-0004-dark-mode", "main"))
        self.assertEqual(b["risk"]["tier"], "T1")
        self.assertTrue(all(g["ok"] for g in b["gates"]))

    def test_lessons_endpoint_reports_the_loop(self):  # W-0001:AC-5
        status, s = self.request("GET", "/api/lessons")
        self.assertEqual(status, 200)
        self.assertEqual((s["total"], s["open"], s["closed"]), (3, 1, 2))
        self.assertEqual(s["controls_holding"], 2)
        self.assertEqual(s["caught_by_existing_gate"], 1)

    def test_unknown_item_and_static_files(self):
        self.assertEqual(self.request("GET", "/api/work/W-9999")[0], 404)
        status, html = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("ai-sdlc", html)
        self.assertEqual(self.request("GET", "/../../etc/passwd")[0], 404)


class WriteSafetyTest(ServerTestCase):
    def test_there_is_no_approve_endpoint(self):
        for path in ("/api/work/W-0003/approve", "/api/approve"):
            status, _ = self.post(path, {"stage": "intent", "by": "Someone", "role": "po"})
            self.assertEqual(status, 404, path)
        self.assertEqual(api.work_item(self.root, "W-0003")["chain"]["intent"]["status"], "proposed")

    def test_writes_need_json_and_header(self):
        status, body = self.request("POST", "/api/work", {"title": "x", "owner": "y"}, {"Content-Type": "application/json"})
        self.assertEqual(status, 403)
        status, _ = self.request("POST", "/api/work", {"title": "x", "owner": "y"}, {"Content-Type": "text/plain", "X-SDLC": "1"})
        self.assertEqual(status, 403)

    def test_foreign_host_header_is_refused(self):
        self.assertEqual(self.request("GET", "/api/overview", host="evil.example:80")[0], 403)

    def test_new_stage_submit_flow_and_gate_errors(self):
        status, r = self.post("/api/work", {"title": "Export to CSV", "owner": "Dana Park <dana@example.com>", "tier": "T1"})
        self.assertEqual(status, 201)
        work_id = r["id"]
        status, err = self.post(f"/api/work/{work_id}/submit", {"stage": "intent"})
        self.assertEqual(status, 409)  # an empty draft has no sources yet
        self.assertIn("sources", err["error"])
        status, err = self.post(f"/api/work/{work_id}/stage", {"stage": "spec"})
        self.assertEqual(status, 201)  # drafting is allowed; proposing the spec is what the chain blocks
        status, err = self.post(f"/api/work/{work_id}/submit", {"stage": "spec"})
        self.assertEqual(status, 409)
        self.assertIn("intent must be accepted first", err["error"])


if __name__ == "__main__":
    unittest.main()
