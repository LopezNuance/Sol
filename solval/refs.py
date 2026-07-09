from __future__ import annotations

import re
from typing import Any, Iterator

HEX64 = r"[a-f0-9]{64}"
OBJECT_RE = re.compile(rf"^object:sha256:({HEX64})$")
DIGEST_RE = re.compile(rf"^digest:sha256:({HEX64})$")
CELL_RE = re.compile(r"^cell:([A-Za-z0-9_:-]+)$")
NAMED_OUTPUT_RE = re.compile(r"^cell:([A-Za-z0-9_:-]+)#([A-Za-z0-9_:-]+)$")
RECORD_RE = re.compile(r"^record:([A-Za-z0-9_:-]+)$")
RUN_RE = re.compile(r"^run:([A-Za-z0-9_:-]+)$")
COMMIT_RE = re.compile(r"^commit:([A-Za-z0-9_:-]+)$")
BRANCH_RE = re.compile(r"^branch:([A-Za-z0-9_:-]+)$")
RENDER_RE = re.compile(r"^render:([A-Za-z0-9_:-]+)$")
SOL_URI_RE = re.compile(r"^sol://([^/]+)/([^/]+)/(.+)$")

REF_PREFIXES = ("object:", "digest:", "cell:", "record:", "run:", "commit:", "branch:", "render:", "sol://")


def iter_strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v)


def iter_refs(obj: Any) -> Iterator[str]:
    for s in iter_strings(obj):
        if s.startswith(REF_PREFIXES):
            yield s


def parse_ref(ref: str) -> tuple[str, str | tuple[str, str]] | None:
    if m := OBJECT_RE.match(ref):
        return ("object", m.group(1))
    if m := DIGEST_RE.match(ref):
        return ("digest", m.group(1))
    if m := NAMED_OUTPUT_RE.match(ref):
        return ("named_output", (m.group(1), m.group(2)))
    if m := CELL_RE.match(ref):
        return ("cell", m.group(1))
    if m := RECORD_RE.match(ref):
        return ("record", m.group(1))
    if m := RUN_RE.match(ref):
        return ("run", m.group(1))
    if m := COMMIT_RE.match(ref):
        return ("commit", m.group(1))
    if m := BRANCH_RE.match(ref):
        return ("branch", m.group(1))
    if m := RENDER_RE.match(ref):
        return ("render", m.group(1))
    if m := SOL_URI_RE.match(ref):
        return ("sol_uri", (m.group(1), m.group(2) + "/" + m.group(3)))
    return None


def bare_id(ref: str, prefix: str) -> str:
    return ref.split(":", 1)[1] if ref.startswith(prefix + ":") else ref
