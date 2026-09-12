# SOL-QRY Freeze-Gate Reproducibility Gap

Date: 2026-09-08 (UTC)
Subject: `freeze_report.json` (SOL-QRY v0.3 freeze gate, 18/19, NOT_FROZEN)

## Provenance of the 18/19 result

`freeze_report.json` was produced by the OpenAI Codex chat session that built
the first SOL-QRY implementation ("the executable bound-algebra implementation
and validators", named in the report as the `authoritative_feedback_source`).
The gate run and all of its evidence artifacts exist in that session's
sandbox. They were never exported into this repository. The only QRY-adjacent
artifact moved into this repo so far is the original 31-case SOL corpus
(`corpus/`), which is the SOL-side lineage ancestor, not the QRY
implementation.

## Evidence cited by the gate that is absent from this repo

| Gate condition | Cited evidence | Status in this repo |
|---|---|---|
| 3 (canonical typed AST + canonicalization schemas) | `schemas/query.schema.json`, `schemas/execution.schema.json`, `schemas/bound.schema.json`; `query_digest sha256:adfd2597...` | **absent** |
| 4 (Substrait mapping profile) | `docs/substrait-profile.md`; `mapping_digest sha256:56c68814...` | **absent** |
| 8 (authoritative exploded representation) | `reference_profile solqry-reference-exploded/v1`, scan passed | reference profile absent; **authoritative profile now published** (`docs/profiles/exploded-representation-profile.json`, `solqry-authoritative-exploded/v1`) |
| 10 (69-case QRY corpus) | `report_digest sha256:b135e1d0...` (69/69) | **absent** (QGOLD/QPATH cases not in repo) |
| 18 (rewrite-kernel proof certificates) | 5 certificates under `/mnt/data/solqry-bound-algebra-ref/proofs/certificates/` with transcript digests | **absent** (external path, not on this machine) |
| 1, 2, 5, 6, 7, 9, 11-17, 19 | operator coverage, guarantee composition, rewrite registration, disclosure baseline, evaluator keys, substitution, end-to-end bounded query, one-sided bounds, bound provenance, stale assurance, policy boundaries, AVG rule, leakage separation | evidence recorded in `freeze_report.json`; the implementation that produced it is **absent** |

The digests recorded in `freeze_report.json` (query, mapping, corpus report,
certificate transcripts) are bound to the original sandbox artifacts. Any
artifact re-derived from the v0.3.0 spec draft in this repo would carry
different digests and would **not** reproduce the recorded 18/19; it would be a
fresh publication requiring a fresh gate run.

## Reconstruction received (2026-09-08)

A QRY reference implementation was moved into the repo at `qry_reference_impl/`.
It is a **reconstruction**, explicitly not the original OpenAI sandbox package:

> "This package is a reconstructed QRY reference implementation generated from
> the available thread context. It is **not guaranteed to be byte-identical** to
> the missing OpenAI sandbox package." — `qry_reference_impl/README.md`

What it provides (all now present in the repo):

| Artifact | Location | Notes |
|---|---|---|
| Bound-algebra reference implementation + validators | `qry_reference_impl/qryref/` | engine, validate, rules, bounds, certificate, substrait_mapper, diagnostics |
| Three JSON Schemas | `qry_reference_impl/schemas/` | `qry_query`, `qry_bounds`, `qry_certificate` (draft 2020-12) |
| Substrait profile | `qry_reference_impl/substrait/` | `qry_substrait_profile.yaml` (conservative-subset, JSON sketch) + `mapping.md` |
| 69-case corpus | `qry_reference_impl/corpus/cases/` | `QRY-001`..`QRY-069` |
| Proof certificates | `qry_reference_impl/certificates/` + per-case `certificate.json` | machine-checkable bound-derivation steps |

It runs: `python -m qryref.validate_corpus corpus` → **69/69 cases satisfied
expected diagnostics** (verified 2026-09-08).

### What the reconstruction is

A compact v0.1 design: a QRY intermediate representation for a bounded subset
of relational algebra, focused on **static validation, conservative
row/schema bound inference, and proof-certificate validation** ("the focus is
not execution"). Bound inference uses filter selectivity annotations
(`min_selectivity`/`max_selectivity`) and join relationship cardinality
(`many_to_many`/`many_to_one`/`one_to_many`/`one_to_one`). Validator layers:
`QRY-SCHEMA-*`, `QRY-SEM-*`, `QRY-BOUND-*`, `QRY-CERT-*`, `QRY-SUBSTRAIT-*`.

### What it is NOT (and why it does not close the v0.3.0 gate)

- **Not the original** that produced the 18/19; its digests will not match the
  freeze report's recorded `query_digest`, `mapping_digest`, `report_digest`,
  or certificate transcript digests.
- **Not an implementation of the v0.3.0 design draft.** It contains none of
  the freeze-report's specific registered rule IDs (`sol:rewrite/*`,
  `sol:bound/avg_optional_prefix/v1`), uses `QRY-NNN` corpus case names rather
  than the spec's `QGOLD-*`/`QPATH-*` namespaces, and its Substrait profile is
  a conservative-subset JSON sketch rather than the full mapping the v0.3.0
  draft contemplates.
- Therefore it **cannot re-run the v0.3.0 freeze gate (§44) to 19/19**. The
  gate's conditions reference the v0.3.0 spec's rules, cases, and digests,
  which this v0.1 reconstruction does not implement.

### Effect on the gap

- The "artifacts absent from the repo" half of the gap is **closed**: the
  three schemas, Substrait profile, 69-case corpus, certificates, and
  bound-algebra implementation now exist in the repo (reconstructed).
- The "18/19 not reproducible" half is **not closed**: the reconstruction is a
  different design with different digests, so it does not reproduce the
  recorded 18/19, and it does not satisfy the v0.3.0 gate.

## What is needed to close the gap

1. **Export the QRY implementation** (bound-algebra reference implementation +
   validators) from the OpenAI sandbox into this repo (e.g. `solqry/`).
2. **Commit the four cited artifacts**: `schemas/query.schema.json`,
   `schemas/execution.schema.json`, `schemas/bound.schema.json`,
   `docs/substrait-profile.md` (paths as cited, or updated paths recorded in a
   revised freeze report).
3. **Commit the QRY corpus** (69 golden/pathological cases) and its report.
4. **Commit or pin the proof certificates** (files + transcript digests) so
   condition 18 is checkable from the repo.
5. **Re-run the gate** with the authoritative profile
   (`solqry-authoritative-exploded/v1`) supplied. Condition 8 should then pass
   on the strength of the published profile + a recorded evaluator run over
   the committed corpus instances.
6. On 19/19, mark v0.3.0 frozen per §44 of the v0.3.0 design draft.

## What this repo already contributes to the gate

- The authoritative exploded representation profile (condition 8 designation):
  `docs/profiles/exploded-representation-profile.{md,json}`.
- The SOL-side corpus instances the QRY evaluator runs over: `corpus/` (31
  cases, prototype lineage) and `sol_validator/corpus/` (37 cases, current).
- The promoted RFC-SOL-0001 v0.1.0 baseline that the profile anchors to
  (`Sol_RFC.md`), including §56 (exploded representation) and §14.6
  (reference container).

## Status

- Condition 8 blocker: **cleared at the designation level** (authoritative
  profile published 2026-09-08). A recorded evaluator run over the committed
  instances is still required to evidence the condition in a re-run.
- Conditions 1-7, 9-19: evidence recorded in `freeze_report.json` but **not
  reproducible from this repo**. The reconstruction at `qry_reference_impl/`
  supplies the artifacts (schemas, Substrait profile, 69-case corpus,
  certificates, bound-algebra implementation) but is a v0.1 reconstruction,
  not the original implementation, so it does not reproduce the 18/19 and does
  not satisfy the v0.3.0 gate.
- Gate status: **NOT_FROZEN** (unchanged; no re-run has been performed).

## Path forward (decision needed)

The reconstruction changes the options:

1. **Freeze v0.3.0 (the design draft's target).** Requires either the original
   OpenAI sandbox implementation (not available) or a full implementation of
   the v0.3.0 spec (registered rewrite rules, `sol:bound/avg_optional_prefix`,
   `QGOLD-*`/`QPATH-*` corpus, full Substrait mapping) — a substantially larger
   task than the v0.1 reconstruction.
2. **Adopt the reconstruction as a new v0.1 QRY baseline.** Treat
   `qry_reference_impl/` as a coherent v0.1 bound-algebra + certificates spec
   with its own (smaller) freeze gate, and re-scope the v0.3.0 design draft as
   the forward target. This is the smaller, honest step and matches what is
   actually in the repo.
3. **Extend the reconstruction toward v0.3.0.** Incrementally add the v0.3.0
   spec's registered rules, corpus namespaces, and Substrait mapping to the
   v0.1 engine until it can evidence the §44 gate.

Option 2 is recommended as the immediate next step (it matches the repo state
and is verifiable now); option 1 or 3 is the path if the goal is specifically
the v0.3.0 design draft.

## Decision (2026-09-08)

**Option 3 selected.** The reconstruction at `qry_reference_impl/` will be
extended incrementally toward the v0.3.0 design draft until it can evidence
the §44 freeze gate with a fresh, honest gate run from this repository.

- Phased implementation plan: `docs/qry/2026-09-08-v03-implementation-plan.md`
  (9 phases; all 19 gate conditions mapped; Phase 1 = answer-bound algebra
  and bound provenance).
- The recorded 18/19 remains historical OpenAI-chat evidence; the target is
  a new gate run with fresh digests computed from committed artifacts.
- Status: **in progress**. Phase 1 (answer-bound algebra and bound
  provenance) completed 2026-09-08: certified L/U bound algebra implemented
  in `qry_reference_impl/qryref/certified.py`, 36 unit tests green, corpus
  79/79 (69 legacy + 6 QGOLD + 4 QPATH) with deterministic diagnostics.
  Phase 2 (typed AST and canonicalization) completed 2026-09-09: canonical AST with query
  digests and source manifests, policy-boundary nodes, Sol extension declarations, full
  Substrait mapping profile with recorded `mapping_digest`, execution-record schema;
  55 unit tests green, corpus 79/79 deterministic.
  Phase 3 (exact evaluator over exploded artifacts) completed 2026-09-09: exact scan
  evaluator over the authoritative exploded representation with budget/continuation and
  honest completion states; 68 recorded census runs committed (31 + 37 instances) plus the
  gate-12 bounded-query demo (final rows [[2],[4],[6]], guarantees [bounded,bounded,exact],
  statuses [incomplete_with_continuation x2, complete]); 70 unit tests green, corpus 79/79.
  Phase 4 (rewrite registry and proof kernel) completed 2026-09-10: 7-rule
  registry (5 mandatory + policy-boundary + 1 experimental) and the 25.4
  application kernel (policy/evaluator-boundary default non-preserving
  QV7-07/QV6-05, stale evidence QV5-10/QV7-04, prose-only proof QV7-08,
  physical claims QV7-09/QV9-10, experimental rule QV7-06, machine-summary
  substitution QV8-03/QV8-04 with the Phase-7 answering gate); 6 seeded
  property tests (machine-summary substitution cross-checks the kernel's
  decision against the covering decision procedure); 8 committed artifacts
  under `certificates/rewrites/` (6 property certificates with transcript
  digests, the disclosure proof, the committed covering proof, the registry
  report `report_digest sha256:7216fec1a63c...`); 14 rewrite corpus cases
  including one adversarial case per mandatory rule (§37.4, gate 18);
  105 unit tests green, corpus 93/93 deterministic.
  Phase 5 (query pathology corpus) completed 2026-09-10: corpus
  restructured into the spec's QGOLD/QPATH namespaces (69 legacy QRY-NNN
  cases retained as supplemental under `corpus/supplemental/`); 27 new
  normative cases (48 of the 64 now active, 16 blocked by Phases 6-8 and
  documented in `docs/qry/2026-09-10-phase5-corpus-gap.md`); execution-
  record case support (spec 30) with real exact-evaluator runs over the
  committed GOLD-01 artifact (QV5-07, QRY-EXEC-002); corpus report
  artifact `corpus/report.json` with a fresh `report_digest`
  (normative/supplemental split); 119 unit tests green, corpus 120/120
  deterministic (48 normative + 72 supplemental).
