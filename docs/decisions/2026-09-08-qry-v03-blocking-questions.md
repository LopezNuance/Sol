# Decisions: RFC-SOL-QRY-0001 §43.1 v0.3-blocking open questions

Date: 2026-09-08 (UTC)
Status: Decided — all 20 v0.3-blocking questions resolved
Subject: `documentation/RFC-SOL-QRY-0001-v0.3.0.md` §43.1

The v0.3.0 design draft is a complete normative specification; each blocking
question below is resolved by the draft's own normative text. These decisions
record the resolution and its landing section so the questions can be closed
out of §43.1. None of these decisions amends RFC-SOL-0001 or the v0.3.0 draft;
they fix the open-question list against the published draft text.

Change-control note: per §44 of the v0.3.0 draft, findings during the frozen
implementation period are triaged as errata / corpus entry / unfreeze
candidate. These 20 resolutions are spec-completeness closures, not
implementation findings.

## Summary

| Q | Decision (one line) | Landing |
|---|---|---|
| 1 | §10.1 snapshot-schema relations are the mandatory normalized base relations; §10.2 history schema for historical queries | §10.1, §10.2 |
| 2 | JSON Schema (draft 2020-12) catalog over the §8.1 many-sorted domains and §8.2 parameterized reference types | §8, §10 |
| 3 | Typed JSON AST, deterministically canonicalized + hashed; Substrait mapping SHOULD, not normative | §19.1, §29.2, §29.4, §25.9 |
| 4 | Lower/upper as content-addressed object refs; exact results use `lower_object = upper_object = result_object`; unavailable sides explicit | §13.3, §13.4, §13.5 |
| 5 | Baseline proof vocabulary (mechanized_proof … contract_assertion); prose alone never supports `proven` | §25.6 |
| 6 | Mandatory kernel = the five registered rewrite rules (selection pushdown, projection pruning, join associativity, union normalization, machine-summary substitution) | §37.4, freeze report |
| 7 | Minimum lower-membership provenance mode is `tuple` | §12.5 |
| 8 | Upper-bound derivation fields per §12.6 (input relations, rule ID, sources/commits, contexts, evaluators, view substitutions, rewrites) | §12.6 |
| 9 | Local completeness assertion identifies relation, predicate region, source commits, visibility policy, valid-time interval, supporting actor/verification, staleness | §16.8 |
| 10 | Minimum valid-time model is a `valid_from`/`valid_to` interval; combined queries use AT COMMIT + VALID AT | §17.2, §17.3 |
| 11 | Query execution MAY reuse the Sol run model or a registered query-run subtype; reference uses the registered subtype | §30 |
| 12 | Result object is a content-addressed object referenced by `guarantee.result_object`; kind is SET/BAG/SEQUENCE; completion states per §30.2 | §30, §11.4, §13.4 |
| 13 | Minimum logical-disclosure profile enforces disclosure for values, tuple existence, cardinality, provenance, diagnostics, errors; no general non-inference claim without a conforming profile | QINV-12, QV9-02..08 |
| 14 | No physical side-channel profile is mandatory for a baseline service; `not_claimed` by default; deferred to SOL-PRIV | QINV-12, §25.3, §37.8 |
| 15 | Universal key fields: evaluator contract ID, source commit, input digests, the four policies, output schema; model/config/prompt/tool-policy/seed/service-version are evaluator-specific | §26.5 |
| 16 | No additional mandatory aggregate-bound rules beyond COUNT_SET, SUM, MIN, MAX, `sol:bound/avg_optional_prefix/v1`; medians/percentiles/rank/top-k deferred | §13.11–13.14 |
| 17 | `proven` ← mechanized_proof/checked_certificate/formal_derivation; `validated`/`tested` ← property_test/adversarial_corpus/exhaustive_finite_check; `contract_asserted` ← contract_assertion; `unknown` ← stale deps | §13.3, §25.6 |
| 18 | First exact substitution rule is eligible when the query is answerable exactly from Levels 0–2 of the machine summary with a matching source commit; sufficient fields per RFC-SOL-0001 §48 / machine_summary schema | QGOLD-005, §37.7, base §48 |
| 19 | Reference syntax `sol:<category>/<slug>/v<N>` (rewrite/bound/evaluator); policies `policy:<name>`; corpus `QGOLD-*`/`QPATH-*` | §25.2, §13.14, §26.5 |
| 20 | Mandatory corpus = the 69 golden/pathological cases recorded in the freeze report, with ≥1 adversarial case per mandatory rewrite rule | §36.1–36.3, §44, freeze report |

