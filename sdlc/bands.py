"""Play 12: control bands on production metrics; a breach writes the next intent.md.

bands/<service>.json:

    {"service": "checkout", "owner": "Dana Park <dana@example.com>", "tier": "T2",
     "bands": [{"name": "p95-latency", "metric": "checkout.p95_ms", "max": 800, "for": 3}]}

Metrics input (latest sample last; a bare number is a one-sample series):

    {"checkout.p95_ms": [640, 810, 850, 905]}

A band is breached when the last `for` samples (default 1) are all outside [min, max].
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import artifacts, frontmatter, workitems

BANDS_DIR = "bands"


@dataclass
class Breach:
    service: str
    band: str
    metric: str
    low: float | None
    high: float | None
    window: int
    samples: list[float]
    owner: str
    tier: str

    @property
    def describe(self) -> str:
        limits = " and ".join(x for x in (
            f">= {self.low:g}" if self.low is not None else "",
            f"<= {self.high:g}" if self.high is not None else "") if x)
        return (f"`{self.metric}` outside band ({limits}) for the last {self.window} sample(s): "
                + ", ".join(f"{v:g}" for v in self.samples[-self.window:]))


def load_bands(root: Path) -> list[dict]:
    configs = []
    for path in sorted((root / BANDS_DIR).glob("*.json")):
        config = json.loads(path.read_text(encoding="utf-8"))
        for key in ("service", "owner", "bands"):
            if key not in config:
                raise ValueError(f"{path.name}: missing '{key}'")
        configs.append(config)
    return configs


def _series(value) -> list[float]:
    return [float(v) for v in (value if isinstance(value, list) else [value])]


def check(configs: list[dict], metrics: dict) -> tuple[list[Breach], list[str]]:
    """(breaches, metrics named by a band but absent from the input)."""
    breaches, missing = [], []
    for config in configs:
        for band in config["bands"]:
            if band["metric"] not in metrics:
                missing.append(f"{config['service']}/{band['name']}: no data for {band['metric']}")
                continue
            series = _series(metrics[band["metric"]])
            window = int(band.get("for", 1))
            low, high = band.get("min"), band.get("max")
            recent = series[-window:]
            if len(recent) < window:
                continue
            outside = [(low is not None and v < low) or (high is not None and v > high) for v in recent]
            if all(outside):
                breaches.append(Breach(config["service"], band["name"], band["metric"], low, high, window,
                                       series, config["owner"], config.get("tier", "T1")))
    return breaches, missing


def _open_incident_for(root: Path, breach: Breach) -> Path | None:
    for path in sorted((root / artifacts.INCIDENT_DIR).glob("*/INC-*.md")):
        try:
            meta, _ = frontmatter.load(path.read_text(encoding="utf-8"))
        except frontmatter.FrontmatterError:
            continue
        if meta.get("service") == breach.service and meta.get("band") == breach.band and meta.get("status") != "closed":
            return path
    return None


def _next_incident_id(root: Path, year: int) -> str:
    highest = 0
    for path in (root / artifacts.INCIDENT_DIR / str(year)).glob(f"INC-{year}-*.md"):
        m = re.match(rf"INC-{year}-(\d+)$", path.stem)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"INC-{year}-{highest + 1:03d}"


def open_loop(root: Path, breach: Breach, now: dt.datetime | None = None) -> dict:
    """Write an incident record and a proposed follow-up intent, unless one is already open."""
    existing = _open_incident_for(root, breach)
    if existing:
        return {"status": "deduplicated", "incident": existing.relative_to(root).as_posix()}
    now = now or dt.datetime.now(dt.timezone.utc)
    incident_id = _next_incident_id(root, now.year)
    incident_rel = f"{artifacts.INCIDENT_DIR}/{now.year}/{incident_id}.md"

    intent = workitems.new_work(root, f"{breach.service} {breach.band} breach", breach.owner, breach.tier,
                                origin="maintain-loop", year=now.year)
    art = artifacts.load(intent, root)
    art.meta["sources"] = [{"kind": "incident", "ref": incident_id},
                           {"kind": "metric", "ref": f"{breach.metric} window={breach.window}"}]
    art.body = art.body.replace("## Problem\n", f"## Problem\n{breach.describe} (see {incident_id}).\n", 1)
    target = " and ".join(x for x in (
        f">= {breach.low:g}" if breach.low is not None else "",
        f"<= {breach.high:g}" if breach.high is not None else "") if x)
    art.body = art.body.replace("## Desired outcome\n",
                                f"## Desired outcome\n`{breach.metric}` back within band ({target}) and a guard against recurrence.\n", 1)
    workitems._save(art)
    workitems.submit(intent, root)

    incident_path = root / incident_rel
    incident_path.parent.mkdir(parents=True, exist_ok=True)
    incident_path.write_text(workitems.render_template(root, "incident.md", {
        "id": incident_id, "service": breach.service, "band": breach.band,
        "detected_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "followup_intent": intent.relative_to(root).as_posix(),
        "signal": breach.describe,
    }), encoding="utf-8")
    return {"status": "opened", "incident": incident_rel, "intent": intent.relative_to(root).as_posix()}
