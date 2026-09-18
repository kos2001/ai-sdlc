"""Minimal YAML-subset frontmatter parser/writer (stdlib only).

Supported subset — enough for SDLC artifacts, deliberately nothing more:

    key: scalar            # strings; surrounding quotes are stripped
    key: [a, b]            # inline list of scalars ([] = empty list)
    key:                   # block list; items are scalars or flat mappings
      - scalar
      - k: v
        k2: v2

Anything outside this subset raises FrontmatterError instead of guessing.
"""

from __future__ import annotations

import re

FENCE = "---"


class FrontmatterError(ValueError):
    pass


def split(text: str) -> tuple[str, str]:
    """Return (frontmatter_source, body). Raises if the fence is missing."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FENCE:
        raise FrontmatterError("missing opening '---' frontmatter fence on line 1")
    for i in range(1, len(lines)):
        if lines[i].strip() == FENCE:
            return "".join(lines[1:i]), "".join(lines[i + 1 :])
    raise FrontmatterError("missing closing '---' frontmatter fence")


def _strip_comment(line: str) -> str:
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i].rstrip()
    return line.rstrip()


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _inline_list(raw: str) -> list[str]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_scalar(part) for part in inner.split(",")]


def _value(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return _inline_list(raw)
    return _scalar(raw)


_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?$")


def parse(source: str) -> dict:
    data: dict = {}
    current_key: str | None = None  # key that owns an open block list
    current_item: dict | None = None
    item_indent = 0
    for lineno, original in enumerate(source.splitlines(), start=1):
        line = _strip_comment(original)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            m = _KEY.match(stripped)
            if not m:
                raise FrontmatterError(f"line {lineno}: expected 'key: value', got {original!r}")
            key, raw = m.group(1), m.group(2)
            current_item = None
            if raw is None or raw == "":
                data[key] = []
                current_key = key
            else:
                data[key] = _value(raw)
                current_key = None
            continue

        if current_key is None:
            raise FrontmatterError(f"line {lineno}: unexpected indentation")

        if stripped.startswith("- ") or stripped == "-":
            entry = stripped[1:].strip()
            m = _KEY.match(entry)
            if m and m.group(2) is not None:
                current_item = {m.group(1): _value(m.group(2))}
                item_indent = indent + 2
                data[current_key].append(current_item)
            else:
                current_item = None
                data[current_key].append(_scalar(entry))
            continue

        m = _KEY.match(stripped)
        if current_item is not None and m and indent >= item_indent:
            current_item[m.group(1)] = _value(m.group(2) or "")
            continue
        raise FrontmatterError(f"line {lineno}: cannot parse {original!r}")
    return data


def load(text: str) -> tuple[dict, str]:
    source, body = split(text)
    return parse(source), body


def _dump_scalar(value) -> str:
    s = "" if value is None else str(value)
    if s == "" or s[0] in "[]{}#&*!|>'\"%@`-" or ": " in s or " #" in s or s != s.strip():
        return '"' + s.replace('"', "'") + '"'
    return s


def dump(data: dict) -> str:
    out = []
    for key, value in data.items():
        if isinstance(value, list):
            if not value:
                out.append(f"{key}: []")
                continue
            if all(not isinstance(v, dict) for v in value):
                out.append(f"{key}: [{', '.join(_dump_scalar(v) for v in value)}]")
                continue
            out.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        prefix = "  - " if first else "    "
                        out.append(f"{prefix}{k}: {_dump_scalar(v)}")
                        first = False
                else:
                    out.append(f"  - {_dump_scalar(item)}")
        else:
            out.append(f"{key}: {_dump_scalar(value)}")
    return "\n".join(out) + "\n"


def render(data: dict, body: str) -> str:
    return f"{FENCE}\n{dump(data)}{FENCE}\n{body}"
