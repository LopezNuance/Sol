#!/usr/bin/env python3
"""Container benchmark for RFC-SOL-0001 section 59, Q1 (physical container).

Packages an exploded artifact (artifact.sol.d layout) into candidate container
formats and measures the bounded-read requirements REQ-014.1..REQ-014.5:

  REQ-014.1  bounded manifest read
  REQ-014.2  structural index read
  REQ-014.3  random object access
  REQ-014.4  integrity verification
  REQ-014.5  progressive loading (levels 0-4, RFC section 11)

Candidates:
  exploded-dir  plain directory tree (current non-normative debug representation)
  zip-flat      single-file ZIP, entries mirror the exploded layout, STORED
  tar           single-file tar (sequential; included as contrast)

Measurement: bytes read from the container via a counting wrapper, file opens,
wall time (secondary). Each operation opens the container fresh, as a real
reader would. The primary metric is amplification: bytes a reader must touch
for a bounded operation, relative to total artifact bytes.

Standard library only. Deterministic (fixed synthetic seed, sorted walks).
"""

import hashlib
import json
import os
import random
import sys
import tarfile
import tempfile
import time
import zipfile

STORE = "objects/sha256"
LEVEL_FILES = {
    # RFC section 11 levels, mapped to exploded-representation file sets.
    # Level 3 (full sources) is byte-identical to level 2 in the exploded
    # representation because cell sources live inside the cell JSON files;
    # the report records that equality explicitly.
    "level_0": ["manifest.json"],
    "level_1": ["manifest.json", "execution_structure.json"],
    "level_2": [
        "manifest.json",
        "execution_structure.json",
        "cells/", "records/", "actors/", "runs/", "commits/",
        "renders/machine_summary.json",
    ],
    "level_3": None,  # filled at runtime: level_2 set (sources are inline)
    "level_4": None,  # filled at runtime: level_2 set + objects/
}


class CountingFile:
    """File object that counts bytes actually read."""

    def __init__(self, path):
        self._f = open(path, "rb")
        self.bytes_read = 0
        self.opens = 1

    def read(self, *a):
        data = self._f.read(*a)
        self.bytes_read += len(data)
        return data

    def readinto(self, b):
        n = self._f.readinto(b)
        self.bytes_read += n
        return n

    def seek(self, *a):
        return self._f.seek(*a)

    def tell(self):
        return self._f.tell()

    def close(self):
        self._f.close()

    def __getattr__(self, item):
        # Delegate everything else (seekable, readable, ...) to the wrapped file.
        return getattr(self._f, item)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def measure(fn):
    """Run fn(counter_factory) and return (result, bytes, opens, wall_ms)."""
    t0 = time.perf_counter()
    result = fn()
    wall_ms = (time.perf_counter() - t0) * 1000.0
    return result, wall_ms


