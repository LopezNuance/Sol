from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .validate import validate_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a Sol pathology/golden corpus")
    ap.add_argument("corpus", nargs="?", default="corpus")
    ap.add_argument("--strict-extra", action="store_true", help="fail when diagnostics beyond expected appear")
    args = ap.parse_args()
    root = Path(args.corpus)
    failures = 0
    total = 0
    for case in sorted(p for p in root.iterdir() if p.is_dir()):
        art = case / "artifact.sol.d"
        if not art.exists():
            continue
        total += 1
        diags = validate_path(art)
        rules = [d.rule_id for d in diags]
        exp_path = art / "expected_diagnostics.json"
        expected = []
        if exp_path.exists():
            expected = json.loads(exp_path.read_text()).get("expected_rule_ids", [])
        missing = [r for r in expected if r not in rules]
        extra = [r for r in rules if r not in expected]
        ok = not missing and (not args.strict_extra or not extra)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {case.name}: expected={expected} got={rules}")
        if missing:
            print(f"  missing: {missing}")
        if extra:
            print(f"  extra: {extra}")
        if not ok:
            failures += 1
            (case / "actual_diagnostics.json").write_text(json.dumps([asdict(d) for d in diags], indent=2, sort_keys=True), encoding="utf-8")
    print(f"\n{total - failures}/{total} cases satisfied expected diagnostics")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
