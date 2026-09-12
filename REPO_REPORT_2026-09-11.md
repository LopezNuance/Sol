# Sol Repository Report

Date: 2026-09-11 (UTC). Scope: what this repository currently contains and how
each part supports the Sol specification. Every baseline figure below was
re-verified on 2026-09-11 08:15Z-08:25Z by running the commands in §5; the
recorded digests match the committed freeze evidence.

## 1. Repository at a Glance

| Path | What it is |
|---|---|
| `Sol_RFC.md` | RFC-SOL-0001 "Sol — A Cooperative Computational Work Artifact", v0.1.0 (promoted 2026-09-08), 63 numbered sections |
| `documentation/RFC-SOL-QRY-0001-v0.3.0.md` | Companion RFC-SOL-QRY-0001 "Declarative Query Semantics for Sol", v0.3.0, **FROZEN 2026-09-11** (Revision 3), 47 numbered sections |
| `documentation/` (remainder) | Historical QRY drafts (`SOL-QRY-draft.md`, v0.2.0 design draft), the docx export of the base RFC, one unrelated challenge document |
| `sol_validator/` | Base-RFC reference validator and MVP implementation surface, 9 published JSON schemas, 37-case corpus, 12-check demo suite, repo-ready example artifact |
| `qry_reference_impl/` | QRY reference implementation: certified bound algebra, typed-AST canonicalization, exact evaluator, rewrite registry and proof kernel, semantic evaluators, logical-disclosure layer, 136-case corpus, proof certificates, 68 recorded evaluator runs, §44 gate harness, 190 unit tests |
| `docs/` | Decision notes, the 9-phase QRY implementation plan, gap records, the authoritative exploded-representation profile, acceptance criteria, errata log, internal review, both submission packages |
| `container_benchmark/` | Container benchmark that resolved base-RFC question Q1 (single-file ZIP, STORED entries) |
| `freeze_report.json` | Historical v0.1 QRY reconstruction gate report (18/19, NOT_FROZEN); retained untouched as evidence |
| `freeze_report_v030.json` | QRY v0.3.0 freeze-gate report: 19/19, status FROZEN, report digest `sha256:1ea510ee17a5…` |
| `NEXT_STEPS_2026-09-07T0315Z.md` | Master plan and status for both RFC tracks |
| `src/sol/`, `pyproject.toml`, `uv.lock`, `scripts/quality.sh`, `reports/quality/` | Project tooling and quality-report history |

The top-level `README.md` is empty (0 bytes); the operational documentation
lives in `sol_validator/README.md` and `qry_reference_impl/README.md`.

## 2. The Two Specifications

**RFC-SOL-0001 (base, v0.1.0).** Sol is a self-contained, versioned
computational work artifact in which the artifact itself is the source of
truth and rendered surfaces (HTML, Markdown, PDF, dashboards, machine
summaries) are derived views. Ten invariants (INV-01..INV-10) anchor the
model: artifact source of truth, visible execution structure, no hidden
out-of-order execution, serialized state only, outputs are derived, internal
storage of required artifacts, safe rendering, machine legibility without
rendering, attributed agency, and bounded structural reads. The spec defines
the ontology (cells, semantic records, anchor cells, actors, runs, commits,
branches, object store, rendered views), the reference grammar, a five-level
bounded read model (L0 manifest .. L4 object payloads), conformance levels,
the status model with legal transitions, container requirements
(REQ-014.1..REQ-014.5), and a V0-V5 validation catalog. v0.1.0 was promoted
from the draft freeze on 2026-09-08 carrying the errata log (E-001..E-003)
and the nine batched unfreeze candidates from the Phase 1 decisions. Twelve
post-v0.1 open questions remain in §59.

**RFC-SOL-QRY-0001 (companion, v0.3.0 FROZEN).** SOL-QRY defines a rigorous,
implementation-independent query contract over committed Sol state. It
separates four concerns: set-theoretic/model-theoretic semantics, declarative
logic, a logical algebra transformable under registered
equivalence-preserving rewrite rules, and physical execution (deliberately
outside the normative core). Its central constructs are certified
answer-bound relations $L \subseteq Q(I) \subseteq U$ with declared guarantee
kinds (`exact`, `lower_bound`, `upper_bound`, `bounded`, `heuristic`),
bound-aware provenance (lower-membership vs upper-bound derivation),
assurance with dependency-driven staleness, open/closed-world and temporal
semantics, registered semantic evaluators, and a logical-disclosure vs
physical-side-channel leakage policy. v0.3.0 passed the §44 freeze gate
19/19 on 2026-09-11 and is frozen for implementation; it does not amend or
unfreeze RFC-SOL-0001.

## 3. How the Repository Supports RFC-SOL-0001