## Detail

### Q1. What exact normalized base relations are mandatory?

**Decision.** The mandatory normalized base relations are the §10.1 snapshot
schema: `Artifact`, `ManifestFeature`, `Cell`, `CellDependency`,
`LinearCellPosition`, `ExecutionNode`, `ExecutionEdge`, `Record`,
`RecordStatus`, `RecordDependency`, `Claim`, `Evidence`, `Supports`, `Decision`,
`DecisionCandidate`, `DecisionBasis`, `Proposal`, `Review`, `Verification`,
`Failure`, `Actor`, `Run`, `RunCell`, `OutputContract`, `OutputBinding`,
`Object`, `ProvenanceInput`, `ProvenanceOutput`, `Render`, `Diagnostic`,
`Branch`, `Signature`. The §10.2 history schema is mandatory for historical
queries. A conforming implementation MAY expose additional registered
relations. Normalization follows §10.3 (no repeated arrays as indivisible
values) and §10.4 (ordinals where order is meaningful).

### Q2. What canonical schema language defines relation and type catalogs?

**Decision.** JSON Schema (draft 2020-12), consistent with the
RFC-SOL-0001 published schema set. The relation and type catalogs are JSON
Schema catalogs over the §8.1 many-sorted domains (`ArtifactId`, `CommitId`,
…, `JSON`) and the §8.2 parameterized reference types (`Ref<Cell>`,
`Ref<Record>`, …). Cross-type equality is prohibited (§8.1); scalar equality is
within-type (§8.3).

### Q3. What exact AST encoding and Substrait mapping are required?

**Decision.** The canonical interchange form is a typed AST, JSON-encoded
(§19.1), with deterministic canonicalization and hashing (§29.4: the query
digest covers the canonical expression, parameter types and bound values,
source manifest, semantic modes, result schema, evaluator-contract
identities, the four policies, required guarantee, and required equivalence
dimensions). Standard relational nodes SHOULD map to Substrait concepts and
Sol-specific semantics are declared extensions (§29.2); Substrait and Calcite
are not normative dependencies (§25.9). Unknown required extensions MUST fail
validation (§29.5).

### Q4. How are lower and upper relation objects serialized efficiently?

**Decision.** Lower and upper relations are serialized as content-addressed
object references (`object:sha256:...`) carried by the guarantee record
(§13.3). When `L = U = R`, a single result object is serialized with the
canonical shorthand `lower_object = upper_object = result_object` (§13.4). An
unavailable side is represented explicitly, never synthesized from an
arbitrary finite universe (§13.5).

### Q5. What proof artifact formats qualify as mechanized proofs, checked certificates, or accepted formal derivations?

**Decision.** The baseline proof-evidence vocabulary is `mechanized_proof`,
`checked_certificate`, `formal_derivation`, `exhaustive_finite_check`,
`property_test`, `adversarial_corpus`, `contract_assertion` (§25.6).
`mechanized_proof`, `checked_certificate`, or a profile-accepted
`formal_derivation` MAY support `proven` assurance; `property_test`,
`adversarial_corpus`, and `exhaustive_finite_check` support `tested` or
profile-defined `validated`; `contract_assertion` supports `contract_asserted`.
A prose `proof_reference` alone MUST NOT justify `proven`.

### Q6. Which rewrite rules are mandatory for baseline optimizer conformance?

