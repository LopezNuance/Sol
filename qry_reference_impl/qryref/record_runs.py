"""Recorded exact-evaluator runs (gate 8 evidence) and the end-to-end
bounded-query demo (gate 12 evidence).

Regenerates, from the committed repository artifacts:

  evaluator_runs/
    corpus/<CASE>/{query,run,rows}.json          31 cases (prototype instance)
    sol_validator_corpus/<CASE>/{query,run,rows}.json   37 cases (current instance)
    demo_budget_degradation/{query,step_N,state_N,rows_N,report}.json
    report.json                                   fresh report_digest

Every run is reproducible: the inputs (query + pinned artifact digest)
are committed, and re-running this module over the committed artifacts
produces byte-identical outputs (37.5 determinism).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .canonical import canonical_json, query_digest
from .exact import (ExecutionState, artifact_tree_digest, execute_step,
                     resume_step, scan_artifact_relation)
from .schemas import validate_json_schema

ROOT = Path(__file__).resolve().parents[1]          # qry_reference_impl/
REPO = ROOT.parent                                   # repository root
RUNS = ROOT / "evaluator_runs"

# Census query: exact scan of every record of the artifact, sorted by
# record_id. This is the recorded run for gate condition 8.
CENSUS_SCHEMA = [
    {"name": "record_id", "type": "string", "nullable": True},
    {"name": "record_type", "type": "string", "nullable": True},
    {"name": "lifecycle", "type": "string", "nullable": True, "path": "status.lifecycle"},
    {"name": "staleness", "type": "string", "nullable": True, "path": "status.staleness"},
    {"name": "verification", "type": "string", "nullable": True, "path": "status.verification"},
]

INSTANCES = (
    ("corpus", REPO / "corpus"),
    ("sol_validator_corpus", REPO / "sol_validator" / "corpus"),
)

DEMO = ROOT / "demos" / "budget_degradation"

README = """# Recorded Exact-Evaluator Runs (SOL-QRY v0.3, Phase 3)

Profile: `solqry-authoritative-exploded/v1`
(`docs/profiles/exploded-representation-profile.{md,json}`)
Regenerate: `cd qry_reference_impl && python3 -m qryref.record_runs`

This directory is the committed evidence for freeze-gate conditions 8 and 12
of the v0.3.0 design draft
(`documentation/RFC-SOL-QRY-0001-v0.3.0.md`):

- **Condition 8** — exact evaluator runs over the authoritative exploded
  RFC-SOL-0001 representation. One full-scan census run per case of both
  committed instances:
  - `corpus/` — 31 cases (prototype instance, the 31/31 lineage ancestor)
  - `sol_validator/corpus/` — 37 cases (current instance, authoritative for
    v0.1.0 conformance)
  Each case directory holds the exact query that was run (`query.json`,
  with the pinned artifact tree digest), the execution record
  (`run.json`, `qry.execution.v0.3`), and the result rows (`rows.json`).
  Every census run completes with the `exact` guarantee.
- **Condition 12** — end-to-end bounded query demonstrating honest budget
  degradation (`demo_budget_degradation/`). The demo artifact
  (`demos/budget_degradation/artifact.sol.d/`, 6 records) is scanned with a
  budget of 2 rows per step: the exact answer `[[2],[4],[6]]` is reached
  only after the third step. Guarantees
  `[bounded, bounded, exact]`, statuses
  `[incomplete_with_continuation, incomplete_with_continuation, complete]`
  — a budget-truncated result never carries the `exact` guarantee
  (spec 30.2). `step_N.json` are the execution records, `state_N.json` the
  continuation states (content-addressed partial-result objects), and
  `report.json` the evidence summary.

## Reproducibility

Every run is reproducible from the repository: the inputs (query + pinned
artifact digest) are committed, and re-running `record_runs` over the
committed artifacts produces byte-identical outputs (spec 37.5
determinism). `report.json` carries a fresh `report_digest` computed over
the report content (excluding the digest field itself).

## Execution model (spec 30)

- Completion states: `complete` / `incomplete_with_continuation` /
  `failed` / `cancelled`.
- A continuation token binds the query digest, the source manifest, the
  policies, the evaluator identities, and the partial-result state
  (30.3); resuming against a different query, instance, or partial state
  fails with `QRY-EXEC-002`.
- Execution records follow 30.4 and validate against
  `schemas/qry_execution.schema.json`.
- The first exact evaluator does not need physical indexes (37.3):
  correct scans over one artifact are sufficient to validate semantics.
  `evaluate` and `least_fixpoint` nodes are not executable by the first
  evaluator and produce `QRY-EXEC-003` (semantic evaluation is Phase 6).
