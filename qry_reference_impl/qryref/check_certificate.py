"""Check a committed rewrite certificate (25.6).

Usage:
  python3 -m qryref.check_certificate [CERT.json ...]

Re-runs the rule's property test over the same seeded instances, verifies
every transcript entry, and recomputes the transcript digest. A verified
certificate is a *checked certificate*: it MAY support `proven` assurance
for the rule (25.6, Q5). With no arguments, checks every certificate under
certificates/rewrites/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .canonical import canonical_json
from .property_tests import verify_certificate

ROOT = Path(__file__).resolve().parents[1]


def check_file(p: Path) -> tuple[bool, str]:
    obj = json.loads(p.read_text())
    if obj.get("schema_version") == "solqry.rewrite-certificate/v1":
        ok, detail = verify_certificate(obj)
        print(f"{'verified' if ok else 'FAILED'}\t{p.name}\t{obj.get('rule_slug')}"
              f"\tcases={obj.get('cases')}\ttranscript_digest={obj.get('transcript_digest')}\t{detail}")
        return ok, detail
    if obj.get("format") == "solqry-covering-proof/v1":
        from .make_rewrites_corpus import (covering_proof, gold_covering_proof,
                                          heuristic_covering_proof)
        # Each committed covering proof (lossy QPATH-034, exact QGOLD-005,
        # heuristic QPATH-033) verifies against its own builder.
        ok = any(
            p.read_text() == json.dumps(builder(), indent=2, sort_keys=True) + "\n"
            for builder in (covering_proof, gold_covering_proof,
                            heuristic_covering_proof))
        print(f"{'verified' if ok else 'FAILED'}\t{p.name}\tcovering-proof"
              f"\tsummary_fields={obj.get('summary_fields')}\t"
              + ("content matches the committed builder" if ok else "content drift"))
        return ok, "covering proof"
    if obj.get("format") == "solqry-rewrite-registry/v1":
        content = {k: v for k, v in obj.items() if k != "report_digest"}
        import hashlib
        recomputed = "sha256:" + hashlib.sha256(
            canonical_json(content).encode("utf-8")).hexdigest()
        ok = recomputed == obj.get("report_digest")
        print(f"{'verified' if ok else 'FAILED'}\t{p.name}\tregistry"
              f"\trules={len(obj.get('rules', {}))}\treport_digest={obj.get('report_digest')}\t"
              + ("digest recomputes" if ok else "report digest mismatch"))
        return ok, "registry report"
    return False, f"unknown artifact format in {p.name}"


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        paths = [Path(a) for a in argv]
    else:
        paths = sorted((ROOT / "certificates" / "rewrites").glob("*.json"))
    rc = 0
    for p in paths:
        ok, _ = check_file(p)
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
