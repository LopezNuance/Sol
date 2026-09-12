from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from .canonical import canonical_json
from .validate import validate_case_dir


def is_normative(name: str) -> bool:
    """Spec 36.1/36.2 names 64 normative cases: QGOLD-001..021 and
    QPATH-001..043. QPATH-044/045/046 (gate-18 adversarial additions) and
    the legacy QRY-NNN cases are supplemental (plan finding F-1)."""
    m = re.fullmatch(r"(QGOLD|QPATH)-(\d{3})", name)
    if not m:
        return False
    n = int(m.group(2))
    return (m.group(1) == "QGOLD" and 1 <= n <= 21) \
        or (m.group(1) == "QPATH" and 1 <= n <= 43)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.corpus_dir)
    bases = [b for b in (root / "cases", root / "supplemental") if b.exists()]
    if not bases:
        bases = [root]
    case_dirs = sorted(set().union(
        *[set(b.glob("QRY-*")) | set(b.glob("QGOLD-*")) | set(b.glob("QPATH-*"))
          for b in bases]))
    results = []
    ok = 0
    for c in case_dirs:
        manifest = json.loads((c / "manifest.json").read_text())
        expected = set(manifest.get("expected_diagnostics", []))
        # Clean cases must be reproducible by inference; defective-claim
        # cases are validated as claims only (13.19).
        diags = validate_case_dir(c, check_match=not expected, manifest=manifest)
        got = {d.rule_id for d in diags}
        passed = expected.issubset(got)
        if not expected and got:
            passed = False
        if passed: ok += 1
        results.append({
            "case_id": c.name,
            "kind": "normative" if is_normative(c.name) else "supplemental",
            "passed": passed,
            "expected": sorted(expected),
            "got": sorted(got),
            "diagnostics": [d.to_json() for d in diags],
        })
    by_kind = {}
    for r in results:
        by_kind.setdefault(r["kind"], {"total": 0, "passed": 0})
        by_kind[r["kind"]]["total"] += 1
        by_kind[r["kind"]]["passed"] += 1 if r["passed"] else 0
    report = {
        "format": "solqry-corpus-report/v1",
        "spec": "RFC-SOL-QRY-0001 v0.3.0 design draft, 36",
        "normative": by_kind.get("normative", {"total": 0, "passed": 0}),
        "supplemental": by_kind.get("supplemental", {"total": 0, "passed": 0}),
        "cases": results,
    }
    # Fresh report_digest over the report content (excluding the digest
    # field itself), per the recorded-run pattern (37.5 determinism).
    content = canonical_json(report)
    report["report_digest"] = "sha256:" + hashlib.sha256(
        content.encode("utf-8")).hexdigest()
    report_path = root / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report_path.chmod(0o644)
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for r in results:
            status = "ok" if r["passed"] else "FAIL"
            print(f"{status}\t{r['case_id']}\t{r['kind']}\t"
                  f"expected={','.join(r['expected']) or '-'}\t"
                  f"got={','.join(r['got']) or '-'}")
        for kind in ("normative", "supplemental"):
            v = by_kind.get(kind, {"total": 0, "passed": 0})
            print(f"{v['passed']}/{v['total']} {kind} cases satisfied expected diagnostics")
        print(f"{ok}/{len(results)} cases satisfied expected diagnostics; "
              f"report {report_path} report_digest {report['report_digest']}")
    return 0 if ok == len(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
