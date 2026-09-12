"""CLI: run one budgeted step of the exact scan evaluator.

Usage:
  python3 -m qryref.run_evaluator QUERY.json --budget N [--base-dir DIR]
      [--resume RUN.json STATE.json] [--state-out FILE]

Prints the execution record (qry.execution.v0.3) on stdout. When the
step is incomplete, the continuation state is written to --state-out
(if given). Exit codes: 0 complete, 3 incomplete_with_continuation,
1 failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .exact import ExecutionState, execute_step, resume_step


def load_json(path: Path):
    return json.loads(path.read_text())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", type=Path)
    ap.add_argument("--budget", type=int, required=True)
    ap.add_argument("--base-dir", type=Path, default=Path.cwd())
    ap.add_argument("--resume", nargs=2, metavar=("RUN", "STATE"), type=Path,
                    help="previous execution record + continuation state")
    ap.add_argument("--state-out", type=Path, default=None)
    args = ap.parse_args(argv)

    query = load_json(args.query)
    if args.resume:
        run, state_obj = load_json(args.resume[0]), load_json(args.resume[1])
        state = ExecutionState(offsets=state_obj["offsets"])
        result = resume_step(query, args.budget, run["continuation"], state,
                             base_dir=args.base_dir)
    else:
        result = execute_step(query, args.budget, base_dir=args.base_dir)

    print(json.dumps(result.record, indent=2, sort_keys=True))
    if result.state is not None and args.state_out:
        args.state_out.write_text(json.dumps(
            {"offsets": result.state.offsets, "digest": result.state.digest()},
            indent=2, sort_keys=True) + "\n")
    if result.diagnostics:
        for d in result.diagnostics:
            print(f"{d.severity}\t{d.rule_id}\t{d.category}\t{d.target}\t{d.message}",
                  file=sys.stderr)
    if result.status == "complete":
        return 0
    if result.status == "incomplete_with_continuation":
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
