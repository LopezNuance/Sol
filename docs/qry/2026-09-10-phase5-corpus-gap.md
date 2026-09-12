# Phase 5 Corpus Gap: Blocked Normative Cases

Date: 2026-09-10 (UTC)
Subject: RFC-SOL-QRY-0001 v0.3.0 design draft, §36 (64 normative cases)
Plan: `docs/qry/2026-09-08-v03-implementation-plan.md`, Phase 5 (gates 10, 11)

## Status

Phase 5 restructured the corpus into the spec's `QGOLD-*`/`QPATH-*`
namespaces and shipped **48 of the 64 normative cases** as green case
directories under `qry_reference_impl/corpus/cases/`:

- 21 pre-existing (Phases 1 and 4): QGOLD-010/013/014/015/016/019/020/021,
  QPATH-021/022/023/026/031/034/036/037/038/039/041/042/043;
- 27 new (this phase): QGOLD-001/002/003/004/006/007/008/012/017/018,
  QPATH-001/003/004/006/008/009/010/011/012/015/016/017/018/019/030/032/035.

**Phase 6 update (2026-09-10):** the semantic-evaluator phase shipped 8 of
the blocked cases as green case directories (QGOLD-009, QPATH-002/007/020/
024/025/033/040), bringing the corpus to **56 of the 64 normative cases
green** (128/128 with the 72 supplemental cases). QPATH-014 was assigned
to Phase 7: its temporal validation failure is a commit-resolution check
(QV1-02, spec 17.5) in the same commit-identity/freshness domain as the
Phase 7 source-commit machinery (QV8-03, covering-proof pins), and Phase 7
is the only remaining implementation phase.

**Phase 7 update (2026-09-10):** the machine-summary substitution phase
shipped 3 of the blocked cases as green case directories (QGOLD-005,
QPATH-013, QPATH-014), bringing the corpus to **59 of the 64 normative
cases green** (131/131 with the 72 supplemental cases). The remaining
**5 normative cases are blocked by Phase 8** (logical disclosure and
leakage separation). Per the ground rule (green at every phase boundary),
the blocked cases are documented here rather than shipped as failing case
directories. Each unblocks when the named phase lands; the Phase 9 gate
re-run then validates all 64.

**Phase 8 update (2026-09-11):** the logical-disclosure and
leakage-separation phase shipped the final 5 blocked cases as green case
directories (QGOLD-011, QPATH-005, QPATH-027, QPATH-028, QPATH-029),
bringing the corpus to **all 64 of the 64 normative cases green**
(136/136 with the 72 supplemental cases). The machinery:
`qryref/disclosure.py` (QV9-03 bucketed-cardinality baseline with the
reference partition `["0", "1-9", "10-19", "20-99", "100+"]`; QV8-08/
QV9-04 independent provenance visibility, 32.7; QV9-05 error behavior;
QV9-08 non-inference claims, 32.6), the query-level `leakage_policy` and
source-level `restricted` declarations, and the record-level disclosure
declarations (`cardinality_disclosure`, `error_behavior`,
`non_inference_claim`). No blocked cases remain; the Phase 9 gate re-run
validates all 64 from committed artifacts.

## Blocked cases

| Case | Spec title | Expected diagnostics | Blocker | Unblocks in |
|---|---|---|---|---|
| QGOLD-011 | Leakage policy with redacted values and bucketed cardinality | (clean) | Requires the logical-disclosure/leakage separation machinery (redaction, bucketed cardinality, disclosure proofs) — gate conditions 6 and 19. | Phase 8 (shipped 2026-09-11) |
| QPATH-005 | The hidden redaction leak | QV9-03 | QV9-03 (cardinality suppression/bucketing) is not implemented; requires Phase 8 leakage machinery. | Phase 8 (shipped 2026-09-11) |
| QPATH-027 | The verbose denial | QV9-05 | QV9-05 (error and unauthorized-reference behavior obey policy) is not implemented; requires Phase 8. | Phase 8 (shipped 2026-09-11) |
| QPATH-028 | The provenance side door | QV8-08, QV9-04 | QV8-08 (provenance disclosure obeys the selected authorization/leakage policy) and QV9-04 (independent visibility rules for provenance kinds) are not implemented; requires Phase 8. | Phase 8 (shipped 2026-09-11) |
| QPATH-029 | The timing promise | QV9-08 | QV9-08 (no general non-inference claim without a conforming profile) is not implemented; requires Phase 8. | Phase 8 (shipped 2026-09-11) |

## Supplemental cases (retained, documented per F-1)

- **QPATH-044/045/046** (in `corpus/cases/`): out-of-spec gate-18
  adversarial additions — one per mandatory rewrite rule without a
  normative §36.2 case (projection pruning, join associativity, union
  normalization). Retained because §37.4 requires an adversarial case per
  mandatory rule; they are classified supplemental by the corpus report.
- **QRY-001..QRY-069** (moved to `corpus/supplemental/`): the v0.1
  reconstruction's legacy corpus (plan finding F-1: the spec names 64
  normative cases, the freeze report cites 69). Retained and still
  validated by the harness; the v0.3 compatibility layer they exercise
  stays in place until the Phase 5 restructure is complete for them —
  which it now is, in the sense that they validate unchanged against the
  v0.3 engine.

## Implementation notes (drift fixes made in Phase 5)

Two implementation gaps surfaced while building the normative cases;
both were fixed in this phase and are covered by unit tests
(`tests/test_corpus_phase5.py`):

1. **QV2-01/QV2-05 output domain** (`qryref/v3_semantic.py`): the check
   fired when the difference's *right* side read an unbounded source.
   The spec's QPATH-011 ("every value that is not a claim") requires it
   to fire when the *output domain* (left side) is unbounded; an
   unbounded right side only tests membership and cannot make the output
   unbounded. The check now fires on the left side only.
2. **Source-fact canonicalization** (`qryref/canonical.py`):
   `canonical_source` dropped the Phase-5 source-level facts
   (`branch`, `commit`, `bag`, `approximate`, `unbounded`) and the
   per-side `commit` pins, so query digests and source manifests were
   insensitive to them. They are now part of the canonical source, so
   the 30.3 continuation binding is meaningful for branch-pinned
   sources (QPATH-035) and QV1-05 per-side commits affect the manifest.
   Existing digests are unchanged (no pre-Phase-5 source declares these
   facts).
3. **`on` node shape** (`schemas/qry_query.schema.json`): the shared
   node schema declared `on` as an array (join conditions) while the
   `least_fixpoint` engine consumes a single `{left, right}` object.
   The schema now accepts both shapes.

## Gate 10/11 status

- **Gate 10** (64 normative cases with deterministic diagnostics):
  **64/64 green** (Phase 8, 2026-09-11); all normative cases shipped as
  green case directories and validated in the Phase 9 gate re-run.
- **Gate 11** (query and execution records validate against the
  published schemas): satisfied for all shipped cases — queries against
  `qry_query.schema.json`, execution records against
  `qry_execution.schema.json` (QGOLD-001/012, QPATH-012/035 carry real
  execution records bound to their queries).
- Corpus report: `qry_reference_impl/corpus/report.json` (fresh
  `report_digest`, normative/supplemental split).

**Phase 9 (2026-09-11):** the gate re-run validated all 64 normative
cases from committed artifacts as part of the 19/19 freeze-gate pass;
see `freeze_report_v030.json` and the plan's Phase 9 row.