| Spec requirement | Repository support |
|---|---|
| Artifact structure and the 9 Appendix C schema classes (§13, App C) | `sol_validator/schemas/` — all 9 classes published (v0.2 set, JSON Schema draft 2020-12) and enforced by the validator |
| Validation rules V0-V5, deterministic diagnostics | `sol_validator/solval/validate.py` — the catalog as executable checks; stable rule IDs incl. V0-07..V0-13 for schema enforcement |
| Container requirements REQ-014.1..014.5 and decision Q1 | `solval/container.py` (single-file ZIP, STORED entries, bounded reads, random object access, integrity) + `container_benchmark/` (harness + `report.json`; tar disqualified at ~21x read amplification) |
| Safe rendering, INV-07 (§47) | `solval/render.py` — HTML/Markdown from a selected commit; discloses stale/invalidated/unverified content; no scripts or event handlers |
| Executor conformance level (§12.5) | `solval/executor.py` — linear execution in committed order, partial-success prefix commits, failure records paired to the same run |
| Imported `.ipynb` classification (Q6) | `solval/import_ipynb.py` + `demos/import_demo/` |
| Change Control gate: "complete examples must validate" | `sol_validator/corpus/GOLD-01` — assembled from the RFC's own examples (§15/16/18/21-27/30/41/42/47/48) with real sha256 digests, zero diagnostics (absorbs erratum E-001) |
| Conformance corpus with exact-match diagnostics | `sol_validator/corpus/` — 37 cases (GOLD-01..06, PATH-001..031), 37/37 under `--strict-extra` |
| Acceptance criteria (§58, 25 items) | `docs/acceptance/2026-09-07-acceptance-criteria.md` + `sol_validator/demos/` (12/12 demonstration checks, `demos/manifest.json`) |
| Errata discipline | `docs/errata/RFC-SOL-0001-errata.md` (E-001..E-003) |
| Submission readiness | `docs/submission/2026-09-08-v0.1.0-submission-package.md` (frozen for the internal venue, stage 1) |

## 4. How the Repository Supports RFC-SOL-QRY-0001

