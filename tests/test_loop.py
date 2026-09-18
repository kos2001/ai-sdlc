"""Play 12 (control band -> incident -> intent) and the event routing that chains plays."""

import datetime as dt
import json

from sdlc import artifacts, bands, cli, events, release, workitems
from tests.helpers import RepoTestCase, git

NOW = dt.datetime(2026, 9, 18, 9, 30, tzinfo=dt.timezone.utc)


class BandsTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.write("bands/checkout.json", json.dumps({
            "service": "checkout", "owner": self.human, "tier": "T2",
            "bands": [{"name": "p95-latency", "metric": "checkout.p95_ms", "max": 800, "for": 3},
                      {"name": "error-rate", "metric": "checkout.error_ratio", "min": 0, "max": 0.01}]}))

    def test_breach_needs_consecutive_samples(self):
        configs = bands.load_bands(self.root)
        breaches, missing = bands.check(configs, {"checkout.p95_ms": [900, 700, 900, 900], "checkout.error_ratio": 0.001})
        self.assertEqual(breaches, [])
        breaches, _ = bands.check(configs, {"checkout.p95_ms": [700, 810, 850, 905], "checkout.error_ratio": 0.001})
        self.assertEqual([b.band for b in breaches], ["p95-latency"])
        self.assertIn("810, 850, 905", breaches[0].describe)

    def test_missing_metric_is_reported_not_silently_passed(self):
        _, missing = bands.check(bands.load_bands(self.root), {"checkout.p95_ms": 100})
        self.assertEqual(missing, ["checkout/error-rate: no data for checkout.error_ratio"])

    def test_breach_writes_valid_incident_and_proposed_intent_once(self):
        breach, = bands.check(bands.load_bands(self.root), {"checkout.p95_ms": [900, 900, 900], "checkout.error_ratio": 0})[0]
        result = bands.open_loop(self.root, breach, NOW)
        self.assertEqual(result["incident"], "incidents/2026/INC-2026-001.md")
        intent = artifacts.load(self.root / result["intent"], self.root)
        self.assertEqual(intent.status, "proposed")  # a human still has to accept it
        self.assertEqual(intent.meta["origin"], "maintain-loop")
        self.assertEqual(intent.meta["risk_tier"], "T2")
        self.assertEqual(intent.meta["sources"][0], {"kind": "incident", "ref": "INC-2026-001"})
        self.assertEqual(cli.validate_all(self.root), [])

        again = bands.open_loop(self.root, breach, NOW)
        self.assertEqual(again["status"], "deduplicated")


class EventsTest(RepoTestCase):
    def test_accepting_artifacts_routes_to_next_play(self):
        intent = workitems.new_work(self.root, "Cache", self.human, year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        self.commit("proposed")
        self.assertEqual(events.derive(self.root, "HEAD~1"), [])  # proposing fires nothing

        base = git(self.root, "rev-parse", "HEAD").strip()
        workitems.approve(intent, self.root, self.human, "product-owner")
        self.commit("accept intent")
        found = events.derive(self.root, base)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["event"], "intent.accepted")
        self.assertEqual(found[0]["skill"], "write-spec")
        self.assertEqual(found[0]["work_id"], "W-0001")

    def test_new_incident_routes_to_closing_the_loop(self):
        self.write("bands/c.json", json.dumps({"service": "c", "owner": self.human,
                                               "bands": [{"name": "b", "metric": "m", "max": 1}]}))
        self.commit("bands")
        breach, = bands.check(bands.load_bands(self.root), {"m": 5})[0]
        bands.open_loop(self.root, breach, NOW)
        self.commit("breach")
        kinds = sorted(e["event"] for e in events.derive(self.root, "HEAD~1"))
        self.assertEqual(kinds, ["incident.opened"])  # the proposed intent waits for a human


class ReleaseRecordTest(RepoTestCase):
    def test_record_lists_work_items_approvers_and_agents(self):
        intent = workitems.new_work(self.root, "Cache", self.human, year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        self.commit("W-0001 accept intent")
        base = git(self.root, "rev-parse", "HEAD").strip()
        self.write("src/cache.py", "x = 1\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "W-0001 add cache\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
        text = release.record(self.root, base, pr="#12", approvers=["Dana Park"], now=NOW)
        self.assertIn("Risk tier:** T1", text)
        self.assertIn("W-0001", text)
        self.assertIn("intent.md accepted by Dana Park", text)
        self.assertIn("Claude <noreply@anthropic.com>", text)
