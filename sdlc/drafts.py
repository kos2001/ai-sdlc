"""Edit draft content without granting access to gate metadata."""

import hashlib
import os
import tempfile
from pathlib import Path

from . import artifacts, frontmatter, workitems

MAX_TEXT = 48 * 1024


def revision(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, root: Path, data: dict) -> dict:
    allowed = {"stage", "body", "sources", "revision"}
    if set(data) - allowed:
        raise ValueError("only stage, body, sources and revision may be edited")
    body = data.get("body")
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_TEXT:
        raise ValueError("body must be text of at most 48 KiB")
    expected = data.get("revision")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("revision is required")
    if not path.is_file():
        raise ValueError("no draft at this stage")
    raw = path.read_bytes()
    art = artifacts.load_text(raw.decode("utf-8"), path.relative_to(root).as_posix(), root)
    if art.load_error or art.status != "draft":
        raise workitems.GateError("only draft artifacts can be edited")
    if revision(raw) != expected:
        raise workitems.GateError("draft changed since it was loaded; reload before saving")
    if "sources" in data:
        sources = data["sources"]
        if art.kind != "intent":
            raise ValueError("sources can only be edited on intent")
        if not isinstance(sources, list) or len(sources) > 50:
            raise ValueError("sources must be a list of at most 50 entries")
        for source in sources:
            if not isinstance(source, dict) or set(source) != {"kind", "ref"}:
                raise ValueError("each source needs only kind and ref")
            if any(not isinstance(source[k], str) or not source[k].strip()
                   or len(source[k]) > 2000 or "\n" in source[k] or "\r" in source[k]
                   for k in ("kind", "ref")):
                raise ValueError("source kind and ref must be nonempty single-line text")
        art.meta["sources"] = sources
    result = frontmatter.render(art.meta, body).encode("utf-8")
    # The subset frontmatter parser must round-trip without altering any metadata.
    check = artifacts.load_text(result.decode("utf-8"), art.rel, root)
    if check.load_error or check.meta != art.meta or check.body != body:
        raise ValueError("content cannot be safely serialized")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".draft-", delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(result)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.chmod(temp_path, path.stat().st_mode & 0o777)
        # Detect outside edits that occurred while preparing the replacement.
        if path.read_bytes() != raw:
            raise workitems.GateError("draft changed while saving; reload before saving")
        os.replace(temp_path, path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    return {"path": art.rel, "status": "draft", "revision": revision(result)}
