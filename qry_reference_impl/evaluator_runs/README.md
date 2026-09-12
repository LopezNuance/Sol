# Recorded Exact-Evaluator Runs (SOL-QRY v0.3, Phase 3)

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