"""


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    path.chmod(0o644)


def census_query(relpath: str, tree_digest: str) -> dict:
    return {
        "schema_version": "qry.query.v0.3",
        "query_id": "solqry-record-census",
        "description": "Exact evaluator census over the authoritative exploded "
                       "representation (gate 8 evidence): scan all records, "
                       "sorted by record_id.",
        "sources": {
            "records": {
                "schema": CENSUS_SCHEMA,
                "artifact": {
                    "path": relpath,
                    "relation": "records",
                    "digest": tree_digest,
                },
            }
        },
        "nodes": [
            {"id": "r", "op": "read", "source": "records"},
            {"id": "s", "op": "sort", "input": "r", "by": ["record_id"]},
        ],
        "root": "s",
    }


def record_instance(instance: str, corpus_dir: Path) -> list[dict]:
    """Record one full-scan census run per case of one corpus instance."""
    out_dir = RUNS / instance
    if out_dir.exists():
        shutil.rmtree(out_dir)
    entries = []
    for case in sorted(p for p in corpus_dir.iterdir() if p.is_dir()):
        art = case / "artifact.sol.d"
        if not art.is_dir():
            raise SystemExit(f"missing artifact: {art}")
        relpath = str(art.relative_to(REPO))
        digest = artifact_tree_digest(art)
        _, total = scan_artifact_relation(art, "records", CENSUS_SCHEMA)
        query = census_query(relpath, digest)
        result = execute_step(query, max(1, total), base_dir=REPO,
                              run_id=f"qrun:{instance}:{case.name}")
        if result.diagnostics or result.status != "complete":
            raise SystemExit(
                f"census run failed for {instance}/{case.name}: "
                f"{[d.rule_id for d in result.diagnostics]} {result.status}")
        _write(out_dir / case.name / "query.json", query)
        _write(out_dir / case.name / "run.json", result.record)
        _write(out_dir / case.name / "rows.json", [list(r) for r in result.rows])
        entries.append({
            "case": case.name,
            "artifact": relpath,
            "artifact_digest": digest,
            "query_digest": query_digest(query),
            "status": result.status,
            "guarantee": result.record["guarantee"]["kind"],
            "rows_returned": result.record["rows_returned"],
            "result_object": result.record["guarantee"]["result_object"],
        })
    return entries


def demo_query() -> dict:
    art = DEMO / "artifact.sol.d"
    return {
        "schema_version": "qry.query.v0.3",
        "query_id": "QDEMO-budget-degradation",
        "description": "Gate 12: the exact answer ([[2],[4],[6]]) is smaller "
                       "than the source (6 rows); with a budget of 2 rows per "
                       "step the run degrades honestly: two bounded "
                       "incomplete_with_continuation steps, then a complete "
                       "exact step.",
        "sources": {
            "tasks": {
                "schema": [{"name": "step", "type": "i64", "nullable": False}],
                "artifact": {
                    "path": str((DEMO / "artifact.sol.d").relative_to(REPO)),
                    "relation": "records",
                    "digest": artifact_tree_digest(art),
                },
            }
        },
        "nodes": [
            {"id": "r", "op": "read", "source": "tasks"},
            {"id": "f", "op": "filter", "input": "r",
             "predicate": {"terms": [{"field": "step", "op": "lte", "value": 6}]}},
            {"id": "s", "op": "sort", "input": "f", "by": ["step"]},
        ],
        "root": "s",
    }


def record_demo(budget: int = 2) -> dict:
    """Run the gate-12 bounded query step by step and record everything."""
    out_dir = RUNS / "demo_budget_degradation"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    query = demo_query()
    _write(out_dir / "query.json", query)

    state: ExecutionState | None = None
    continuation = None
    guarantees, statuses, final_rows = [], [], []
    step = 0
    while True:
        step += 1
        if state is None:
            result = execute_step(query, budget, base_dir=REPO,
                                  run_id=f"qrun:demo_budget_degradation:step_{step}")
        else:
            result = resume_step(query, budget, continuation, state,
                                 base_dir=REPO,
                                 run_id=f"qrun:demo_budget_degradation:step_{step}")
        if result.diagnostics:
            raise SystemExit(f"demo step {step} failed: "
                             f"{[d.rule_id for d in result.diagnostics]}")
        _write(out_dir / f"step_{step}.json", result.record)
        _write(out_dir / f"rows_{step}.json", [list(r) for r in result.rows])
        guarantees.append(result.record["guarantee"]["kind"])
        statuses.append(result.status)
        final_rows = [list(r) for r in result.rows]
        if result.status == "complete":
            break
        if step > 10:
            raise SystemExit("demo did not complete within 10 steps")
        state = result.state
        continuation = result.record["continuation"]
        _write(out_dir / f"state_{step}.json",
               {"offsets": state.offsets, "digest": state.digest()})

    report = {
        "gate_condition": 12,
        "title": "End-to-end bounded query demonstrates honest budget degradation",
        "budget_rows_per_step": budget,
        "steps": step,
        "final_rows": final_rows,
        "guarantees": guarantees,
        "statuses": statuses,
        "query_digest": query_digest(query),
        "source_manifest": result.record["source_manifest"],
        "result_object": result.record["guarantee"]["result_object"],
    }
    _write(out_dir / "report.json", report)
    return report


def main() -> int:
    if RUNS.exists():
        shutil.rmtree(RUNS)
    RUNS.mkdir(parents=True)
    (RUNS / "README.md").write_text(README)
    (RUNS / "README.md").chmod(0o644)
    report = {
        "format": "solqry-exact-evaluator-runs/v1",
        "profile": "solqry-authoritative-exploded/v1",
        "instances": {},
        "demo": None,
    }
    for instance, corpus_dir in INSTANCES:
        entries = record_instance(instance, corpus_dir)
        report["instances"][instance] = {
            "path": str(corpus_dir.relative_to(REPO)),
            "cases": len(entries),
            "runs": entries,
        }
    report["demo"] = record_demo()
    content = canonical_json(report)
    import hashlib
    report["report_digest"] = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
    _write(RUNS / "report.json", report)

    # Sanity: every recorded run validates against the published schema.
    for run_path in RUNS.rglob("*.json"):
        if run_path.name in ("run.json",) or run_path.name.startswith("step_"):
            rec = json.loads(run_path.read_text())
            diags = validate_json_schema(rec, "qry_execution.schema.json", "execution")
            if diags:
                raise SystemExit(f"execution record invalid: {run_path}: {diags}")
    total = sum(v["cases"] for v in report["instances"].values())
    print(f"recorded {total} census runs "
          f"({', '.join(f'{k}: {v['cases']}' for k, v in report['instances'].items())}) "
          f"+ {report['demo']['steps']} demo steps; report_digest "
          f"{report['report_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
