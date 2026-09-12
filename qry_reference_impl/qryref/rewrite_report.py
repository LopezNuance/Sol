"""Generate the committed rewrite-kernel artifacts (gates 5 and 18).

Writes, deterministically, under certificates/rewrites/:

  <rule-slug>.json           property-test certificate (transcript + digest)
  disclosure-proof.json      the accepted disclosure proof for the
                             policy-boundary rule (QGOLD-021)
  covering-proof.json        the committed covering proof referenced by
                             the machine-summary substitution cases
                             (QPATH-034; QV8-03/QV8-04 checks)
  covering-proof-gold.json   the committed field-complete exact covering
                             proof (QGOLD-005; the substitution applies)
  covering-proof-heuristic.json
                             a field-complete covering proof for a summary
                             produced heuristically (QPATH-033; QV8-02)
  registry_report.json       condition-5 evidence (registered kernel with
                             proof metadata) + report_digest

Re-running over the same repository state produces byte-identical files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .canonical import canonical_json
from .make_rewrites_corpus import (covering_proof, gold_covering_proof,
                                  heuristic_covering_proof)
from .property_tests import TESTS, build_certificate
from .rewrites import registry_report

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "certificates" / "rewrites"


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    path.chmod(0o644)


def main() -> int:
    if OUT.exists():
        import shutil
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for slug in TESTS:
        _write(OUT / f"{slug}.json", build_certificate(slug))
    _write(OUT / "covering-proof.json", covering_proof())
    _write(OUT / "covering-proof-gold.json", gold_covering_proof())
    _write(OUT / "covering-proof-heuristic.json", heuristic_covering_proof())

    report = registry_report()
    content = canonical_json(report)
    report["report_digest"] = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
    _write(OUT / "registry_report.json", report)

    print(f"certificates: {', '.join(TESTS)}; registry report_digest {report['report_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