| Spec section | Repository support |
|---|---|
| §13 certified answer-bound algebra | `qryref/certified.py` — certified L/U relations, guarantee kinds, transfer rules for all 16 core operators, structural one-sided containment, difference/complement/recursion, aggregate bounds incl. `sol:bound/avg_optional_prefix/v1`, assurance with stale downgrade, bound provenance, $L \subseteq U$ validation |
| §29 typed AST, canonicalization, query records | `qryref/canonical.py` (idempotent canonicalization, `digest:sha256` query digests, per-source manifests) + `schemas/qry_query.schema.json` |
| §29.2/§25.9 Substrait mapping | `substrait/qry_substrait_profile.yaml` (v0.3 normative baseline) + recorded `mapping_digest` + mapping notes |
| §30 query execution records | `qryref/exact.py`, `run_evaluator.py`, `record_runs.py` — exact scan evaluator over the authoritative exploded representation `solqry-authoritative-exploded/v1` with budget/continuations and honest completion states; `evaluator_runs/` holds 68 committed runs (all complete/exact) plus the gate-12 budget-degradation demo |
| §25 registered rewrite rules and proof discipline | `qryref/rewrites.py` (7-rule registry: 5 mandatory + policy-boundary + experimental, with the §25.4 application kernel), `property_tests.py` (seeded property tests), `certificates/rewrites/` (5 property certificates, the disclosure proof, 3 committed covering proofs, registry report — 10/10 verified), `rewrites/*.md` (human-readable derivations) |
| §26 semantic evaluators | `qryref/evaluators.py` + `v3_semantic.py` — materialized and bounded modes, deterministic evaluation key, materialization obligation, equality prohibition |
| §32 authorization, redaction, leakage | `qryref/disclosure.py` — mandatory bucketed-cardinality mechanism (reference partition `["0", "1-9", "10-19", "20-99", "100+"]`), provenance visibility, verbose-denial and non-inference-claim checks; logical/physical separation of gate 19 |
| §34/§35 conformance roles and validation rules | `qryref/rules.py` — 55-rule validator catalog (QRY-SEM/BOUND/CERT/SUBSTRAIT + the spec's QV*/QINV* rules); `validate.py` / `validate_corpus.py` |
| §36 query pathology corpus | `corpus/` — all 64 normative cases (QGOLD-001..021, QPATH-001..043) plus 72 supplemental (3 out-of-spec adversarial QPATH-044..046 + 69 legacy `QRY-NNN` cases), 136/136 with deterministic diagnostics; report `corpus/report.json` |
| §37 reference implementation order | `docs/qry/2026-09-08-v03-implementation-plan.md` — 9 phases, all COMPLETE (2026-09-08..11), with per-phase evidence |
| §44 v0.3 freeze gate | `qryref/gate_check.py` — re-evidences all 19 conditions from committed artifacts with fresh digests; `freeze_report_v030.json` records 19/19, FROZEN |
| Gate condition 8 (authoritative exploded representation) | `docs/profiles/exploded-representation-profile.{md,json}` — profile `solqry-authoritative-exploded/v1` designated over `corpus/` and `sol_validator/corpus/` |

Unit tests: 190 (`qry_reference_impl/tests/`), covering every transfer rule,
canonicalization stability, the exact evaluator, the rewrite kernel, the
evaluator contracts, the disclosure layer, and corpus regressions.

## 5. Verification (all re-run 2026-09-11)

Run with `/usr/bin/python3` (3.14.4); the repo `.venv` lacks `jsonschema`.

| Command (cwd) | Result |
|---|---|
| `/usr/bin/python3 -m pytest -q` (`qry_reference_impl/`) | 190 passed |
| `/usr/bin/python3 -m qryref.validate_corpus corpus` (`qry_reference_impl/`) | 136/136 (64 normative + 72 supplemental); report digest `sha256:3855d1c452fa…` |
| `/usr/bin/python3 -m qryref.check_certificate` (`qry_reference_impl/`) | 10/10 verified |
| `/usr/bin/python3 -m qryref.gate_check` (`qry_reference_impl/`) | 19/19, status FROZEN; report digest `sha256:1ea510ee17a5…` |
| `/usr/bin/python3 -m solval.validate_corpus corpus --strict-extra` (`sol_validator/`) | 37/37 |
| `/usr/bin/python3 -m solval.mvp_demo` (`sol_validator/`) | 12/12 |
| `git diff --check` (repo root) | clean |

Digest discipline: recorded report digests are the sha256 of the canonical
JSON serialization of the report content (digest field excluded), not of the
raw file bytes. The gate harness recomputes every digest from the committed
files, so any drift in a cited artifact breaks the 19/19 result. The
historical `freeze_report.json` (v0.1 reconstruction, 18/19, NOT_FROZEN)
cited out-of-repo paths; it is retained untouched as evidence of the
reproducibility gap that the v0.3.0 gate run closed.

## 6. Decision and Documentation Trail

- `NEXT_STEPS_2026-09-07T0315Z.md` — master plan: base-RFC Phases 0-5 all
  CLOSED; QRY companion items 1-5 all DONE (profile publication,
  reconstruction moved into the repo, 20 blocking questions resolved,
  Option-3 freeze to 19/19, submission relationship).
- `docs/decisions/` — venue (internal now, public spec next, IETF-style
  final), the 11 v0.1-blocking questions, the 20 QRY v0.3-blocking
  questions, and the QRY submission relationship (separate companion RFC,
  submitted alongside the base RFC at stage 2).
- `docs/qry/` — 9-phase implementation plan (all phases COMPLETE with
  evidence), the Phase 5 corpus-gap record (no blocked cases remain), and
  the reproducibility-gap record (resolved by the v0.3.0 gate run).
- `docs/submission/` — both frozen submission packages (base v0.1.0, QRY
  v0.3.0), each an end-to-end reviewer inventory: frozen spec, normative
  artifacts, executable support, decision trail, verification commands.
- `docs/reviews/2026-09-08-v0.1.0-internal-review.md` — venue stage-1
  internal review with all findings triaged (no unfreeze candidates).

## 7. Current State and Open Items

- Both specifications are frozen for implementation: base RFC v0.1.0
  (2026-09-08) and QRY v0.3.0 (2026-09-11). Both submission packages are
  frozen for the public-spec stage (stage 2 of 3).
- Owner-driven next step (external process, not repo work): venue stage 2 —
  namespace/trademark review, IANA media-type registration for
  `application/vnd.sol.notebook`, and a public comment cycle for both RFCs.
- Post-freeze candidates, each needing its own plan before starting: spec
  §37.8 (SOL-IDX/SOL-PLAN physical indexes, statistics, and physical
  side-channel conformance profiles — explicitly out of the v0.3.0 freeze
  scope); the 12 base-track post-v0.1 open questions (`Sol_RFC.md` §59);
  and the companion family (SOL-IDX/PLAN/MEM/SEM/FED/PRIV) as separate
  future RFCs.
- Housekeeping observations: the top-level `README.md` is empty;
  `qry_reference_impl.zip` (2026-09-08) is a stale snapshot of the
  reference implementation and should not be treated as current; the
  working tree carries uncommitted work (including the QRY implementation
  tree) and has not been committed, per the project's working practice.
