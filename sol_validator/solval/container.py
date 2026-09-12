"""Physical .solnb container (decision Q1, 2026-09-07).

A single-file ZIP archive with STORED (uncompressed) entries whose internal
layout is identical to the exploded artifact.sol.d/ representation
(RFC section 56). Proposed media type: application/vnd.sol.notebook
(subject to namespace review; see the RFC Project Name section).

Container-level requirements (RFC section 14):
  REQ-014.1 bounded manifest read     -- central-directory lookup; the
                                         manifest member is read without
                                         touching object payloads.
  REQ-014.2 structural index read     -- execution_structure.json and the
                                         Level 1/2 indexes are read without
                                         object payloads.
  REQ-014.3 random object access      -- objects/sha256/<digest> is a
                                         standalone member; no unpacking.
  REQ-014.4 integrity verification    -- every stored object's bytes must
                                         hash to its member name; manifest
                                         and index must parse.
  REQ-014.5 progressive loading       -- members are read individually; a
                                         range-capable remote client fetches
                                         only the members it needs.

STORED entries: objects are already compressed per section 43 (registered
codecs), so container-level compression is redundant; STORED keeps
byte-exact integrity verification and random access simple (Q1 rationale).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

MEDIA_TYPE = "application/vnd.sol.notebook"
EXTENSION = ".solnb"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)  # deterministic archives
OBJECT_PREFIX = "objects/sha256/"


def pack(exploded: str | Path, out: str | Path) -> Path:
    """Pack an exploded artifact.sol.d/ tree into a .solnb container.

    Deterministic: sorted member order, STORED entries, fixed timestamps.
    """
    exploded = Path(exploded).resolve()
    out = Path(out)
    if out.exists():
        out.unlink()
    entries = sorted(p for p in exploded.rglob("*") if p.is_file())
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in entries:
            name = p.relative_to(exploded).as_posix()
            zi = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, p.read_bytes())
    return out


def unpack(solnb: str | Path, out: str | Path) -> Path:
    """Unpack a .solnb container into an exploded artifact.sol.d/ tree."""
    solnb = Path(solnb)
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    with zipfile.ZipFile(solnb) as zf:
        zf.extractall(out)
    return out


@contextmanager
def unpack_to_temp(solnb: str | Path) -> Iterator[Path]:
    d = Path(tempfile.mkdtemp(prefix="solnb-"))
    try:
        yield unpack(solnb, d / "artifact.sol.d")
    finally:
        shutil.rmtree(d, ignore_errors=True)


class _CountingFile:
    """File wrapper that counts bytes actually read (benchmark method)."""

    def __init__(self, path: Path):
        self._f = open(path, "rb")
        self.bytes_read = 0
        self.opens = 1

    def read(self, *a):
        data = self._f.read(*a)
        self.bytes_read += len(data)
        return data

    def seek(self, *a):
        return self._f.seek(*a)

    def tell(self):
        return self._f.tell()

    def close(self):
        self._f.close()

    def seekable(self) -> bool:
        return self._f.seekable()

    def readable(self) -> bool:
        return self._f.readable()

    def writable(self) -> bool:
        return self._f.writable()

    @property
    def closed(self) -> bool:
        return self._f.closed


class SolnbContainer:
    """Bounded-read reader over a .solnb container (REQ-014.x)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._zf = zipfile.ZipFile(self.path)

    # -- structural access -------------------------------------------------
    def names(self) -> list[str]:
        return sorted(self._zf.namelist())

    def read(self, name: str) -> bytes:
        return self._zf.read(name)

    def manifest(self) -> dict:
        """REQ-014.1: bounded manifest read (no object payloads)."""
        return json.loads(self.read("manifest.json"))

    def execution_structure(self) -> dict:
        """REQ-014.2: structural index read (no object payloads)."""
        return json.loads(self.read("execution_structure.json"))

    def object(self, digest: str) -> bytes:
        """REQ-014.3: random object access without unpacking."""
        return self.read(f"{OBJECT_PREFIX}{digest}")

    def object_exists(self, digest: str) -> bool:
        return f"{OBJECT_PREFIX}{digest}" in self._zf.namelist()

    def object_digests(self) -> list[str]:
        return [n.rsplit("/", 1)[-1] for n in self.names() if n.startswith(OBJECT_PREFIX)]

    # -- integrity (REQ-014.4) ----------------------------------------------
    def verify_objects(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for digest in self.object_digests():
            data = self.object(digest)
            out[digest] = hashlib.sha256(data).hexdigest() == digest
        return out

    def verify(self) -> list[str]:
        """Return a list of integrity problems (empty = verified)."""
        problems: list[str] = []
        names = self.names()
        if "manifest.json" not in names:
            problems.append("manifest.json missing")
        else:
            try:
                json.loads(self.read("manifest.json"))
            except Exception as e:
                problems.append(f"manifest.json unreadable: {e}")
        if "execution_structure.json" not in names:
            problems.append("execution_structure.json missing")
        for digest, ok in self.verify_objects().items():
            if not ok:
                problems.append(f"object {digest} bytes do not match digest")
        return problems

    # -- bounded-read measurement (REQ-014.1/014.2/014.5) --------------------
    def bounded_read_bytes(self, member_names: list[str]) -> dict:
        """Open the container fresh and read only the given members.

        Returns bytes actually read from the file (central directory plus
        the requested members), for REQ-014.1/014.2/014.5 evidence.
        """
        cf = _CountingFile(self.path)
        try:
            zf = zipfile.ZipFile(cf)
            total = 0
            for name in member_names:
                total += len(zf.read(name))
            return {
                "bytes_read": cf.bytes_read,
                "member_bytes": total,
                "container_bytes": self.path.stat().st_size,
                "opens": cf.opens,
            }
        finally:
            cf.close()

    def close(self) -> None:
        self._zf.close()

    def __enter__(self) -> SolnbContainer:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def is_solnb(path: str | Path) -> bool:
    p = Path(path)
    if not p.is_file():
        return False
    if p.suffix == EXTENSION:
        return True
    with open(p, "rb") as f:
        return f.read(4) == b"PK\x03\x04"