**Decision.** The mandatory baseline kernel is the five registered rewrite
rules: `sol:rewrite/push_exact_selection_through_join/v1`,
`sol:rewrite/prune_exact_projection/v1`,
`sol:rewrite/associate_exact_join/v1`, `sol:rewrite/normalize_union/v1`, and
`sol:rewrite/substitute_exact_machine_summary/v1` (§37.4; freeze report
condition 5 `mandatory_rules`). Each MUST carry a registered rule ID, explicit
preconditions, declared preservation dimensions, a human-readable derivation,
machine-checkable property tests, at least one adversarial corpus case, and
classified proof/verification evidence (§25.2, §25.6, §36.3).

### Q7. What is the minimum lower-membership provenance mode?

**Decision.** The minimum lower-membership provenance mode is `tuple`
(§12.5): it identifies the certified lower tuples `t ∈ L`. The stronger modes
`why`, `how`, and `full_graph` are optional and explain why a tuple is
certified to belong to the exact relation.

### Q8. What exact upper-bound derivation fields are mandatory?

**Decision.** Upper-bound derivation provenance MUST be able to record how the
upper relation was certified as an envelope, and SHOULD identify: the input
upper/lower relations used by the transfer rule; the normative or registered
transfer-rule ID; source manifests and commits; temporal, visibility,
authorization, and leakage contexts; semantic evaluators and evaluator
guarantees; view substitutions; and rewrite-rule applications (§12.6). This
establishes `R ⊆ U` without establishing `t ∈ R` for every `t ∈ U`.

### Q9. What exact semantics should local completeness assertions use?

**Decision.** A completeness assertion SHOULD identify: the relation; the
predicate region for which it is complete; the source commits; the visibility
policy; the valid-time interval; the actor or verification that supports it;
and its staleness state (§16.8). Negation MAY rely on a local completeness
assertion rather than requiring the entire relation to be globally closed.

### Q10. What minimum valid-time model is required?

**Decision.** The minimum valid-time model is a `valid_from`/`valid_to`
interval (or another registered interval representation) on temporal semantic
records (§17.2). A combined query specifies both artifact-time and valid-time
(`AT COMMIT <c>` + `VALID AT <instant>`, §17.3). Lower and upper relations
MUST be evaluated under the same artifact-time and valid-time context (§17.6).

### Q11. Should query executions reuse `run` directly or use a registered subtype?

**Decision.** Both are permitted: a query execution MAY reuse the Sol run
model or use a registered query-run subtype (§30). The reference
implementation uses the registered query-run subtype (`query_run_*`) carrying
`query_ref`, `query_digest`, `source_manifest`, `actor_id`, `guarantee`,
`assurance` (with `effective_status` after staleness), `provenance_mode`,
completion state, `resource_usage`, and `logical_rewrites` (§30). Continuation
tokens bind to the same query digest, source manifest, policies, evaluator
identities, and partial-result state (§30.3).

### Q12. What exact result-object format is required?

**Decision.** The result object is a content-addressed object
(`object:sha256:...`) referenced by `guarantee.result_object` in the query
execution record (§30). The result declares a kind — `SET<T>`, `BAG<T>`, or
`SEQUENCE<T>` (§11.4). Exact results use the `lower_object = upper_object =
result_object` shorthand (§13.4). Completion states are `complete`,
`incomplete_with_continuation`, `failed`, `cancelled` (§30.2); an incomplete
result MUST NOT carry the `exact` guarantee for the complete query unless the
evaluator proves omitted work cannot affect the result.

### Q13. What minimum logical-disclosure policy profile is mandatory?

**Decision.** The minimum logical-disclosure policy profile declares and
enforces disclosure for values, tuple existence, cardinality, provenance,
diagnostics, and errors (QINV-12; QV9-02 through QV9-05 and QV9-07). A query
service MUST enforce the declared logical-disclosure policy and MUST NOT claim
general non-inference unless a profile explicitly defines and verifies that
property (QV9-08).

