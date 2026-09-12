# SOL-QRY v0.3.0 Implementation Plan (Option 3)

Date: 2026-09-08 (UTC)
Status: active
Supersedes: the "decision needed" state of `2026-09-08-reproducibility-gap.md`
Decision: **Option 3 — extend the reconstruction toward v0.3.0** (user, 2026-09-08)

## 1. Objective

Extend `qry_reference_impl/` (the v0.1 QRY reconstruction, currently 69/69)
incrementally until it implements the v0.3.0 design draft
(`documentation/RFC-SOL-QRY-0001-v0.3.0.md`) well enough to
**evidence the §44 freeze gate with a fresh, honest gate run from this
repository**, then mark v0.3.0 frozen per §44.

The recorded 18/19 in `freeze_report.json` is historical OpenAI-chat evidence
bound to sandbox digests. It is **not** reproducible and is not the target.
The target is a new gate run whose every cited artifact (schemas, mapping
profile, corpus report, certificates, evaluator runs) exists in this repo and
whose digests are computed from the committed artifacts.

## 2. Ground rules

1. **Fresh publication.** The gate re-run produces a new freeze report with
   new digests. `freeze_report.json` stays in the repo as historical evidence
   and is not edited.
2. **Green at every phase boundary.** `cd qry_reference_impl &&
   python3 -m qryref.validate_corpus corpus` passes at the end of every
   phase (69/69 until Phase 5 restructures the corpus; then the
   QGOLD/QPATH count).
3. **Deterministic diagnostics.** Same source + same query → same
   diagnostics → same ordering (§37.5). Exact-match discipline, as in the
   SOL corpus `--strict-extra` mode.
4. **Triage discipline.** Every semantic defect found during implementation
   is triaged as erratum / new corpus entry / unfreeze candidate (§36.3,
   §44). Unfreeze candidates are batched, not applied ad hoc.
5. **No drift.** Before each code change, the relevant spec section is
   re-read; drift is surfaced, not papered over.
6. **Compatibility during transition.** The v0.3 AST schema (Phase 2)
   accepts the v0.1 query shape as a subset and canonicalizes it, so the
   existing 69-case corpus stays green until Phase 5 rewrites the fixtures
   into canonical v0.3 form under the QGOLD/QPATH namespaces.

## 3. Findings logged at plan time

| # | Finding | Triage |
|---|---|---|
| F-1 | Corpus count mismatch: spec §36.1/§36.2 names **64** cases (QGOLD-001..021 = 21, QPATH-001..043 = 43); the freeze report cites a **69**-case corpus; the Q20 decision text says "QGOLD-001 through QGOLD-020 and the QPATH set" = **63**. | **Unfreeze candidate** (batch with the next semantic revision). Implementation target: the 64 normative cases; the reconstruction's extra cases are retained as supplemental and documented. |
| F-2 | The reconstruction's bound model is row-count min/max only; v0.3.0 requires certified tuple relations $L \subseteq R \subseteq U$ with guarantee kinds, provenance, and aggregate bound rules. | Scope of Phase 1 (expected gap, not a defect). |
| F-3 | Gate condition 8 evidence requires *recorded evaluator runs* over the committed exploded-representation instances (`corpus/`, `sol_validator/corpus/`); the published profile clears the designation only. | Scope of Phase 3. |
| F-4 | Interval-valued aggregates cannot be modeled as endpoint tuples in L/U: the aggregate result is a certified *numeric interval* (13.11), so L/U carry the certified/enclosed group keys and the per-group intervals are carried as a separate annotation on the bound record. | Implementation decision (Phase 1), consistent with 13.11-13.14; no spec change needed. |

## Phase status (updated 2026-09-11)