def list_exploded(root):
    """Sorted relative paths of all files under root."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return out


def object_sizes(root):
    """{relpath: (size, sha256)} for objects under objects/sha256/."""
    out = {}
    base = os.path.join(root, STORE)
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        full = os.path.join(base, name)
        if not os.path.isfile(full):
            continue
        h = hashlib.sha256()
        with open(full, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        out[os.path.join(STORE, name)] = (os.path.getsize(full), h.hexdigest())
    return out


# --- candidates -------------------------------------------------------------

def op_dir(root, relpath):
    """Read one file from the exploded directory. Returns (data, bytes, opens)."""
    with open(os.path.join(root, relpath), "rb") as f:
        data = f.read()
    return data, len(data), 1


def op_zip(container, relpath):
    """Read one entry from a fresh ZipFile over a counting wrapper."""
    cf = CountingFile(container)
    with cf, zipfile.ZipFile(cf) as zf:
        data = zf.read(relpath)
    return data, cf.bytes_read, cf.opens


def op_tar(container, relpath):
    """Read one member from a fresh seekable tarfile over a counting wrapper.

    mode='r' (seekable) builds the member index by scanning from the start;
    that scan is the honest random-access cost of tar and is counted.
    """
    cf = CountingFile(container)
    with cf, tarfile.open(fileobj=cf, mode="r") as tf:
        member = tf.getmember(relpath)
        f = tf.extractfile(member)
        data = f.read() if f is not None else None
    if data is None:
        raise FileNotFoundError(relpath)
    return data, cf.bytes_read, cf.opens


def read_set_dir(root, relpaths):
    total, opens = 0, 0
    for p in relpaths:
        _, b, o = op_dir(root, p)
        total += b
        opens += o
    return total, opens


def read_set_zip(container, relpaths):
    """Read a set of entries through ONE open container (shared central dir)."""
    cf = CountingFile(container)
    with cf, zipfile.ZipFile(cf) as zf:
        for p in relpaths:
            zf.read(p)
    return cf.bytes_read, cf.opens


def read_set_tar(container, relpaths):
    cf = CountingFile(container)
    with cf, tarfile.open(fileobj=cf, mode="r") as tf:
        for p in relpaths:
            f = tf.extractfile(tf.getmember(p))
            if f is not None:
                f.read()
    return cf.bytes_read, cf.opens


def pack_zip(exploded_root, out_path):
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
        for rel in list_exploded(exploded_root):
            zf.write(os.path.join(exploded_root, rel), arcname=rel)


def pack_tar(exploded_root, out_path):
    with tarfile.open(out_path, "w") as tf:
        for rel in list_exploded(exploded_root):
            tf.add(os.path.join(exploded_root, rel), arcname=rel)


# --- benchmark driver -------------------------------------------------------

def run_case(name, exploded_root, outdir, artifact_bytes):
    relpaths = list_exploded(exploded_root)
    objs = object_sizes(exploded_root)
    if not objs:
        raise SystemExit(f"{name}: no objects found under {STORE}/")
    largest = max(objs, key=lambda k: objs[k][0])
    smallest = min(objs, key=lambda k: objs[k][0])

    level_sets = {
        "level_0": LEVEL_FILES["level_0"],
        "level_1": LEVEL_FILES["level_1"],
        "level_2": [p for p in relpaths
                    if p in ("manifest.json", "execution_structure.json")
                    or p.startswith("cells/") or p.startswith("records/")
                    or p.startswith("actors/") or p.startswith("runs/")
                    or p.startswith("commits/")
                    or p == "renders/machine_summary.json"],
    }
    level_sets["level_3"] = level_sets["level_2"]
    level_sets["level_4"] = level_sets["level_2"] + sorted(
        p for p in relpaths if p.startswith(STORE + "/"))

    zip_path = os.path.join(outdir, f"{name}.solnb.zip")
    tar_path = os.path.join(outdir, f"{name}.solnb.tar")
    pack_zip(exploded_root, zip_path)
    pack_tar(exploded_root, tar_path)

    candidates = {
        "exploded-dir": {
            "op": lambda p: op_dir(exploded_root, p),
            "set": lambda ps: read_set_dir(exploded_root, ps),
        },
        "zip-flat": {
            "op": lambda p: op_zip(zip_path, p),
            "set": lambda ps: read_set_zip(zip_path, ps),
        },
        "tar": {
            "op": lambda p: op_tar(tar_path, p),
            "set": lambda ps: read_set_tar(tar_path, ps),
        },
    }

    results = {}
    for cand, impl in candidates.items():
        entry = {}

        # REQ-014.1 bounded manifest read
        data, b, o = impl["op"]("manifest.json")
        entry["REQ-014.1_manifest"] = {
            "bytes_read": b, "opens": o,
            "amplification": round(b / artifact_bytes, 4),
            "manifest_bytes": len(data),
        }

        # REQ-014.2 structural index read (manifest + execution skeleton)
        b, o = impl["set"](["manifest.json", "execution_structure.json"])
        entry["REQ-014.2_index"] = {
            "bytes_read": b, "opens": o,
            "amplification": round(b / artifact_bytes, 4),
        }

        # REQ-014.3 random object access (worst + best case)
        for label, obj in (("worst_case", largest), ("best_case", smallest)):
            data, b, o = impl["op"](obj)
            entry[f"REQ-014.3_object_{label}"] = {
                "object": obj, "object_bytes": objs[obj][0],
                "bytes_read": b, "opens": o,
                "amplification": round(b / artifact_bytes, 4),
            }

        # REQ-014.4 integrity verification of the largest object
        data, b, o = impl["op"](largest)
        digest = hashlib.sha256(data).hexdigest()
        entry["REQ-014.4_verify_largest"] = {
            "object": largest, "bytes_read": b, "opens": o,
            "amplification": round(b / artifact_bytes, 4),
            "sha256_match": digest == objs[largest][1],
        }

        # REQ-014.5 progressive loading, cumulative per level
        levels = {}
        for lvl in ("level_0", "level_1", "level_2", "level_3", "level_4"):
            b, o = impl["set"](level_sets[lvl])
            levels[lvl] = {
                "cumulative_bytes": b, "opens": o,
                "amplification": round(b / artifact_bytes, 4),
            }
        entry["REQ-014.5_progressive"] = levels

        results[cand] = entry

    return {
        "artifact_bytes": artifact_bytes,
        "file_count": len(relpaths),
        "object_count": len(objs),
        "largest_object": {"path": largest, "bytes": objs[largest][0]},
        "smallest_object": {"path": smallest, "bytes": objs[smallest][0]},
        "level_note": ("level_3 equals level_2 byte-for-byte in the exploded "
                       "representation: cell sources are inline in cell JSON"),
        "candidates": results,
    }


def main():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    corpus = os.path.join(repo, "sol_validator", "corpus")
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
    os.makedirs(outdir, exist_ok=True)

    import shutil

    gold1 = os.path.join(corpus, "GOLD-01", "artifact.sol.d")

    def make_synthetic():
        # Synthetic scale variant: GOLD-01 plus one 16 MiB object with a
        # deterministic payload, so the random-access contrast is visible.
        # The object is NOT part of the corpus and is labeled synthetic in
        # the report.
        tmp = tempfile.mkdtemp(prefix="solbench-")
        root = os.path.join(tmp, "artifact.sol.d")
        shutil.copytree(gold1, root)
        payload = random.Random(20260907).randbytes(16 * 1024 * 1024)
        digest = hashlib.sha256(payload).hexdigest()
        with open(os.path.join(root, STORE, digest), "wb") as f:
            f.write(payload)
        return root, tmp

    cases = [("GOLD-01", gold1, False, None)]
    synth_root, synth_tmp = make_synthetic()
    cases.append(("GOLD-01+16MiB-synthetic", synth_root, True, synth_tmp))

    report = {
        "format": "sol-container-benchmark/v1",
        "purpose": ("RFC-SOL-0001 section 59 Q1: benchmark candidate physical "
                    "containers against REQ-014.1..REQ-014.5"),
        "candidates": {
            "exploded-dir": "plain directory tree (non-normative debug representation)",
            "zip-flat": "single-file ZIP, STORED entries, layout mirrors artifact.sol.d",
            "tar": "single-file tar (sequential; contrast candidate)",
        },
        "measurement": ("bytes read from the container via counting wrappers; "
                        "each operation opens the container fresh; "
                        "amplification = bytes_read / artifact_bytes"),
        "inputs": [],
        "results": {},
    }

    for name, root, synthetic, cleanup_tmp in cases:
        total = 0
        for rel in list_exploded(root):
            total += os.path.getsize(os.path.join(root, rel))
        report["inputs"].append({
            "name": name,
            "artifact": os.path.relpath(root, repo),
            "synthetic": synthetic,
            "note": ("GOLD-01 plus a deterministic 16 MiB object "
                     "(seed 20260907); not part of the corpus"
                     if synthetic else "real corpus artifact"),
            "total_bytes": total,
        })
        report["results"][name] = run_case(name, root, outdir, total)
        if cleanup_tmp is not None:
            shutil.rmtree(cleanup_tmp, ignore_errors=True)

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Human-readable summary.
    print(f"report: {report_path}\n")
    for name, res in report["results"].items():
        print(f"== {name} ({res['artifact_bytes']} bytes, "
              f"{res['object_count']} objects, "
              f"largest {res['largest_object']['bytes']} B) ==")
        for cand, entry in res["candidates"].items():
            m = entry["REQ-014.1_manifest"]
            i = entry["REQ-014.2_index"]
            w = entry["REQ-014.3_object_worst_case"]
            v = entry["REQ-014.4_verify_largest"]
            l0 = entry["REQ-014.5_progressive"]["level_0"]
            l4 = entry["REQ-014.5_progressive"]["level_4"]
            print(f"  {cand:<13} manifest x{m['amplification']:<8} "
                  f"index x{i['amplification']:<8} "
                  f"obj-worst x{w['amplification']:<8} "
                  f"verify-ok={v['sha256_match']} "
                  f"L0 x{l0['amplification']:<8} L4 x{l4['amplification']}")
        print()


if __name__ == "__main__":
    sys.exit(main())
