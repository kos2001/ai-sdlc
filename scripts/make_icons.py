#!/usr/bin/env python3
"""Generate the ai-sdlc icon set from one geometry.

The mark is the loop: six arcs in the stage colours (Plan → Design → Build → Test → Deploy
→ Maintain, clockwise from the top) around an amber dot — the human gate at the centre.

    python3 scripts/make_icons.py            # SVGs only (stdlib)
    python3 scripts/make_icons.py --png      # also PNG + ICO (needs Pillow)

Writes web/icons/ and copies the files the web app serves into sdlc/webapp/.
"""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "icons"
APP = ROOT / "sdlc" / "webapp"

STAGES = ["#3D5BD9", "#D4502E", "#0B8A6B", "#8A4BD0", "#C9851A", "#C23A7A"]  # plan … maintain
GATE = "#E0A548"
INK = "#10201B"
GAP_DEG = 9          # gap between arcs
R, STROKE, DOT = 19.0, 7.0, 5.2   # in a 64-unit box


def arc_points(i: int, cx: float = 32, cy: float = 32, r: float = R) -> tuple[tuple[float, float], tuple[float, float]]:
    a0 = math.radians(-90 + i * 60 + GAP_DEG / 2)
    a1 = math.radians(-90 + (i + 1) * 60 - GAP_DEG / 2)
    return (cx + r * math.cos(a0), cy + r * math.sin(a0)), (cx + r * math.cos(a1), cy + r * math.sin(a1))


def mark_svg(background: bool) -> str:
    parts = []
    if background:
        parts.append(f'<rect width="64" height="64" rx="14" fill="{INK}"/>')
    for i, colour in enumerate(STAGES):
        (x0, y0), (x1, y1) = arc_points(i)
        parts.append(f'<path d="M{x0:.2f} {y0:.2f}A{R} {R} 0 0 1 {x1:.2f} {y1:.2f}" fill="none" stroke="{colour}" stroke-width="{STROKE}"/>')
    parts.append(f'<circle cx="32" cy="32" r="{DOT}" fill="{GATE}"/>')
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">' + "".join(parts) + "</svg>\n"


def write_svgs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "app-icon.svg").write_text(mark_svg(background=True))
    (OUT / "favicon.svg").write_text(mark_svg(background=False))


def write_pngs() -> None:
    from PIL import Image, ImageDraw

    def render(size: int, background: bool) -> Image.Image:
        s = 16  # supersample, then downscale for smooth edges
        big = size * s
        k = big / 64
        img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if background:
            d.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(14 * k), fill=INK)
        box = [(32 - R) * k, (32 - R) * k, (32 + R) * k, (32 + R) * k]
        pad = STROKE * k / 2  # PIL draws the stroke inside the box; widen it so the centre line sits on R
        box = [box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad]
        for i, colour in enumerate(STAGES):
            d.arc(box, -90 + i * 60 + GAP_DEG / 2, -90 + (i + 1) * 60 - GAP_DEG / 2, fill=colour, width=int(STROKE * k))
        d.ellipse([(32 - DOT) * k, (32 - DOT) * k, (32 + DOT) * k, (32 + DOT) * k], fill=GATE)
        return img.resize((size, size), Image.LANCZOS)

    for size, name in ((512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png")):
        render(size, background=True).save(OUT / name)
    fav = render(64, background=False)
    fav.resize((32, 32), Image.LANCZOS).save(OUT / "favicon-32.png")
    fav.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])


def main(argv: list[str]) -> int:
    write_svgs()
    if "--png" in argv:
        write_pngs()
    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        if (OUT / name).exists():
            shutil.copy2(OUT / name, APP / name)
    print("\n".join(sorted(p.name for p in OUT.iterdir())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