### Q14. Which physical side-channel profile, if any, is mandatory for a baseline service?

**Decision.** No physical side-channel profile is mandatory for a baseline
service. `physical_side_channel_class` MAY be claimed only under a physical
conformance profile that defines observables and operator implementations; a
logical rule alone ordinarily leaves this dimension `not_claimed` (§25.3,
QINV-12). Physical side-channel conformance profiles are deferred to the
SOL-PRIV companion specification (§37.8 Phase 8).

### Q15. Which evaluation-key fields are universally mandatory versus evaluator-specific?

**Decision.** Universally mandatory in the evaluation key: evaluator contract
ID, source commit, input object/tuple digests, visibility/authorization/
leakage/assessment policies, and output schema. Evaluator-specific (SHOULD):
model identity and version, configuration digest, prompt-template digest,
tool-policy digest, random seed or sampling identity, and external service
version (§26.5). All logically repeated invocations with the same key MUST
resolve to the same immutable result object.

### Q16. Which aggregate-bound rules are mandatory beyond COUNT_SET, SUM, MIN, MAX, and optional-prefix AVG?

**Decision.** None additional are mandatory for the v0.3 baseline. The
mandatory aggregate-bound rules are `COUNT_SET` (§13.11), `SUM` (§13.12),
`MIN`/`MAX` (§13.13), and `sol:bound/avg_optional_prefix/v1` (§13.14).
Medians, percentiles, rank, and top-k remain subject to their own registered
rules and are not part of baseline v0.3 conformance.

### Q17. Which evidence forms are sufficient for each assurance status under the baseline profile?

**Decision.** `proven` ← `mechanized_proof`, `checked_certificate`, or a
profile-accepted `formal_derivation`. `validated` ← `property_test`,
`adversarial_corpus`, or `exhaustive_finite_check` under a declared validation
profile. `tested` ← `property_test`, `adversarial_corpus`, or
`exhaustive_finite_check`. `contract_asserted` ← `contract_assertion`.
`unknown` ← stale or unverifiable assurance dependencies (effective assurance
downgrades to `unknown` until current verification is established, §13.3).
Prose without a checked derivation MUST NOT support `proven` (§25.6).

### Q18. Which machine-summary fields are sufficient for the first exact substitution rules?

**Decision.** The first exact substitution rule,
`sol:rewrite/substitute_exact_machine_summary/v1`, is eligible when the query
is answerable exactly from Levels 0–2 of the machine summary with a matching
source commit (QGOLD-005; §37.7). The sufficient machine-summary fields are
those published in RFC-SOL-0001 §48 and the machine-summary schema: identity
and source-commit pinning, `execution_structure`, `cells`, `actors`, `records`
(with full status blocks), `runs`, `failures`, `diagnostics`,
`open_proposals`, `stale`, and `renders`. Ineligible queries are rejected or
fetch deeper levels.

### Q19. What reference syntax identifies rewrite rules, bound rules, evaluators, and policies?

**Decision.** The reference syntax is `sol:<category>/<slug>/v<N>`: rewrite
rules `sol:rewrite/<slug>/v<N>` (§25.2), bound rules `sol:bound/<slug>/v<N>`
(§13.14), evaluators `sol:evaluator/<slug>/v<N>` (§26.5). Policies use
`policy:<name>`. Corpus cases use the `QGOLD-*` and `QPATH-*` namespaces;
other namespaces MUST be registered explicitly before use (§25.2).

### Q20. Which golden and pathological cases are mandatory before freeze?

**Decision.** The mandatory corpus is the 69 golden/pathological cases
recorded in the freeze report (QGOLD-001 through QGOLD-020 and the QPATH set),
which must pass with deterministic diagnostics (freeze report condition 10;
§36.1, §36.2). Every mandatory rewrite rule MUST have at least one adversarial
corpus case that fails when a required precondition is removed (§36.3).
Deterministic diagnostics: same source + same query → same diagnostics → same
ordering (§37.5).