| Phase | Status | Evidence |
|---|---|---|
| 1 — Answer-bound algebra and bound provenance | **COMPLETE** (2026-09-08) | `qryref/certified.py` (certified L/U relations, guarantee kinds, transfer rules for all 16 gate-condition-1 operators, one-sided structural containment, difference/complement/recursion, COUNT_SET/SUM/MIN-MAX/`sol:bound/avg_optional_prefix/v1`, assurance + stale downgrade, bound provenance, L⊆U validation, QV5-01/02/03/04/06/10/12, QV8-06/07, QINV-14). 36 unit tests green (`tests/test_certified.py`); corpus **79/79** (69 legacy + QGOLD-013/014/015/016/019/020, QPATH-031/037/038/042) with deterministic diagnostics; SOL side unchanged (37/37 strict, 12/12 demo). |
| 2 — Typed AST and canonicalization | **COMPLETE** (2026-09-09) | `qryref/canonical.py` (idempotent canonicalization, `digest:sha256` query digests, per-source `object:sha256` + `manifest_digest` source manifests), `qryref/rules.py` (QRY-SEM-018/019, §29.2 extension URNs, `sol:bound/policy_boundary/v1`), `qryref/engine.py` (policy-boundary op + extension-declaration check), `qryref/certified.py` (policy-boundary identity transfer), `qryref/substrait_mapper.py` (all 18 ops mapped, set-op kinds, profile digest, QRY-SUBSTRAIT-001/002), `substrait/qry_substrait_profile.yaml` (v0.3 normative baseline) with recorded `mapping_digest`, `schemas/qry_execution.schema.json` (§30 shape), `extensions` added to `schemas/qry_query.schema.json`. 19 tests in `tests/test_canonical.py` (idempotence, digest stability under key/node/tuple order, source manifests, policy boundary, extension declarations, Substrait mapping, execution schema); 55 unit tests green; corpus 79/79 with deterministic diagnostics; SOL side unchanged (37/37 strict, 12/12 demo). |
| 3 — Exact evaluator over exploded artifacts | **COMPLETE** (2026-09-09) | `qryref/exact.py` (exact scan evaluator over the authoritative exploded representation `solqry-authoritative-exploded/v1`: artifact tree digests, content-pinned artifact sources, budget-limited execution with continuations per §30.2/§30.3, honest completion states, settledness rules incl. early `limit` settlement, execution records per §30.4, QRY-EXEC-001..008); `qryref/run_evaluator.py` (CLI); `qryref/record_runs.py` (recorded-run harness); `evaluator_runs/` committed (68 census runs: 31 prototype + 37 current instance, all complete/exact, with fresh `report_digest`; gate-12 demo: 3 steps, guarantees `[bounded,bounded,exact]`, statuses `[incomplete_with_continuation×2, complete]`, final rows `[[2],[4],[6]]`); `demos/budget_degradation/` (demo artifact + query); `artifact` source kind added to `schemas/qry_query.schema.json` (with field `path` for dot-path extraction) and `canonical.py` (instance-sensitive source manifests). 15 tests in `tests/test_exact.py` (scan, digest pin, full scan, budget/continuation, binding mismatch, limit settlement, set ops/join/aggregate, non-executable ops, recorded-run reproducibility); 70 unit tests green; corpus 79/79 deterministic; SOL side unchanged (37/37 strict, 12/12 demo). |
| 4 — Rewrite registry and proof kernel | **COMPLETE** (2026-09-10) | `qryref/rewrites.py` (7-rule registry: 5 mandatory + policy-boundary + 1 experimental; the 25.4 application kernel: registration QV7-01, preconditions QV7-02, evaluator barrier QV6-05, policy-boundary default non-preserving QV7-07/QV9-09/QINV-15, stale evidence QV5-10/QV7-04, prose-only proof QV7-08, physical claims QV7-09/QV9-10, experimental rule QV7-06, machine-summary substitution QV8-03/QV8-04 with the Phase-7 answering gate); `qryref/property_tests.py` (6 seeded property tests; machine-summary substitution is a cross-check of the kernel's QV8-03/QV8-04/eligible decision against the covering decision procedure); `qryref/rewrite_report.py` + `qryref/check_certificate.py` (CLIs); `certificates/rewrites/` (6 property certificates with transcript digests, the disclosure proof, the committed covering proof, and the registry report, `report_digest sha256:7216fec1a63c...`); `rewrites/*.md` (7 human-readable derivations); 14 rewrite corpus cases (QGOLD-010/021; QPATH-021/022/023/026/034/036/039/041/043/044/045/046) — every mandatory rule has an adversarial case (§37.4, gate 18); 35 tests in `tests/test_rewrites.py` (registry shape, golden patterns, exact QPATH diagnostics, §36.3 sensitivity, certificate round-trip, report determinism); 105 unit tests green; corpus **93/93** deterministic; SOL side unchanged (37/37 strict, 12/12 demo). |
| 5 — Query pathology corpus | **COMPLETE** (2026-09-10) | Corpus restructured into the spec's `QGOLD-*`/`QPATH-*` namespaces (36.1/36.2, F-1): 69 legacy `QRY-NNN` cases moved to `corpus/supplemental/` (retained, still validated); 27 new normative cases added by `qryref/make_corpus_phase5.py` (certified-bound goldens QGOLD-002/003/004/006/007/008/017/018 with hand-computed cores; execution-record cases QGOLD-001/012, QPATH-012/035 with real exact-evaluator runs over the committed GOLD-01 artifact — QV5-07 truncation-labeled-exact and QRY-EXEC-002 continuation drift; the QV8-03 stale-materialized-view rewrite case QPATH-008; plan-shape/claim pathologies QPATH-001/003/004/006/009/010/011/015/016/017/018/019/030/032); execution-record case support in `qryref/validate.py` (schema, 30.3 binding, manifest pins, QV5-07, QRY-EXEC-002 resume check); `qryref/validate_corpus.py` normative/supplemental split + corpus report artifact (`corpus/report.json`, fresh `report_digest`); `corpus/manifest.json` upgraded to `qry.corpus.v0.3`. Drift fixes: QV2-01/05 now fire on the difference's output domain (left side) per QPATH-011; `canonical_source` now includes the source-level facts (`branch`/`commit`/`bag`/`approximate`/`unbounded`) and per-side commit pins so digests/manifests are instance-sensitive; the `on` node shape accepts both join (array) and least-fixpoint (object) forms. 16 normative cases blocked by Phases 6-8 are documented in `docs/qry/2026-09-10-phase5-corpus-gap.md`, not shipped as failing directories (ground rule: green at every phase boundary). 119 unit tests green (14 new in `tests/test_corpus_phase5.py` + restructured `tests/test_corpus.py`); corpus **120/120** (48 normative + 72 supplemental) deterministic; SOL side unchanged (37/37 strict, 12/12 demo). |
| 6 — Materialized and bounded semantic evaluators | **COMPLETE** (2026-09-10) | `qryref/evaluators.py` (registered evaluator contracts per 26.2: deterministic `positive_classifier`, stochastic `vector_similarity`/`semantic_equivalence` (semantic-equivalence relations), stochastic `tuple_generator` (not tuple-preserving); the Q15 universal evaluation-key fields (26.5); the 26.7 materialized-assessment record contract; the equality prohibition (26.8); the inline-evaluator barrier (26.4); claim-based checks QV5-08/QV5-09/QV6-07); `schemas/qry_query.schema.json` (top-level `required_dimensions`, source-level `assessment` record); `qryref/canonical.py` (assessment and non-empty `required_dimensions` join the source/query identity; digests of existing cases unchanged); `qryref/v3_semantic.py` (plan-shape and claim checks wired into the semantic pipeline); `qryref/certified.py` (evaluate transfer: a tuple-generating evaluator certifies no upper side — 13.7.1, 26.6); `qryref/engine.py` (QRY-SEM-018: a filter with an evaluator term or an assessment source requires the declared extension `urn:qry:v0.3:semantic-evaluator-barrier` / `urn:qry:v0.3:materialized-assessment`); `qryref/rewrites.py` (QV8-02 via the covering proof's `guarantee` field, QV7-03 preservation-dimension coverage in the application kernel, committed `covering-proof-heuristic.json`); `qryref/rules.py` (13 new rules: QINV-04/13, QV5-08/09, QV6-01..07, QV7-03, QV8-02); `qryref/check_certificate.py` (the heuristic covering proof verifies against its own builder); `qryref/make_corpus_phase6.py` (8 new normative cases: QGOLD-009 materialized-assessment golden; QPATH-002 equality forgery; QPATH-007 duplicated stochastic call; QPATH-020 heuristic resurrection; QPATH-024 transient memo; QPATH-025 incomplete key; QPATH-033 hidden heuristic view; QPATH-040 fabricated selector); 23 tests in `tests/test_evaluators.py` (registry/Q15 shape, key contract, forgery, duplication with/without the required dimension, claim checks, assessment immutability, kernel gates, corpus regression). 142 unit tests green; corpus **128/128** (56 normative + 72 supplemental) deterministic; SOL side unchanged (37/37 strict, 12/12 demo). |
| 7 — Machine-summary substitution | **COMPLETE** (2026-09-10) | `qryref/rewrites.py` (the Phase-7 answering gate is lifted: `sol:rewrite/substitute_exact_machine_summary/v1` applies for a proven covering query — committed covering proof, matching source commit, field-complete, exact guarantee — and the rewritten query answers the span's sources from the committed machine summary (source-level `machine_summary` annotation with the covering proof and the source-commit pin, 28.3/28.5); the application record carries the covering proof and the source-commit pin; QV8-02 via the proof's `guarantee` field); `qryref/make_rewrites_corpus.py` (`gold_covering_proof`/`gold_covering_proof_digest`; the committed field-complete exact covering proof `covering-proof-gold.json`); `qryref/rewrite_report.py` (writes the gold proof; registry report digest unchanged, `sha256:7216fec1a63c…`); `qryref/check_certificate.py` (each committed covering proof verifies against its own builder); `qryref/property_tests.py` (the eligibility cross-check now treats no precondition diagnostics as eligible; transcript digest unchanged); `schemas/qry_query.schema.json` (source-level `machine_summary` and `latest` declarations); `qryref/canonical.py` (both join the source identity); `qryref/v3_semantic.py` (QV1-02 temporal validation: a latest-commit selection requires an ancestry relation and a deterministic tie or conflict rule, 17.5; the claim-context half of QV7-03: a rewrite cited in the claim's provenance must cover the query-required dimensions, 25.4.3); `qryref/certified.py` (QV8-05: a requested mode above `tuple` requires per-tuple membership provenance for every lower tuple, 12.4–12.5); `qryref/rules.py` (QV8-05); `qryref/make_corpus_phase7.py` (3 new normative cases: QGOLD-005 exact machine-summary substitution, applied and recorded; QPATH-013 the provenance-dropping rewrite; QPATH-014 the timestamp time traveler); 17 tests in `tests/test_phase7.py` (substitution application and record, exact-result preservation, all four ineligible paths, QV8-05 modes, QV7-03 claim context, QV1-02 temporal, corpus regression); two Phase-4 tests updated from the Phase-7 gate to the applied behavior. 159 unit tests green; corpus **131/131** (59 normative + 72 supplemental) deterministic; SOL side unchanged (37/37 strict, 12/12 demo). |
| 8 — Logical disclosure and leakage separation | **COMPLETE** (2026-09-11) | `qryref/disclosure.py` (logical-disclosure baseline, 32: the mandatory bucketed-cardinality mechanism with the reference baseline partition `["0", "1-9", "10-19", "20-99", "100+"]` carrying the 10-19 bucket, well-formed-partition validation, and the disclosure checks QV9-03 (raw count under a bucketed policy, undeclared buckets, disclosure under suppression), QV8-08/QV9-04 (provenance visibility applied independently to lower-membership, upper-derivation, and rewrite/evaluator identities, 32.7 — a restricted-source citation under a redacted provenance policy is the side door), QV9-05 (error and unauthorized-reference behavior obey policy, 32.5), QV9-08 (no general non-inference claim without a conforming profile — adversary model, query history, leakage channels, verification method — and no declared physical channel weaker than suppressed, 32.6); the logical/physical separation of gate 19 rests on this plus the Phase-4 kernel's QV7-09/QV9-10); `schemas/qry_query.schema.json` (query-level `leakage_policy` declaration — logical-disclosure dimensions, `count_buckets`, physical side channels, optional non-inference profile — and source-level `restricted` flag); `schemas/qry_bounds_v3.schema.json` (record-level disclosure declarations: `cardinality_disclosure`, `error_behavior`, `non_inference_claim`); `qryref/canonical.py` (the `restricted` flag joins the source identity, the leakage policy joins the query identity, 29.4); `qryref/certified.py` (`validate_bound_record` takes the full record and runs the disclosure checks); `qryref/rules.py` (QV8-08, QV9-03/04/05/08); `qryref/make_corpus_phase8.py` (5 new normative cases: QGOLD-011 leakage policy with redacted values and bucketed cardinality, clean; QPATH-005 the hidden redaction leak; QPATH-027 the verbose denial; QPATH-028 the provenance side door; QPATH-029 the timing promise); 31 tests in `tests/test_phase8.py` (bucket partition mechanism, QV9-03 modes, QV8-08/QV9-04 categories, QV9-05, QV9-08 conforming/weak-channel paths, canonicalization, corpus regression). 190 unit tests green; corpus **136/136** (64 normative + 72 supplemental) deterministic — all 64 normative cases of the spec now shipped; SOL side unchanged (37/37 strict, 12/12 demo); rewrite registry report digest unchanged (`sha256:7216fec1a63c…`). §37.8 (SOL-IDX/SOL-PLAN, physical conformance profiles) remains post-gate and out of scope. |
| 9 — Gate re-run and freeze | **COMPLETE** (2026-09-11) | `qryref/gate_check.py` (the §44 gate harness: re-evidences all 19 conditions from committed repository artifacts with fresh digests — bound-rule coverage for the 16 core operators, deterministic reject/downgrade cases (QPATH-003/006), canonicalization schemas + a fresh query digest, the Substrait mapping profile with the recomputed mapping digest, the rewrite registry report with the recomputed report digest, the logical-disclosure baseline (bucket 10-19) with its five validator rules and the Phase 8 cases, the materialized-assessment golden with its evaluation key, the 68 recorded exact-evaluator runs (all complete/exact) with the recomputed runs report digest, the proven-covering substitution (QGOLD-005 applied, QPATH-034 lossy-rejected), the full corpus report (136/136, 64/64 normative) with the recomputed report digest, the execution-record cases against the published schemas, the gate-12 budget-degradation demo, QGOLD-013..016, the bound-provenance golden and pathologies (QGOLD-018, QPATH-037/038), the stale-assurance case (QPATH-023), the policy-boundary rewrite pair (QPATH-026 rejected, QGOLD-021 applied with the disclosure proof), the AVG golden and pathology (QGOLD-020, QPATH-042) with the certified intervals, the checked certificate set (5 property certificates, the disclosure proof, 3 committed covering proofs, the registry report) with the adversarial case per mandatory rule, and the logical/physical leakage separation (QPATH-043, QPATH-029, QGOLD-011)); `freeze_report_v030.json` (19/19, status FROZEN, report digest `sha256:1ea510ee17a5…`; the historical `freeze_report.json` retained untouched); the spec's status section and NEXT_STEPS record the freeze. |

## 4. Phase plan

Phase order follows the spec's normative implementation order (§37), with the
logical-disclosure work (gate 6, 19) inserted before the gate re-run because
§37.8 (physical profiles) is explicitly post-gate.

### Phase 1 — Answer-bound algebra and bound provenance

Spec: §37.1, §12.5–12.9, §13.1–13.19. Gate: **1, 2, 13, 14, 15, 17**.

Scope:

- Certified lower/upper relation objects: concrete tuple sets and symbolic
  row-count bounds as proof-equivalent representations (§13.16).
- Design decision (P1): QRY IR sources **MAY** carry a `tuples` array
  (finite exact instances). When present, the source's exact denotation is
  the tuple set and $L = U = R$ is computable; when absent, row-count bounds
  remain the symbolic path (guarantees `lower_bound` / `upper_bound` /
  `bounded`). This keeps the existing 69-case corpus green (symbolic path)
  while making golden cases executable (concrete path).
- Guarantee kinds: `exact`, `lower_bound`, `upper_bound`, `bounded`,
  `heuristic` (§13.2); invariant $L \subseteq U$ MUST hold (§13.1) and is
  validated (`QV5-01`).
- Transfer rules for every core logical operator (gate condition 1):
  Annotate, Difference, Distinct, Evaluate, Group, Intersect, Join,
  LeastFixpoint, Limit, Order, Project, Relation, Rename, Select,
  TemporalSlice, Union.
- Componentwise transfer (positive monotone, exact deterministic
  predicates) and structural one-sided containment for heuristic
  suboperations (§13.7, §13.7.1): tuple-preserving Select →
  $U_{out} = U_R$; Intersect → $U_1$ (or $U_1 \cap U_2$); Difference →
  $U_1$ (or $U_1 \setminus L_2$); Union → any available $L$; certified
  positive filter may replace the empty lower.
- Difference $L_R = L_1 \setminus U_2$, $U_R = U_1 \setminus L_2$
  (§13.8); complement vs explicit finite exact domain $D$:
  $L = D \setminus U_R$, $U = D \setminus L_R$ (§13.9); recursion:
  separate lfp lower/upper with stratification (§13.10).
- Aggregate bounds: COUNT_SET $|L| \le C \le |U|$ (§13.11); SUM
  min/max over $O = U \setminus L$ (§13.12); MIN/MAX (§13.13);
  `sol:bound/avg_optional_prefix/v1` with extremal optional prefixes and
  `may_be_empty` when $n_L = 0$ (§13.14).
- Mixed-guarantee composition invalidates only dependent sides; no
  label-inferred guarantees; concrete bound objects propagate (§13.16).
  Partial-bound availability: sides computed independently (§13.17).
  Validity ≠ tightness: the validator MUST NOT reject tighter bounds
  (§13.18); guarantee validation checklist (§13.19).
- Unsupported guarantee compositions deterministically reject or downgrade
  (gate condition 2).
- Assurance (§13.3): statuses `proven` / `validated` / `contract_asserted` /
  `tested` / `unaudited` / `unknown`; evidence kinds per the Q5 decision;
  stale dependencies → effective `unknown`.
- Provenance: lower-membership modes `tuple` / `why` / `how` / `full_graph`
  (minimum `tuple`, Q7); upper-bound derivation fields per Q8; $U \setminus L$
  tuples are unexcluded and carry no positive why-provenance; exact collapse
  $L = U = R$ (§12.5–12.9).
- L/U serialization as content-addressed object references
  (`object:sha256:...`) with the exact-collapse shorthand (§13.4, Q4);
  unavailable sides explicit, never synthesized (§13.5).

Acceptance:

- Unit tests for every transfer rule, including one-sided containment and
  the $L \subseteq U$ invariant.
- New corpus cases pass with deterministic diagnostics: QGOLD-013,
  QGOLD-014, QGOLD-015, QGOLD-016, QGOLD-019, QGOLD-020; QPATH-031,
  QPATH-037, QPATH-038, QPATH-042.
- Existing 69-case corpus still green (symbolic row-bound path unchanged).

### Phase 2 — Typed AST and canonicalization

Spec: §37.2, §29.1–29.5. Gate: **3, 4**.

Scope:

- Typed AST schema (v0.3) published; deterministic canonicalization;
  query digests.
- Source manifests; explicit policy-boundary nodes.
- Full Substrait mapping profile documented (supersedes the
  conservative-subset sketch) with a recorded `mapping_digest`.
- Sol extension declarations for `sol:rewrite/*`, `sol:bound/*`,
  `sol:evaluator/*` references (Q19).
- Compatibility layer: v0.1 query shape accepted and canonicalized to v0.3
  form so the 69-case corpus stays green.

Acceptance:

- Published schemas validate every corpus query and execution record.
- Canonicalization is idempotent and digest-stable (same bytes → same
  digest; re-canonicalization is a no-op).
- Substrait mapping profile committed with digest; every standard node in
  the corpus maps; unmapped nodes produce a deterministic diagnostic.

### Phase 3 — Exact evaluator over exploded artifacts

Spec: §37.3, §30.1–30.4. Gate: **8, 12**.

Scope:

- Exact scan evaluator over the RFC-SOL-0001 exploded debug representation
  per the authoritative profile `solqry-authoritative-exploded/v1`
  (`docs/profiles/exploded-representation-profile.{md,json}`). No physical
  indexes required.
- Recorded evaluator runs over the committed instances: `corpus/` (31
  cases) and `sol_validator/corpus/` (37 cases).
- Budget/limit with continuations and honest completion states
  (§30.2, §30.3); `incomplete_with_continuation` results carry bounded
  guarantees, not exact labels.
- End-to-end bounded query demonstrating honest budget degradation
  (gate condition 12): a query whose exact answer is larger than the
  budget, run to a bounded result with correctly labeled guarantees and
  statuses.

Acceptance:

- Recorded runs committed (inputs, digests, outputs) and reproducible from
  the repo.
- The end-to-end bounded query produces a result whose guarantees and
  statuses are honest (no exact label on a budget-truncated result).

### Phase 4 — Rewrite registry and proof kernel

Spec: §37.4, §25.1–25.9. Gate: **5, 16, 18**.

Scope:

- Rewrite-rule registration with the five mandatory rules (Q6):
  `sol:rewrite/push_exact_selection_through_join/v1`,
  `sol:rewrite/prune_exact_projection/v1`,
  `sol:rewrite/associate_exact_join/v1`,
  `sol:rewrite/normalize_union/v1`,
  `sol:rewrite/substitute_exact_machine_summary/v1`; plus the registered
  `sol:rewrite/push_filter_across_policy_with_disclosure_proof/v1`.
- Each rule: registered rule ID, explicit preconditions, declared
  preservation dimensions, human-readable derivation, machine-checkable
  property tests, at least one adversarial corpus case, classified
  proof/verification evidence (§25.2, §25.6).
- Proof-evidence discipline: prose alone MUST NOT justify `proven`
  (§25.6, Q5); certificates carry transcript digests.
- Rewrites spanning policy or evaluator boundaries default to
  **non-preserving** unless explicitly proven (gate condition 16;
  `QV7-07`).

Acceptance:

- Corpus cases pass: QGOLD-010, QGOLD-021; QPATH-021, QPATH-022,
  QPATH-023, QPATH-026, QPATH-034, QPATH-036, QPATH-039, QPATH-041,
  QPATH-043, QPATH-044, QPATH-045, QPATH-046. (QPATH-034/044/045/046
  were added during implementation: §37.4 requires at least one
  adversarial corpus case per mandatory rule, and the registry's
  `adversarial_corpus` references named them before they existed — the
  historical freeze report had claimed condition 18 with those dangling
  references.)
- Property tests + adversarial cases exist per mandatory rule; the
  adversarial case fails when a required precondition is removed (§36.3).
- Committed certificates (files + transcript digests) make condition 18
  checkable from the repo.

### Phase 5 — Query pathology corpus

Spec: §37.5, §36.1–36.3. Gate: **10, 11**.

Scope:

- Restructure the 69 `QRY-NNN` cases into the spec's `QGOLD-*` / `QPATH-*`
  namespaces (64 normative cases per F-1; supplemental cases retained and
  documented).
- Rewrite fixtures into canonical v0.3 AST form (Phase 2 compatibility
  layer retired).
- Deterministic diagnostics end to end (§37.5).
- Query and execution records validate against the published schemas
  (gate condition 11).

Acceptance:

- All 64 normative QGOLD/QPATH cases pass with deterministic diagnostics
  (gate condition 10).
- Corpus report committed with a fresh `report_digest`.

### Phase 6 — Materialized and bounded semantic evaluators

Spec: §37.6, §26.1–26.9. Gate: **7**.

Scope:

- One semantic evaluator end to end in materialized mode: finite input
  relation → complete evaluation key → immutable assessment object →
  assessment relation → ordinary exact query over that relation.
- Inline (bounded) mode: exact or upper-bounded candidate relation →
  tuple-preserving heuristic semantic filter → certified empty or
  sound-positive lower → certified input-derived upper.
- Deterministic evaluation key contract (universally mandatory fields per
  Q15; evaluator-specific fields declared).
- Materialization obligation and equality prohibition (§26.7, §26.8).

Acceptance:

- Corpus cases pass: QGOLD-009, QGOLD-013, QGOLD-014; QPATH-007,
  QPATH-020, QPATH-024, QPATH-025, QPATH-033, QPATH-040.
- The materialized assessment is queryable as ordinary exact data; the
  heuristic filter preserves certified sides per §13.7.1.

### Phase 7 — Machine-summary substitution

Spec: §37.7, §28.3–28.5. Gate: **9**.

Scope:

- `sol:rewrite/substitute_exact_machine_summary/v1` succeeds only for
  **proven covering queries**: answerable exactly from machine-summary
  Levels 0–2 with a matching source commit (Q18; QGOLD-005).
- Ineligible queries are rejected or fetch deeper levels; a lossy summary
  is never a covering exact view (QPATH-034).
- QV8-05 (every lower-bound tuple carries the requested supported
  membership provenance, 12.4–12.5) and the claim-context half of QV7-03
  (a rewrite cited in a claim's provenance must cover the query-required
  dimensions, 25.4.3): QPATH-013.
- Temporal commit resolution (17.1, 17.5, QV1-02): a source's latest
  commit selection MUST declare a branch or lineage, an ancestry
  relation, and a deterministic tie or conflict rule; wall-clock
  timestamp alone across divergent branches is a temporal validation
  failure (QPATH-014, assigned to this phase 2026-09-10 — the check is
  commit-identity semantics in the same domain as the Phase 7
  source-commit machinery).

Acceptance:

- Corpus cases pass: QGOLD-005; QPATH-034; QPATH-013; QPATH-014.
- Substitution is recorded with the covering proof and the source-commit
  pin.

### Phase 8 — Logical disclosure and leakage separation

Spec: §32.1–32.11. Gate: **6, 19**.

Note: the spec's §37.8 (SOL-IDX, SOL-PLAN, physical leakage profiles) is
explicitly post-gate and is **out of scope** for the freeze. This phase
covers the logical-layer gate conditions only.

Scope:

- Logical-disclosure baseline with the mandatory bucketed-cardinality
  mechanism (`QV9-03`, bucket 10–19) and the validator rules around it.
- Redaction, provenance visibility, and semantic-evaluator disclosure
  dimensions (§32.2, §32.7, §32.8).
- Logical vs physical separation: no physical side-channel equivalence is
  inferred from logical rewriting alone (gate condition 19; `QV7-09`,
  `QV9-10`).

Acceptance:

- Corpus cases pass: QGOLD-011; QPATH-005, QPATH-026, QPATH-027,
  QPATH-028, QPATH-029, QPATH-043.
- A declared logical rewrite never emits a physical non-inference claim.

### Phase 9 — Gate re-run and freeze

Spec: §44. Gate: **all 19**.

Scope:

- Full gate harness run against the committed implementation: every
  condition re-evidenced from repo artifacts (fresh digests).
- New freeze report committed (e.g. `freeze_report_v030.json`);
  `freeze_report.json` retained as historical evidence.
- On 19/19: mark v0.3.0 frozen per §44; record the freeze in the spec's
  status section and in `NEXT_STEPS_2026-09-07T0315Z.md`.

Acceptance:

- 19/19 with every cited artifact present in the repo and every digest
  recomputable from committed files.
- No open unfreeze candidates blocking the frozen version (F-1 batched or
  resolved).

## 5. Gate-condition → phase map

| Condition | Summary | Phase |
|---|---|---|
| 1 | Bound-transfer rules for every core logical operator | 1 |
| 2 | Unsupported compositions reject or downgrade | 1 |
| 3 | Canonical typed AST + canonicalization schemas | 2 |
| 4 | Substrait mapping profile documented | 2 |
| 5 | Rewrite registration, proof evidence, assurance obligations | 4 |
| 6 | Logical-disclosure baseline + validator rules | 8 |
| 7 | Semantic evaluator materialization + eval-key contracts | 6 |
| 8 | Exact evaluator over exploded RFC-SOL-0001 representation | 3 |
| 9 | Machine-summary substitution for proven covering queries | 7 |
| 10 | Mandatory golden/pathological cases pass, deterministic diagnostics | 5 |
| 11 | Query/execution records validate against published schemas | 5 |
| 12 | End-to-end bounded query with honest budget degradation | 3 |
| 13 | Structural one-sided bounds (QGOLD-013..016) | 1 |
| 14 | Bounded-result provenance: lower certification vs upper derivation vs non-exclusion | 1 |
| 15 | Stale assurance evaluates effectively as unknown | 1 |
| 16 | Policy/evaluator-boundary rewrites default non-preserving | 4 |
| 17 | `sol:bound/avg_optional_prefix/v1` golden + pathological cases | 1 |
| 18 | Rewrite kernel property tests + adversarial cases + proof artifacts | 4 |
| 19 | Logical/physical leakage claims separated | 8 |

## 6. Sequencing and dependencies

```text
Phase 1 (bound algebra) ─┬─► Phase 3 (exact evaluator) ─► Phase 4 (rewrite kernel)
Phase 2 (AST/canon) ─────┤                                    │
                         └─► Phase 6 (evaluators) ─► Phase 7 (summary substitution)
Phase 5 (corpus restructure) after Phases 1-4 (needs the new rule IDs + cases)
Phase 8 (disclosure) after Phase 4 (policy-boundary rules)
Phase 9 (gate re-run) after all of the above
```

- Phase 1 and Phase 2 are independent and can proceed in parallel.
- Phase 5 depends on Phases 1–4 because the normative QGOLD/QPATH cases
  reference the new rule IDs, bound rules, and evaluator contracts.
- Phase 9 is the only phase that changes the spec's status.

## 7. Open questions (non-blocking)

1. **F-1 resolution path.** If the unfreeze candidate is resolved as an
   erratum (spec list is the mandatory minimum), the 64-case target stands.
   If it is resolved as a spec amendment, the §36.1/§36.2 lists gain the
   supplemental cases. Either way the implementation corpus is a superset of
   the normative list.
2. **Evaluator choice for Phase 6.** One semantic evaluator end to end is
   required; the specific evaluator (e.g. a deterministic text classifier
   over record fields) is an implementation choice, not a spec question.
3. **Physical profiles (spec §37.8).** Deliberately post-gate; no action
   needed for the freeze.
