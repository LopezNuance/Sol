# RFC-SOL-QRY-0001: Declarative Query Semantics for Sol

## Status

**v0.3.0-design-draft — Revision 3**

This document is a proposed companion specification to **RFC-SOL-0001: Sol — A Cooperative Computational Work Artifact**, whose v0.1.0 draft is frozen for implementation. This document does not amend or unfreeze RFC-SOL-0001.

SOL-QRY is not ready for semantic freeze. The v0.3 freeze gate is defined in §44.

Normative terms such as **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used in the sense of RFC 2119 and RFC 8174 when, and only when, they appear in uppercase.

---

## Change Summary from v0.2 Design Draft

Revision 3 is a targeted semantic erratum pass over Revision 2. It preserves the Revision 2 architecture and incorporates the second external review as normative, testable structure.

Revision 3 adds or clarifies:

1. **Structural one-sided answer bounds.** Tuple-preserving filters, intersections, differences, unions, and other containment-declared operators may retain certified lower or upper sides even when another predicate or operand is heuristic. A heuristic contribution invalidates only the bound sides that depend on it; it does not force a blanket downgrade when operator containment independently proves a side.
2. **Bound-aware provenance.** Ordinary tuple-membership provenance applies to the certified lower relation. Upper relations carry bound-derivation provenance. Tuples in `U \ L` are unexcluded candidates, not positively proven members of the exact answer.
3. **Validity versus tightness.** Normative transfer rules establish valid baseline bounds, not necessarily globally tight bounds. Registered rules may produce tighter bounds when their proof obligations are satisfied.
4. **Logical disclosure versus physical side channels.** Rewrite conformance now distinguishes value, existence, cardinality, error, and provenance disclosure from timing, resource use, access paths, and evaluator invocation counts. Rewrites crossing policy or evaluator boundaries are non-preserving by default unless explicitly proven.
5. **Assurance dependency and staleness.** Assurance records inherit RFC-SOL-0001 dependency-driven staleness. Stale or unverifiable proof evidence reduces effective assurance to `unknown` until reverification.
6. **Proof-evidence discipline.** Rewrite rules classify mechanized proofs, checked certificates, formal derivations, finite checks, property tests, adversarial corpus cases, and contract assertions. Tests alone do not justify `proven` assurance.
7. **Certified `AVG` intervals.** The registered rule `sol:bound/avg_optional_prefix/v1` computes extremal averages over finite exact-valued lower and upper sets by sorting optional tuples and evaluating prefixes.
8. **Corpus and freeze-gate expansion.** New golden and pathological cases cover one-sided semantic filters, stratified bounds, upper-bound provenance, stale assurance, policy-boundary rewrites, tuple-generating evaluators, tighter valid bounds, and certified `AVG` intervals.

Revision 3 also corrects the rewrite-corpus identifier namespace and removes the informal word “useful” from guarantee-kind definitions.

---

## Abstract

Sol defines a self-contained, versioned computational work artifact whose structured state is canonical and whose rendered surfaces are derived. It provides stable identities for cells, semantic records, objects, runs, commits, branches, actors, and outputs; it also defines provenance, staleness, verification, internal history, and bounded structural reads.

This document proposes **SOL-QRY**, a declarative query model over committed Sol state.

The design separates four concerns:

1. **Set-theoretic and model-theoretic semantics** define what data exists and what a query result means.
2. **Declarative logic** defines which tuples belong to a result without prescribing an access path.
3. **Logical algebra** provides a compositional representation that can be transformed under registered, semantics-preserving rewrite rules.
4. **Physical execution** chooses scans, indexes, graph traversals, materialized views, paging, caching, semantic evaluators, and model calls. Physical execution is intentionally outside the normative core of SOL-QRY.

The central rule is:

> Set-theoretic semantics defines the answer. Logic defines the requested relation. Logical algebra enables registered equivalence-preserving transformation. Physical execution determines compute and I/O cost.

SOL-QRY uses exact set semantics by default, explicit bag and sequence semantics where required, commit-pinned source snapshots, typed references, provenance-preserving evaluation, explicit open-world and closed-world assumptions, safe negation, temporal semantics, and declared answer guarantees. Learned or LLM-based semantic evaluations are modeled as attributed, typed computations that produce inspectable relations; they do not silently redefine equality or truth.

For approximate or budget-limited execution, SOL-QRY represents a relation by certified lower and upper bounds:

\[
L \subseteq Q(I) \subseteq U
\]

Certified sides may survive heuristic suboperations when structural containment proves them. Provenance distinguishes certified membership in `L` from construction of `U`; a tuple occurring only in `U` remains unexcluded rather than proven.

A physical plan may be slower, faster, exact, or approximate. It may not misrepresent its relationship to the query denotation.

---

# 1. Purpose

The purpose of SOL-QRY is to define a rigorous, implementation-independent query contract for Sol artifacts.

A conforming query system should be able to answer questions such as:

- Which claims are current, verified, and supported by current evidence?
- Which decisions depend on claims that need reverification?
- Which outputs were produced by a particular actor under a particular environment?
- Which records became stale after a given commit?
- Which cells are reachable downstream from a changed configuration cell?
- Which named outputs resolve to objects produced by valid runs at a selected commit?
- Which results can be answered from a machine summary without loading large object payloads?
- Which assertions are recorded, which are supported, and which are accepted as facts under an explicit assessment policy?
- Which answers are exact, bounded, heuristic, or incomplete under a declared execution budget?

SOL-QRY is not a storage format, index format, page manager, vector-search protocol, agent orchestration language, or mutation language. It defines the logical meaning that those systems must preserve.

---

# 2. Relationship to RFC-SOL-0001

RFC-SOL-0001 provides the substrate required for a database-style query layer:

- the artifact is the canonical computational record;
- rendered views are derived from committed state;
- semantic records are independently addressable and separate from narrative placement;
- named outputs are distinct from immutable object identities;
- execution operates against committed snapshots;
- outputs, claims, evidence, decisions, and verification have explicit dependencies;
- staleness propagates through those dependencies;
- machine summaries support bounded-context consumption;
- containers must support bounded structural reads and random object access.

SOL-QRY treats those artifact structures as a logical database instance.

The physical `.solnb` representation does not need to be relational. A conforming implementation may store Sol state in an embedded database, indexed package, content-addressed object graph, document store, or another representation. SOL-QRY defines a normalized logical projection over that state.

This specification preserves the RFC-SOL-0001 distinctions between:

- canonical structured state and derived rendering;
- logical named outputs and concrete immutable objects;
- authored output contracts and run-level output bindings;
- artifact history order and wall-clock timestamps;
- semantic records and cells that merely anchor them into narrative flow.

---

# 3. Scope

## 3.1 In scope

SOL-QRY defines:

1. a typed universe of Sol values and references;
2. a commit-pinned source model;
3. a normalized logical schema over committed artifact state;
4. set, bag, and sequence result semantics;
5. exact identity and equality rules;
6. missing, unknown, redacted, unavailable, and unresolved states;
7. artifact-assertion semantics and optional world-assessment semantics;
8. open-world and closed-world declarations;
9. artifact time and valid time;
10. declarative relational-calculus semantics;
11. a finite, domain-independent expressiveness profile;
12. positive recursion and stratified negation;
13. exact aggregation semantics;
14. a canonical logical-algebra representation;
15. registered rewrite rules and proof obligations;
16. provenance and annotation modes;
17. semantic-evaluator contracts and materialized assessments;
18. certified lower and upper answer bounds, including structural one-sided bounds;
19. lower-membership provenance and upper-bound derivation provenance;
20. assurance evidence, assurance dependencies, and staleness;
21. execution budgets and answer guarantees;
22. exact and registered aggregate-bound rules, including finite-set `AVG` intervals;
23. logical and materialized views;
24. canonical query and query-result records;
25. authorization, redaction, logical disclosure, and physical side-channel policies;
26. conformance requirements for readers, compilers, evaluators, optimizers, and validators.

## 3.2 Out of scope

The following belong in companion specifications:

- physical index layouts;
- statistics and cardinality estimation;
- cost-based optimization;
- physical join algorithms;
- page formats and buffer-pool management;
- GPU, CPU, or storage residency policy;
- distributed query scheduling;
- semantic model selection;
- automatic entity-resolution policy;
- mutation statements;
- transaction commit mechanics beyond reuse of Sol commits;
- global cross-artifact catalog administration;
- general-purpose differential privacy;
- unrestricted probabilistic-database semantics.

---

# 4. Architectural Layers

SOL-QRY adopts the following stack:

```text
Set theory and model theory
          ↓
Declarative relational query
          ↓
Logical relational algebra
          ↓
Registered equivalence-preserving rewrites
          ↓
Physical execution plan
          ↓
Indexes, scans, graphs, paging, caches, objects, and model calls
```

The upper layers define meaning. The lower layers define cost.

A larger artifact or federated source is not expected to execute with the same latency as a smaller resident source. Paging, indexing, and materialized views are capacity and performance mechanisms, not semantic mechanisms. A query remains the same query whether it is answered by an index lookup, a full scan, a graph walk, a cached summary, or a semantic evaluator.

A system MAY trade compute, I/O, latency, or completeness under an explicit budget. It MUST NOT silently change the query’s denotation.

---

# 5. Core Invariants

## QINV-01: Denotation before execution

Every conforming query MUST have a mathematical result independent of the selected physical access path.

An implementation MUST NOT define the meaning of a query as “whatever the retriever happened to return.”

## QINV-02: Pinned source state

Every artifact source MUST resolve to a specific commit before evaluation begins.

A branch name MAY be supplied by a caller, but the evaluator MUST atomically resolve it to a commit and MUST record that commit in the query execution record.

## QINV-03: Set semantics by default

Canonical relations and query results MUST use set semantics unless bag or sequence semantics are explicitly requested.

## QINV-04: Exact identity

The equality operator `=` MUST mean exact typed scalar equality or exact typed identity.

Semantic similarity, likely co-reference, paraphrase, contradiction, or conceptual equivalence MUST NOT be interpreted as equality unless explicitly represented by a relation produced under a declared evaluator or policy.

## QINV-05: Epistemic orthogonality

The following dimensions MUST remain distinct:

- tuple existence;
- assertion existence;
- world truth;
- evidence support;
- verification status;
- staleness;
- availability;
- confidence;
- authorization visibility.

For example, `unverified` MUST NOT be interpreted as false, and `stale` MUST NOT be interpreted as historically false.

## QINV-06: No silent approximation

A result that may omit valid answers or include invalid answers MUST NOT be labeled exact.

## QINV-07: Provenance-preserving evaluation

A result requested with provenance MUST be able to identify the base tuples, records, objects, evaluations, views, and source commits from which it was derived.

## QINV-08: Semantic evaluation is recorded work

An LLM, embedding model, classifier, reranker, or other learned evaluator MUST be represented as an attributed typed computation. Its result MUST be representable as immutable data.

## QINV-09: Safe negation

Classical negation and set difference MUST be used only where the relevant relation is declared complete under the selected snapshot, visibility, authorization, leakage, and assessment policies, or where a certified lower/upper-bound rule establishes a valid result.

## QINV-10: Read-only query semantics

SOL-QRY derives relations. It MUST NOT directly mutate canonical artifact state.

A query result MAY be used to construct a proposal, execution request, verification request, or other Sol operation, but mutation remains governed by Sol authorization, review, execution, and commit semantics.

## QINV-11: Registered rewrite discipline

A conforming optimizer MUST apply only registered rewrite rules whose preconditions are satisfied and whose declared preservation contract covers the query’s required equivalence dimensions.

Implementations are not required or expected to decide arbitrary query equivalence.

## QINV-12: Declared leakage contract

A query service MUST enforce the declared logical-disclosure policy for values, tuple existence, cardinality, provenance, diagnostics, and errors. It MUST enforce any declared physical side-channel profile for execution metadata. It MUST NOT claim general non-inference unless a profile explicitly defines and verifies that property.

## QINV-13: Stable semantic assessments

A semantic evaluation used inside a rewritable plan MUST either:

1. reference a previously materialized immutable assessment relation; or
2. provide a complete deterministic evaluation-key contract under which logically repeated invocations resolve to the same immutable result.

A transient cache alone does not satisfy this invariant.

## QINV-14: Bound-provenance honesty

A tuple in a certified lower relation MAY be represented as proven to belong to the exact answer.

A tuple occurring only in a certified upper relation MUST NOT be represented as proven exact-answer membership. Its metadata may explain why it has not been excluded or how the upper bound was constructed, but that metadata is not ordinary positive why-provenance.

## QINV-15: Conservative policy boundaries

A logical rewrite that crosses, removes, duplicates, reorders, or fuses a visibility, authorization, leakage, error-masking, or semantic-evaluator boundary is non-preserving by default. It MAY be applied only when a registered rule explicitly establishes the required logical-disclosure properties. Physical side-channel preservation requires a separate physical conformance profile.

---

# 6. Expressiveness Profile

## 6.1 Core v0.3 profile

The normative v0.3 core is:

```text
function-free
many-sorted and typed
range-restricted
finite active domain
set semantics by default
positive recursive Datalog
stratified negation
nonrecursive stratified aggregation
no recursion through aggregation
fixed query arity
bounded predicate arity
```

A query outside this profile MAY be accepted by an extension, but the extension MUST declare its semantics, termination conditions, and guarantee rules.

## 6.2 Data complexity

For a fixed query in the core profile, evaluation is intended to remain within polynomial data complexity. This statement applies to the exact logical fragment, not to arbitrary semantic evaluators or physical optimization problems.

## 6.3 Excluded core features

The following are not part of the core profile:

- unrestricted function symbols;
- unbounded value invention;
- recursion through negation;
- recursion through aggregation;
- arbitrary second-order quantification;
- unrestricted probabilistic inference;
- arbitrary natural-language query semantics;
- general query-equivalence decision procedures.

---

# 7. Terminology

## Query source

A commit-pinned Sol artifact included in a query evaluation.

## Source manifest

The immutable list of artifact and commit coordinates used by one evaluation.

## Database instance

The logical set of relations denoted by committed Sol state under a source manifest.

## Base relation

A logical relation directly projected from committed artifact state.

## Derived relation

A relation defined by a query over base or other derived relations.

## Logical view

A named query whose result is derived when referenced.

## Materialized view

A stored result of a named query, tied to source commits, dependencies, freshness state, query identity, provenance, and answer guarantee.

## Assertion

A record that an actor, tool, or process has stated or represented a proposition.

## Accepted fact

A proposition regarded as true under an explicit assessment policy. An accepted fact is not the same as a stored claim record.

## Exact denotation

The mathematical relation `Q(I)` defined by query `Q` over database instance `I`.

## Certified lower bound

A relation `L` proven or contractually established to satisfy:

\[
L \subseteq Q(I)
\]

## Certified upper bound

A relation `U` proven or contractually established to satisfy:

\[
Q(I) \subseteq U
\]

## Answer guarantee

A formal relationship between a returned result and the exact denotation.

## Assurance

Evidence supporting an answer-guarantee claim, such as a proof, validator result, evaluator contract, test record, or unaudited assertion.

## Assurance dependency

A record, object, evaluator contract, source commit, proof artifact, verification, policy, or test result whose current validity is required by an assurance claim.

## Lower-membership provenance

Provenance explaining why a tuple is certified to belong to the exact answer. In a bounded result, this applies to tuples in the lower relation.

## Upper-bound derivation provenance

Provenance explaining how a certified upper relation was constructed, including its source bounds, transfer rules, policies, views, evaluators, and rewrites. It does not prove that each tuple in the upper relation belongs to the exact answer.

## Bound tightness

The degree to which a valid lower bound is large and a valid upper bound is small. Validity is normative. Global tightness is not required unless a rule contract explicitly claims it.

## Semantic evaluator

A typed computation that applies learned, probabilistic, heuristic, or human judgment and emits structured assessment tuples.

## Rewrite rule

A registered transformation from one logical expression pattern to another, with declared preconditions, preservation properties, and proof or verification evidence.

## Leakage policy

A policy specifying what information may be disclosed through values, tuple existence, cardinality, provenance, diagnostics, timing, and other execution metadata.

## Logical disclosure behavior

Information exposed by the logical result contract, including values, tuple existence, cardinality, diagnostics, errors, provenance identities, and policy-visible evaluator results.

## Physical side-channel class

Information exposed by a physical realization, including timing, resource use, access paths, cache behavior, storage reads, and evaluator invocation counts.

---

# 8. Typed Universe

## 8.1 Many-sorted domains

SOL-QRY uses a many-sorted model rather than one untyped value domain.

At minimum, implementations SHOULD recognize domains corresponding to:

```text
ArtifactId
CommitId
BranchId
CellId
RecordId
ObjectRef
DigestRef
ActorId
RunId
RenderId
SignatureId
Timestamp
Interval
String
Boolean
Integer
Decimal
Binary
JSON
```

The total value universe is a disjoint union:

\[
D = \biguplus_{\tau \in Types} D_\tau
\]

Values from unrelated domains MUST NOT compare equal merely because their textual encodings match.

For example:

```text
record:claim_007
cell:claim_007
```

are different typed identities even though both contain the suffix `claim_007`.

## 8.2 Parameterized reference types

Logical schemas SHOULD use parameterized reference types:

```text
Ref<Cell>
Ref<Record>
Ref<Claim>
Ref<Evidence>
Ref<Decision>
Ref<Object>
Ref<Run>
Ref<Commit>
```

A generic reference type MAY be accepted at an interchange boundary, but a query MUST narrow it before applying type-specific operations.

## 8.3 Scalar equality

Scalar equality is defined within a type.

Cross-type numeric comparisons MAY be supported only through explicit coercion rules declared by the type system.

String comparison MUST declare its collation and normalization policy when the result depends on them.

## 8.4 Reference identity

Two immutable `object:` references are equal when their canonical content-addressed identities are equal.

Two logical references are equal when their canonical parsed identities are equal.

A named output reference is not equal to the immutable object to which it resolves. Resolution is a relation, not equality.

## 8.5 Semantic equivalence

Semantic equivalence MUST be represented explicitly, for example:

```text
SemanticEquivalent(
    left_ref,
    right_ref,
    evaluation_id,
    label,
    score
)
```

A semantic-equivalence relation MAY support a join. It MUST NOT silently redefine `=`.

---

# 9. Source and Snapshot Model

## 9.1 Single-artifact instance

For artifact `a` at commit `c`, let:

\[
I_{a,c}
\]

denote the complete logical database instance represented by that committed artifact state.

A query is a function:

\[
Q : I_{a,c} \mapsto R
\]

where `R` is a finite relation.

## 9.2 Branch resolution

A query MAY specify:

```text
artifact: art_01...
branch: main
```

Before evaluation, the runtime MUST resolve:

\[
head(a, main) \rightarrow c
\]

and thereafter evaluate against `I(a,c)`.

If the branch advances during evaluation, the query result remains tied to the originally resolved commit.

## 9.3 Federated instance

A federated query uses an immutable source manifest:

```json
{
  "sources": [
    {
      "artifact_id": "art_A",
      "commit_id": "commit_042",
      "alias": "evaluation"
    },
    {
      "artifact_id": "art_B",
      "commit_id": "commit_119",
      "alias": "contracts"
    }
  ]
}
```

The conceptual federated instance is:

\[
I_F = \biguplus_{(a,c) \in F} I_{a,c}
\]

Artifact-qualified identity MUST be preserved unless an explicit cross-artifact identity relation is applied.

## 9.4 Visibility policy

A source manifest MUST identify the authorization or visibility policy used to expose tuples.

A query over a filtered source answers questions about visible state, not necessarily the complete artifact state. The result metadata MUST disclose that distinction.

---

# 10. Logical Schemas

## 10.1 Snapshot schema

The snapshot schema represents one selected committed state.

Candidate base relations include:

```text
Artifact
ManifestFeature
Cell
CellDependency
LinearCellPosition
ExecutionNode
ExecutionEdge
Record
RecordStatus
RecordDependency
Claim
Evidence
Supports
Decision
DecisionCandidate
DecisionBasis
Proposal
Review
Verification
Failure
Actor
Run
RunCell
OutputContract
OutputBinding
Object
ProvenanceInput
ProvenanceOutput
Render
Diagnostic
Branch
Signature
```

A conforming implementation MAY expose additional registered relations.

## 10.2 History schema

The history schema exposes commit and branch structure:

```text
Commit
CommitParent
Branch
BranchHead
VisibleAt
ChangedAt
IntroducedAt
SupersededAt
RunAtCommit
RecordVersion
CellVersion
ObjectReachability
```

Snapshot queries SHOULD use the snapshot schema. Historical queries SHOULD use the history schema explicitly.

## 10.3 Normalized projection

The logical projection SHOULD avoid storing repeated arrays or nested documents as indivisible query values when their members have independent semantic meaning.

For example, a claim record containing:

```json
{
  "record_id": "claim_007",
  "supporting_evidence": [
    "record:evidence_011",
    "record:evidence_012"
  ]
}
```

is logically projected as:

```text
Claim(claim_007, ...)
Supports(evidence_011, claim_007)
Supports(evidence_012, claim_007)
```

This prevents update anomalies and supports exact joins, constraints, provenance, and indexable access paths.

## 10.4 Ordered arrays

If array order is semantically meaningful, the normalized relation MUST include an ordinal:

```text
LinearCellPosition(ordinal, cell_id)
DecisionCandidatePosition(decision_id, ordinal, candidate_ref)
```

If order is not semantically meaningful, the relation MUST be treated as a set.

## 10.5 Example normalized core

```text
Record(
    record_id,
    record_type,
    summary,
    created_by,
    created_at
)

RecordStatus(
    record_id,
    lifecycle,
    staleness,
    verification
)

Claim(
    record_id,
    statement,
    claim_type,
    confidence,
    confidence_basis
)

Evidence(
    record_id,
    evidence_type,
    source_ref,
    source_object
)

Supports(
    evidence_id,
    claim_id
)

RecordDependency(
    dependent_ref,
    dependency_ref,
    dependency_kind
)

Decision(
    record_id,
    decision_type,
    selected,
    decision_rule,
    made_by
)

DecisionCandidate(
    decision_id,
    candidate_ref
)

DecisionBasis(
    decision_id,
    basis_ref
)

Cell(
    cell_id,
    cell_type,
    title,
    summary,
    source_hash,
    contract_hash,
    actor_id
)

CellDependency(
    cell_id,
    upstream_ref
)

LinearCellPosition(
    ordinal,
    cell_id
)

ExecutionEdge(
    from_cell,
    to_cell
)

OutputContract(
    cell_id,
    output_name,
    mime_type,
    schema_ref
)

OutputBinding(
    run_id,
    cell_id,
    output_name,
    object_ref,
    mime_type
)
```

---

# 11. Set, Bag, and Sequence Semantics

## 11.1 Set semantics

The default relation is a finite mathematical set:

\[
R \subseteq D_{\tau_1} \times \cdots \times D_{\tau_n}
\]

A tuple occurs at most once.

Duplicate content does not imply duplicate identity. Two events with identical text remain distinct if they have distinct event or record IDs.

## 11.2 Bag semantics

A bag associates each tuple with a nonnegative multiplicity:

\[
R_B : Tuple \rightarrow \mathbb{N}
\]

Bag semantics MUST be requested explicitly.

The v0.3 certified bound algebra in §13 is normative for set relations. Approximate bag bounds require a registered extension. Exact bag queries remain permitted.

## 11.3 Sequence semantics

A sequence is an ordered finite collection. A relation is not implicitly ordered.

`ORDER BY` transforms a set or bag into a sequence.

A committed sequence result MUST have a deterministic total order. If the declared sort keys do not form a total order, the evaluator SHOULD add a stable identity as a final tie breaker or MUST report nondeterminism.

## 11.4 Result kinds

A query result MUST declare one of:

```text
SET<T>
BAG<T>
SEQUENCE<T>
```

## 11.5 Limit and sampling

`LIMIT`, `FIRST`, and `TOP` MUST operate on a sequence.

Applying a limit without an explicit order MUST either:

- fail validation for a committed deterministic result; or
- be labeled an arbitrary nondeterministic sample.

A limit over an inexact relation does not generally preserve lower- or upper-bound semantics. Such a plan MUST use a registered bound-transfer rule or downgrade to `heuristic`.

---

# 12. Annotated Relations and Provenance

## 12.1 Finite-support annotated relation

A generalized relation MAY be modeled as:

\[
R_K : Tuple \rightarrow K
\]

where all but finitely many tuples map to zero.

Different annotation structures support different semantics:

| Annotation domain | Interpretation |
|---|---|
| Boolean | set membership |
| Natural numbers | bag multiplicity |
| Provenance polynomial | derivation lineage |
| Product annotation | multiple independent annotations |

## 12.2 Default annotation

The default is Boolean set membership:

\[
K = \mathbb{B} = \{0,1\}
\]

## 12.3 Positive algebra propagation

For suitable annotation structures, positive operators propagate annotations as follows.

Union:

\[
(E_1 \cup E_2)(t) = E_1(t) + E_2(t)
\]

Join:

\[
(E_1 \bowtie E_2)(t)
=
\sum_{t_1 \Join t_2 = t}
E_1(t_1) \cdot E_2(t_2)
\]

Projection:

\[
(\pi_A E)(u)
=
\sum_{t : t[A] = u} E(t)
\]

Selection:

\[
(\sigma_p E)(t)
=
E(t) \cdot [p(t)]
\]

## 12.4 Provenance modes

A query MAY request:

```text
none
tuple
why
how
full_graph
```

A minimal implementation MAY support `none` and `tuple` only.

Provenance MUST identify source commits and SHOULD identify source records, objects, runs, semantic evaluations, view substitutions, and rewrite rules where applicable.

## 12.5 Lower-membership provenance

For a bounded result:

\[
L \subseteq R \subseteq U
\]

ordinary tuple-membership provenance applies normatively to tuples in `L`.

For each `t ∈ L`, the requested `tuple`, `why`, `how`, or `full_graph` mode explains why `t` is certified to belong to the exact relation `R`.

A lower-bound tuple MAY cite:

- exact base tuples;
- certified lower-bound tuples;
- exact predicates;
- transfer-rule applications;
- semantic assessments carrying a lower-bound contract;
- current completeness or integrity assertions;
- and current proof or verification evidence.

## 12.6 Upper-bound derivation provenance

An upper relation MUST be able to record how it was certified as an envelope for the exact answer.

Upper-bound derivation provenance SHOULD identify:

- input upper or lower relations used by the transfer rule;
- the normative or registered transfer-rule ID;
- source manifests and commits;
- temporal, visibility, authorization, and leakage contexts;
- semantic evaluators and evaluator guarantees;
- view substitutions;
- and rewrite-rule applications.

This provenance establishes:

\[
R \subseteq U
\]

It does not establish `t ∈ R` for every `t ∈ U`.

## 12.7 Upper-only tuples

A tuple in:

\[
U \setminus L
\]

has not been excluded by the current bounds but is not positively certified as an exact-answer member.

Such a tuple MUST NOT carry ordinary positive why-provenance that represents exact membership.

An implementation MAY attach extension metadata such as:

```text
possibility_reason
exclusion_not_certified
hidden_determining_evidence
heuristic_predicate_unresolved
```

Membership in `U` alone does not establish that some admissible possible world contains the tuple; it establishes only enclosure by the current upper bound. The semantics of stronger per-tuple possibility explanations are an extension area in v0.3.

## 12.8 Exact-result collapse

When:

\[
L = U = R
\]

lower-membership provenance and upper-bound derivation refer to the same exact result. An implementation MAY serialize one provenance object if it preserves both requested contracts.

## 12.9 Negation and aggregation caveat

Provenance under unrestricted negation and aggregation is substantially more complex than positive relational provenance. SOL-QRY v0.3 restricts provenance guarantees for those operations to normative or registered rules and MUST disclose unsupported modes.

For bounded results, provenance modes above `tuple` apply normatively to lower-membership provenance only unless a registered extension defines stronger upper-only semantics.

---

# 13. Certified Answer-Bound Algebra

## 13.1 Formal model

For a set-valued query `Q` over database instance `I`, the exact denotation is:

\[
R = Q(I)
\]

A certified bounded result is a pair:

\[
(L,U)
\]

such that:

\[
L \subseteq R \subseteq U
\]

The invariant `L ⊆ U` MUST hold.

`L` is a certified lower relation. Every tuple in `L` is guaranteed to belong to the exact answer.

`U` is a certified upper relation. Every exact-answer tuple is guaranteed to occur in `U`.

## 13.2 Canonical guarantee kinds

The canonical guarantee vocabulary is:

```text
exact
lower_bound
upper_bound
bounded
heuristic
```

Their meanings are:

| Kind | Formal meaning |
|---|---|
| `exact` | Both certified sides are present and `L = U = R` |
| `lower_bound` | A certified `L ⊆ R` is present and the upper side is unavailable under §13.5 |
| `upper_bound` | A certified `R ⊆ U` is present and the lower side is unavailable under §13.5 |
| `bounded` | Both certified sides are present; canonical serialization SHOULD use `exact` when they are identical |
| `heuristic` | No certified inclusion relation is established |

The labels `sound_subset` and `complete_superset` MAY be accepted as compatibility aliases for `lower_bound` and `upper_bound`, respectively. Canonical serialization MUST use the v0.3 vocabulary.

A weak but valid side remains available. For example, an explicitly typed empty lower relation is available even when it is not selective.

## 13.3 Assurance is separate from guarantee

A formal guarantee declaration MUST carry an assurance record:

```text
proven
validated
contract_asserted
tested
unaudited
unknown
```

Example:

```json
{
  "guarantee": {
    "kind": "bounded",
    "lower_object": "object:sha256:...",
    "upper_object": "object:sha256:..."
  },
  "assurance": {
    "status": "validated",
    "evidence": ["record:verification_019"],
    "depends_on": [
      "record:verification_019",
      "object:sha256:...",
      "sol:bound/difference/v1"
    ]
  }
}
```

`unknown` is an assurance state, not an answer-guarantee kind.

Assurance evidence SHOULD classify its form:

```text
mechanized_proof
checked_certificate
formal_derivation
exhaustive_finite_check
property_test
adversarial_corpus
contract_assertion
```

A prose `proof_reference` alone MUST NOT justify `proven` assurance.

Property tests and adversarial corpus cases support `tested` or, under a declared validation profile, `validated`; they do not by themselves prove a universal theorem.

Assurance records MUST declare the evidence on which they depend. They inherit the dependency-driven staleness and reverification machinery defined by RFC-SOL-0001 §§20.4 and 37 rather than defining a parallel invalidation system. If a required proof, verification, source object, evaluator contract, policy, or other assurance dependency becomes stale, invalidated, unavailable, or requires reverification:

- the historical assurance record remains in artifact history;
- the assurance record MUST become stale or require reverification under the applicable record profile; and
- its effective assurance for current query evaluation MUST be `unknown` until current verification is established.

## 13.4 Exact result representation

An exact result MAY serialize only one relation object if it declares:

```text
lower_object = result_object
upper_object = result_object
```

or an equivalent canonical shorthand.

## 13.5 Unavailable sides

When only one certified side is available, the missing side MUST be represented explicitly as unavailable rather than synthesized from an arbitrary finite universe.

An unavailable side is not the same as a weak side. An explicit empty lower relation or explicit finite exact upper domain is available when its schema and all source, temporal, visibility, authorization, and policy contexts are defined.

## 13.6 Physical-plan obligation

Every physical operator that consumes or produces an inexact relation MUST either:

1. implement a normative bound-transfer rule in this specification;
2. implement a registered extension rule; or
3. leave unsupported sides unavailable and downgrade the overall result to `heuristic` only when no certified side remains.

## 13.7 Positive monotone operators

Let:

\[
L_1 \subseteq R_1 \subseteq U_1
\]

and:

\[
L_2 \subseteq R_2 \subseteq U_2
\]

For exact deterministic predicates and ordinary set semantics:

| Operator | Certified lower relation | Certified upper relation |
|---|---|---|
| `Select(p, R)` | `Select(p, L)` | `Select(p, U)` |
| `Project(A, R)` | `Project(A, L)` | `Project(A, U)` |
| `Rename(m, R)` | `Rename(m, L)` | `Rename(m, U)` |
| `Union(R1, R2)` | `L1 ∪ L2` | `U1 ∪ U2` |
| `Intersect(R1, R2)` | `L1 ∩ L2` | `U1 ∩ U2` |
| `Join(R1, R2)` | `L1 ⋈ L2` | `U1 ⋈ U2` |
| `Distinct(R)` under set interpretation | `Distinct(L)` | `Distinct(U)` |

These componentwise rules require that every predicate or join condition used to derive the corresponding side be exact and deterministic. A semantic predicate contributes only the sides established by its own contract or by §13.7.1 structural containment.

### 13.7.1 Structural containment and one-sided bounds

A certified output side may be derived without certified semantics for every input when the operator shape itself proves containment.

If an operator `O` satisfies:

\[
O(R_1,\ldots,R_n) \subseteq R_i
\]

then any available certified upper relation `U_i` is an upper bound for the output:

\[
O(R_1,\ldots,R_n) \subseteq R_i \subseteq U_i
\]

If an operator satisfies:

\[
R_i \subseteq O(R_1,\ldots,R_n)
\]

then any available certified lower relation `L_i` is a lower bound for the output.

The baseline core rules are:

| Operator condition | Certified side available independently |
|---|---|
| Tuple-preserving `Select(p, R)` with any predicate guarantee | `U_out = U_R` when `U_R` is available |
| `Intersect(R1, R2)` | `U1` is an upper bound when available; `U2` is also an upper bound when available; use `U1 ∩ U2` when both are available |
| `Difference(R1, R2)` | `U1` is an upper bound when available; use `U1 \ L2` when a certified `L2` is also available |
| `Union(R1, R2)` | Any available `L1` or `L2` is a lower bound; use `L1 ∪ L2` when both are available |

For a heuristic semantic filter over bounded input `R`:

\[
\varnothing \subseteq Select(p_{semantic},R) \subseteq U_R
\]

provided the empty relation is explicitly typed and context-compatible. If the evaluator emits a certified positive set `P` satisfying:

\[
P \subseteq Select(p_{semantic},R)
\]

then `P` MAY replace the empty lower relation.

These rules apply only to tuple-preserving operators. An evaluator that invents tuples, changes tuple identity, expands one tuple into several, or rewrites values is not a `Select` for this purpose and MUST use an operator with an explicit output-domain contract.

A structural containment rule MUST preserve schema mapping, identity, source manifest, temporal context, visibility, authorization, and leakage policy.

## 13.8 Difference

Difference is monotone in its left operand and antimonotone in its right operand.

For:

\[
R = R_1 \setminus R_2
\]

when all required sides are available, valid bounds are:

\[
L_R = L_1 \setminus U_2
\]

\[
U_R = U_1 \setminus L_2
\]

When `L2` is unavailable, `U1` remains a valid upper bound under §13.7.1.

When `U2` is unavailable, no nontrivial lower bound follows from `L1` alone; an explicit empty lower relation remains valid.

This rule is valid only when operands share compatible identity, visibility, authorization, leakage, temporal, and world-assumption contexts.

## 13.9 Complement and negation

For complement relative to an explicit finite exact domain `D`:

\[
L_{\neg R} = D \setminus U_R
\]

\[
U_{\neg R} = D \setminus L_R
\]

Negation therefore exchanges lower- and upper-bound roles.

A complement without an explicit finite exact domain is invalid in the core profile.

## 13.10 Recursion and stratification

Positive recursive rules are monotone. Lower and upper fixed points MAY be computed separately:

```text
lfp(program, lower inputs)
lfp(program, upper inputs)
```

A recursive program containing negation MUST follow the stratification rules in §22. Every lower stratum is fully evaluated before a higher stratum consumes it negatively. Bound transfer across strata uses the rules of the operators in that stratum.

Example:

```text
reachable(X) :- seed(X).
reachable(Y) :- reachable(X), edge(X, Y).

allowed(X) :- reachable(X), not blocked(X).
```

The positive recursive first stratum yields:

```text
L_reachable = lfp(program, lower inputs)
U_reachable = lfp(program, upper inputs)
```

The second stratum is difference:

\[
L_{allowed} = L_{reachable} \setminus U_{blocked}
\]

\[
U_{allowed} = U_{reachable} \setminus L_{blocked}
\]

If a required blocked-side bound is unavailable, §13.7.1 and §13.17 determine which one-sided result remains certified.

## 13.11 COUNT_SET

For a finite set relation:

\[
|L| \leq COUNT\_SET(R) \leq |U|
\]

The result is a certified numeric interval.

## 13.12 SUM

For numeric tuple value `v(t)`, write optional tuples as:

\[
O = U \setminus L
\]

A valid finite bound is:

\[
SUM_{min} = \sum_{t \in L} v(t) + \sum_{t \in O, v(t)<0} v(t)
\]

\[
SUM_{max} = \sum_{t \in L} v(t) + \sum_{t \in O, v(t)>0} v(t)
\]

This assumes each tuple contributes at most once under set semantics and that every value is exact and finite.

## 13.13 MIN and MAX

For nonempty exact-value sets:

\[
MIN(U) \leq MIN(R) \leq MIN(L)
\]

when `L` is nonempty.

Similarly:

\[
MAX(L) \leq MAX(R) \leq MAX(U)
\]

when `L` is nonempty.

If `L` is empty, the evaluator MUST account for the possibility that `R` is empty and MUST return an optional or conditional numeric bound.

## 13.14 AVG over finite exact-valued bounds

Relation inclusion alone does not yield a scalar lower-bound or upper-bound label for `AVG`, but finite exact-valued lower and upper sets permit a certified interval.

The registered rule:

```text
sol:bound/avg_optional_prefix/v1
```

applies when:

- `L` and `U` are finite set relations;
- `L ⊆ U`;
- every included numeric value is exact, finite, present, and visible under the same policy;
- tuple multiplicity is one;
- and `AVG` is defined over one numeric expression.

Let:

\[
O = U \setminus L
\]

Let `n_L = |L|` and `s_L` be the exact sum of values in `L`.

Sort optional values in ascending order:

\[
a_1 \leq a_2 \leq \cdots \leq a_m
\]

and descending order:

\[
d_1 \geq d_2 \geq \cdots \geq d_m
\]

When `n_L > 0`, the certified minimum and maximum are:

\[
AVG_{min} =
\min_{0 \leq k \leq m}
\frac{s_L + \sum_{i=1}^{k} a_i}{n_L+k}
\]

\[
AVG_{max} =
\max_{0 \leq k \leq m}
\frac{s_L + \sum_{i=1}^{k} d_i}{n_L+k}
\]

For each fixed cardinality `k`, an extremal subset uses the `k` smallest or `k` largest optional values, so evaluating sorted prefixes is sufficient. A conforming implementation may compute the interval in `O(m log m)` time.

When `n_L = 0`:

- `k = 0` represents a possibly empty exact relation for which `AVG` is undefined;
- numeric extrema are evaluated over `1 ≤ k ≤ m`; and
- the result MUST include `may_be_empty: true` unless another constraint proves nonemptiness.

If `U` is empty, the exact relation is empty and `AVG` is undefined.

The rule does not apply to approximate numeric values, protected values whose contribution is undisclosed, bag multiplicities, or tuple-generating evaluators unless a registered extension supplies the missing semantics.

A baseline implementation MAY reject inexact `AVG`; an implementation claiming certified inexact `AVG` support in v0.3 MUST implement this rule or a registered rule with equal or stronger validity guarantees.

Medians, percentiles, rank, and top-k remain subject to their own registered rules.

## 13.15 Ordering and limit

Ordering an inexact set does not by itself establish which tuples occupy a given prefix. `LIMIT`, top-k, and rank over inexact inputs require registered position-certainty rules or MUST be labeled heuristic.

## 13.16 Mixed guarantee composition

A heuristic input or predicate invalidates only the certified output sides that depend on its uncertified membership claims.

A plan MAY retain certified lower or upper sides established independently by:

- structural containment under §13.7.1;
- another certified operand side;
- an explicit finite exact domain;
- or a normative or registered transfer rule.

A heuristic candidate relation MUST NOT be treated as a certified lower or upper relation merely because it appears plausible.

If no certified side remains, the result kind is `heuristic`.

A plan MUST NOT infer a guarantee from friendly labels alone. It MUST propagate concrete bound objects or a proof-equivalent symbolic representation.

## 13.17 Partial-bound availability

Each output side is computed independently. If a transfer rule requires an input side that is unavailable, the corresponding output side remains unavailable unless a normative or registered rule establishes a replacement bound.

Baseline examples:

- `Union(R1,R2)` may use any available lower side as a valid output lower bound; when both are available, `L1 ∪ L2` is the baseline lower. Its upper side ordinarily requires both upper sides.
- `Intersect(R1,R2)` ordinarily requires both lower sides for a nontrivial lower bound. Any available operand upper is an output upper bound; both yield the tighter baseline `U1 ∩ U2`.
- `Difference(R1,R2)` may use `U1` as an upper bound without a certified right operand. With `L2`, the tighter baseline is `U1 \ L2`. Its nontrivial lower side requires both `L1` and `U2`.
- A tuple-preserving semantic `Select` may use the input upper relation even when predicate membership is heuristic.

Trivial bounds such as an explicitly typed empty lower relation MAY be used only when their schema, temporal context, visibility context, authorization context, and policy context are explicit.

A trivial finite upper domain MAY be used only when that domain is explicitly enumerated or otherwise exactly defined.

## 13.18 Validity versus tightness

The transfer rules in this section establish valid baseline bounds. They do not require globally maximal lower bounds or globally minimal upper bounds when additional constraints, correlations, provenance, completeness assertions, or domain knowledge are available.

A registered rule MAY produce tighter bounds if its proof obligations establish validity under its declared preconditions.

A validator MUST NOT reject a result solely because its certified bounds are tighter than the normative baseline rule.

A rule claiming optimal or tight bounds MUST define the information model relative to which that claim holds.

## 13.19 Guarantee validation

A validator MUST be able to check:

- `L ⊆ U`;
- the declared operator transfer rule;
- structural-containment justification for one-sided bounds;
- source, temporal, visibility, authorization, and leakage-context compatibility;
- exactness of predicates required by a rule;
- evaluator guarantees;
- aggregate preconditions;
- assurance evidence and effective assurance after staleness;
- provenance classification for lower, upper, and upper-only tuples;
- tighter registered-rule evidence where applicable;
- and any downgrade caused by budgets or unsupported operators.

---

# 14. Missing and Protected Values

SOL-QRY MUST NOT overload one generic null value with multiple meanings.

A typed optional value may be in one of these states:

```text
present(value)
absent
unknown
redacted
unavailable
unresolved
```

## 14.1 Absent

The field is not applicable or was not supplied.

## 14.2 Unknown

A value may exist, but the artifact does not know it.

## 14.3 Redacted

A value exists or may exist, but policy prevents disclosure.

## 14.4 Unavailable

A referenced external resource is not currently retrievable.

## 14.5 Unresolved

A syntactically valid reference does not resolve in the selected source context.

## 14.6 Predicates

The query language SHOULD provide:

```text
IS PRESENT
IS ABSENT
IS UNKNOWN
IS REDACTED
IS UNAVAILABLE
IS UNRESOLVED
```

These states MUST NOT compare equal merely because none exposes an ordinary scalar value.

## 14.7 Protected-value propagation

Operators that consume protected or unavailable values MUST declare whether they:

- preserve the tagged state;
- produce an unknown result;
- suppress the tuple;
- produce a policy-controlled diagnostic;
- or fail evaluation.

A query optimizer MUST NOT rewrite protected-value handling across a boundary where the leakage policy could change.

---

# 15. Assertion Semantics and World Assessment

## 15.1 Artifact truth

A tuple in the `Claim` relation means:

> The selected artifact state contains a claim record with these fields.

It does not by itself mean that the claimed proposition is true in the represented world.

Contradictory claims can coexist without making the artifact database structurally inconsistent. They represent competing assertions.

## 15.2 Status dimensions

Lifecycle, staleness, and verification are metadata about the record and its support state.

They MUST NOT be collapsed into binary truth.

Examples:

- `unverified` does not mean false;
- `failed_verification` does not necessarily prove the opposite proposition;
- `stale` means dependencies or context no longer support current use;
- `withdrawn` describes lifecycle;
- `confidence: 0.8` is not automatically a probability of truth.

## 15.3 World-assessment layer

A separate policy-defined layer MAY derive relations such as:

```text
AcceptedFact(policy_id, proposition_id)
RejectedFact(policy_id, proposition_id)
ConflictedFact(policy_id, proposition_id)
UndeterminedFact(policy_id, proposition_id)
```

A policy MUST declare:

- the evidence relations it considers;
- verification requirements;
- staleness treatment;
- conflict handling;
- temporal scope;
- authority rules;
- whether absence has closed-world meaning.

## 15.4 Four-state support model

A future assessment profile MAY use a two-bit state:

\[
(s^+, s^-) \in \{0,1\}^2
\]

| Positive support | Negative support | Interpretation |
|---:|---:|---|
| 0 | 0 | undetermined |
| 1 | 0 | supported |
| 0 | 1 | refuted |
| 1 | 1 | conflicting |

This requires an explicit negative-support or refutation relation. Existing `supports` relations MUST NOT be reinterpreted to provide that information implicitly.

## 15.5 Assessment provenance

An accepted, rejected, conflicted, or undetermined fact MUST identify the assessment policy, source assertions, evidence, evaluator or actor, source commits, and assessment time.

---

# 16. Open-World and Closed-World Semantics

## 16.1 Relation declarations

Each relation SHOULD declare a world assumption:

```text
closed
open
policy_scoped
approximate
externally_incomplete
```

## 16.2 Closed relation

For a closed relation, absence under the selected snapshot and policy may imply nonmembership.

## 16.3 Open relation

For an open relation, absence means only that no visible assertion is present.

## 16.4 Policy-scoped relation

For a policy-scoped relation, tuples may be hidden. Absence means “not visible under this policy,” not “does not exist.”

## 16.5 Approximate relation

An approximate relation may omit or add tuples according to its certified bound or heuristic contract.

## 16.6 Externally incomplete relation

An externally incomplete relation represents a source known not to cover the full relevant world.

## 16.7 Negation forms

SOL-QRY SHOULD distinguish:

```text
NOT ASSERTED R(x)
NO VISIBLE R(x)
CERTAINLY NOT P(x) UNDER policy
```

These are not equivalent.

## 16.8 Completeness assertions

A completeness assertion SHOULD identify:

- the relation;
- the predicate region for which it is complete;
- the source commits;
- the visibility policy;
- the valid-time interval;
- the actor or verification that supports it;
- and its staleness state.

Example:

```json
{
  "relation": "Evidence",
  "complete_for": {
    "claim_id": "record:claim_007",
    "evidence_type": "metric_table"
  },
  "source_commit": "commit:commit_042",
  "visibility_policy": "policy:internal_full",
  "verification_ref": "record:verification_031"
}
```

Negation MAY rely on a local completeness assertion rather than requiring the entire relation to be globally closed.

## 16.9 Possible-world profiles

A future profile may define a set of admissible worlds:

\[
\Omega_p(I)
\]

under assessment policy `p`.

Certain answers are:

\[
Certain_p(Q,I)
=
\bigcap_{W \in \Omega_p(I)} Q(W)
\]

Possible answers are:

\[
Possible_p(Q,I)
=
\bigcup_{W \in \Omega_p(I)} Q(W)
\]

SOL-QRY v0.3 reserves the query modes:

```text
ASSERTED
CERTAIN UNDER <policy>
POSSIBLE UNDER <policy>
```

Only `ASSERTED` is required for baseline conformance.

---

# 17. Temporal Semantics

## 17.1 Artifact time

Artifact time describes when a tuple is present in committed Sol history.

The fundamental coordinate is commit identity and ancestry, not timestamp order.

## 17.2 Valid time

Valid time describes when a modeled proposition is asserted to hold in the represented world.

A temporal semantic record MAY declare:

```text
valid_from
valid_to
```

or another registered interval representation.

## 17.3 Combined query

A query may specify both:

```text
AT COMMIT commit_042
VALID AT 2026-07-21T14:00:00Z
```

This means:

> Using the knowledge recorded in commit 42, return propositions asserted to be valid at the given world time.

## 17.4 History operators

Candidate temporal constructs include:

```text
AT COMMIT <commit-ref>
ON BRANCH <branch-ref>
KNOWN AT <commit-ref>
VALID AT <instant>
VALID DURING <interval>
CHANGED BETWEEN <commit-a> AND <commit-b>
INTRODUCED BY <commit>
SUPERSEDED BEFORE <commit>
```

## 17.5 Latest

`LATEST` MUST NOT be interpreted solely by wall-clock timestamp in a branching history.

A latest query MUST specify:

- a branch or lineage;
- an ancestry relation;
- a deterministic tie or conflict rule.

## 17.6 Temporal guarantee compatibility

Lower and upper relations MUST be evaluated under the same artifact-time and valid-time context. Bounds from different source commits or valid-time slices MUST NOT be combined without an explicit temporal reconciliation operator.

---

# 18. Integrity Constraints

## 18.1 Constraint types

Relation declarations SHOULD support:

- primary and candidate keys;
- foreign keys;
- functional dependencies;
- check constraints;
- temporal constraints;
- exclusion constraints;
- lifecycle constraints;
- authorization constraints;
- completeness declarations.

## 18.2 Examples

```text
record_id → record_type, created_by, created_at
```

```text
(run_id, cell_id, output_name) → object_ref
```

```text
Supports.evidence_id REFERENCES Evidence.record_id
Supports.claim_id REFERENCES Claim.record_id
```

```text
A selected snapshot has at most one current valid binding
for a logical named output.
```

## 18.3 Optimizer trust

A logical rewrite MAY rely on a constraint only if that constraint is:

- normative for the relation;
- validated at the selected source commits; or
- backed by a current verification record whose dependencies are current.

An asserted but unverified constraint MUST NOT justify correctness-sensitive rewrites.

## 18.4 Constraint provenance

A query result whose exactness depends on a constraint SHOULD include that constraint and its verification in the result provenance.

---

# 19. Declarative Logical Model

## 19.1 Canonical calculus

The normative meaning of a SOL-QRY query SHOULD be expressible as a typed, range-restricted relational-calculus expression:

\[
Q(\bar{x}) = \{\bar{x} \mid \varphi(\bar{x})\}
\]

where `φ` is a formula over the selected database instance.

A minimal grammar is:

\[
\begin{aligned}
\varphi ::= {}& R(t_1,\ldots,t_n) \\
&\mid t_1 = t_2 \\
&\mid t_1 < t_2 \\
&\mid \varphi \land \varphi \\
&\mid \varphi \lor \varphi \\
&\mid \neg \varphi \\
&\mid \exists x:\tau.\varphi \\
&\mid \forall x:\tau.\varphi
\end{aligned}
\]

A human-facing language may resemble SQL, Datalog, comprehensions, or a graphical builder. The canonical interchange form SHOULD be a typed AST.

## 19.2 Query parameters

Queries MAY declare typed parameters:

```json
{
  "name": "target_commit",
  "type": "Ref<Commit>",
  "required": true
}
```

Parameter values MUST be bound before evaluation and included in the query execution identity.

## 19.3 Result schema

A query MUST declare or infer a result schema containing:

- field names;
- field types;
- optionality states;
- collection kind;
- ordering contract;
- provenance mode;
- answer-guarantee requirement;
- and visibility policy.

## 19.4 Declarative requirement

A query states which relation is wanted. It MUST NOT require a particular physical scan, index, join algorithm, cache, page size, or model implementation unless the query is explicitly an execution-diagnostic query.

---

# 20. Query Safety and Domain Independence

A conforming query MUST denote a finite result determined by the finite active domain of its sources and explicit finite domains.

## 20.1 Safety rules

At minimum:

1. Every returned variable MUST be bound by a positive relation atom or finite explicit domain.
2. Every variable appearing in a negated subformula MUST be bound outside that subformula.
3. Every aggregate input MUST range over a finite relation.
4. Universal quantification MUST be over an explicit finite domain.
5. Functions MUST NOT synthesize an unbounded domain.
6. Reference traversal MUST range over resolvable references in the source manifest.
7. A complement MUST name an explicit finite exact domain.

## 20.2 Safe example

```text
{ c |
    Claim(c)
    AND NOT EXISTS e (
        Evidence(e)
        AND Supports(e, c)
    )
}
```

This is safe only if `c` is positively bound and the negated relations satisfy the required completeness contract.

## 20.3 Unsafe example

```text
{ x | NOT Claim(x) }
```

This is unsafe because it ranges over every possible value outside the finite database instance.

## 20.4 Semantic evaluator domains

A semantic evaluator MUST consume an explicit finite input relation. It MUST NOT implicitly search an unbounded external corpus unless that corpus is itself declared as a finite source relation or external service contract.

---

# 21. Recursion

## 21.1 Need for recursion

Sol state contains recursive structures:

- commit ancestry;
- execution reachability;
- dependency closure;
- provenance chains;
- supersession chains;
- evidence graphs.

## 21.2 Least-fixed-point semantics

Positive recursive rules use least-fixed-point semantics.

Example:

```text
ancestor(Older, Newer) :-
    commit_parent(Newer, Older).

ancestor(Older, Newer) :-
    commit_parent(Newer, Middle),
    ancestor(Older, Middle).
```

## 21.3 Stratification

SOL-QRY v0.3 supports:

```text
positive recursion
stratified negation
nonrecursive stratified aggregation
```

Unrestricted recursion through negation or aggregation is outside the core profile.

## 21.4 Termination

A recursive query MUST range over finite source relations and MUST have an evaluation strategy that reaches a finite fixed point or reports nonconformance.

## 21.5 Bounds through recursion

Positive recursive programs MAY be evaluated separately over lower and upper input relations as specified in §13.10. A program containing heuristic semantic evaluators MAY retain any lower or upper sides established by structural containment, another certified operand, an explicit finite exact domain, or a normative or registered rule. If no certified side remains, the result is heuristic.

---

# 22. Negation and Difference

## 22.1 Set difference

`A EXCEPT B` is valid when both operands have compatible identity, temporal, visibility, authorization, leakage, and world-assumption contexts.

Exact classical difference requires exact closed inputs. Bounded difference MAY use the transfer rule in §13.8.

## 22.2 Assertion absence

`NOT ASSERTED R(x)` means that no visible tuple in the selected assertion relation matches.

## 22.3 Epistemic negation

`CERTAINLY NOT P(x) UNDER policy` means the negated proposition holds in every admissible world under the selected assessment policy.

## 22.4 No silent substitution

The evaluator MUST NOT rewrite one form of negation into another unless the relevant world, completeness, policy, and bound assumptions establish equivalence.

## 22.5 Stratified negation

A negated relation MUST be fully defined in a lower stratum. Recursive cycles through negation are invalid in the v0.3 core profile.

---

# 23. Aggregation

## 23.1 Aggregate operators

SOL-QRY SHOULD define:

```text
COUNT_SET
COUNT_BAG
SUM
MIN
MAX
AVG
COLLECT_SET
COLLECT_BAG
```

Plain `COUNT` SHOULD be avoided in the canonical AST because its multiplicity semantics can be ambiguous.

## 23.2 Exact and inexact aggregation

Exact aggregation over exact finite inputs follows ordinary mathematical semantics.

Aggregation over bounded inputs MUST use the rules in §13 or a registered extension rule. An implementation claiming certified inexact `AVG` support MUST implement `sol:bound/avg_optional_prefix/v1` or a registered rule with equal or stronger validity guarantees.

## 23.3 Open and approximate relations

An aggregate over an open-world, policy-filtered, externally incomplete, or approximate relation MUST disclose what was counted.

Examples:

```text
COUNT ASSERTED Evidence
COUNT VISIBLE Evidence
```

## 23.4 Empty input

Each aggregate MUST define its result on empty input.

## 23.5 Determinism

Floating-point and statistical aggregates SHOULD declare numerical stability, precision, and ordering requirements when exact reproducibility is requested.

## 23.6 Bag aggregation

Exact bag aggregation is permitted. Certified approximate bag aggregation requires a registered multiplicity-bound profile and is not part of baseline v0.3 conformance.

---

# 24. Logical Algebra

The logical algebra is implementation-independent. It is not a physical plan.

## 24.1 Core operators

| Operator | Meaning |
|---|---|
| `Relation(R)` | Extension of base or derived relation `R` |
| `Select(predicate, E)` | Tuples of `E` satisfying the predicate |
| `Project(fields, E)` | Selected attributes of tuples in `E` |
| `Rename(mapping, E)` | Attribute renaming |
| `Join(condition, E1, E2)` | Compatible tuple combinations |
| `Union(E1, E2)` | Tuples present in either operand |
| `Intersect(E1, E2)` | Tuples present in both operands |
| `Difference(E1, E2)` | Tuples in `E1` not in `E2`, subject to context requirements |
| `Distinct(E)` | Convert bag semantics to set semantics |
| `Group(keys, aggregates, E)` | Grouping and aggregation |
| `LeastFixpoint(rules)` | Recursive derivation |
| `TemporalSlice(spec, E)` | Restriction by commit or valid time |
| `Annotate(mode, E)` | Request provenance or another annotation |
| `Order(keys, E)` | Convert a relation to a sequence |
| `Limit(n, sequence)` | Prefix of an explicitly ordered sequence |
| `Evaluate(contract, E)` | Invoke or reference a semantic evaluator |

## 24.2 Source-context operators

A small number of context-setting operators are justified:

```text
Snapshot(artifact, commit)
Federation(source_manifest)
ValidTime(interval)
AssessmentPolicy(policy)
VisibilityPolicy(policy)
LeakagePolicy(policy)
```

These establish interpretation context rather than manipulating ordinary tuples.

## 24.3 Sol-specific derived relations

Most Sol-specific behavior SHOULD be expressed as derived relations rather than magical operators.

Examples:

```text
CurrentOutputBinding
CommitAncestor
ReachableDownstream
CurrentSupportingEvidence
CurrentVerification
VisibleRecord
```

## 24.4 Logical properties

Every logical node SHOULD expose properties required for validation and rewriting, including:

```text
schema
collection kind
keys
functional dependencies
world assumption
temporal context
visibility policy
authorization policy
leakage policy
answer bounds
assurance and assurance dependencies
lower-membership provenance capability
upper-bound derivation provenance capability
logical disclosure behavior
physical side-channel profile
determinism
side-effect class
```

---

# 25. Registered Rewrite Rules

## 25.1 No general equivalence requirement

Query equivalence is not decidable for the full family of languages and semantics contemplated by SOL-QRY. A conforming implementation is not required to prove arbitrary plan equivalence.

Conformance instead means that every applied rewrite is an instance of a registered rule whose proof obligations and preconditions are known.

## 25.2 Rewrite rule record

A rewrite rule SHOULD be represented as a registered object such as:

```json
{
  "rule_id": "sol:rewrite/push_exact_selection_through_join/v1",
  "pattern": "object:sha256:...",
  "replacement": "object:sha256:...",

  "requires": {
    "predicate_determinism": "exact",
    "predicate_scope": ["left_input"],
    "collection_kinds": ["set", "bag"],
    "evaluator_free": true,
    "same_temporal_context": true,
    "same_visibility_policy": true,
    "same_authorization_policy": true,
    "same_leakage_policy": true,
    "spans_policy_boundary": false
  },

  "preserves": [
    "value",
    "multiplicity",
    "provenance",
    "answer_bounds",
    "assurance",
    "logical_disclosure"
  ],

  "proof_evidence": [
    {
      "kind": "formal_derivation",
      "ref": "object:sha256:..."
    },
    {
      "kind": "property_test",
      "ref": "object:sha256:..."
    },
    {
      "kind": "adversarial_corpus",
      "ref": "QPATH-022"
    }
  ],

  "verification_refs": ["record:verification_044"],
  "pathology_tests": [
    "QPATH-022",
    "QPATH-026"
  ]
}
```

The corpus namespace is `QGOLD-*` and `QPATH-*`. Other namespaces MUST be registered explicitly before use.

## 25.3 Required preservation dimensions

A rewrite rule MUST declare which of the following it preserves:

```text
value
multiplicity
provenance
order
answer_bounds
assurance
diagnostics
logical_disclosure
evaluation_identity
physical_side_channel_class
```

`physical_side_channel_class` MAY be claimed only under a physical conformance profile that defines observables and operator implementations. A logical rule alone ordinarily leaves this dimension `not_claimed`.

## 25.4 Rule application

Before applying a rewrite, the optimizer MUST establish that:

1. the rule is registered and supported;
2. all declared preconditions hold;
3. every query-required equivalence dimension is preserved;
4. evaluator barriers are respected;
5. temporal, visibility, authorization, leakage, and world-assumption contexts remain compatible;
6. the rule’s proof or verification evidence is current under policy;
7. effective assurance has not become `unknown` through stale dependencies; and
8. any claimed physical side-channel preservation is backed by the required physical profile.

## 25.5 Conservative policy-boundary rule

A rewrite that crosses, removes, duplicates, reorders, or fuses any of the following is non-preserving by default:

```text
VisibilityPolicy
AuthorizationPolicy
LeakagePolicy
authorization filter
redaction projection
error-masking boundary
cardinality-protection boundary
semantic-evaluator boundary
```

Such a rewrite MAY be applied only when its registered rule explicitly proves the required logical-disclosure behavior for the selected policy.

This default is syntactic and conservative. It makes ordinary validation possible without solving the general inference-control problem.

## 25.6 Proof-evidence discipline

Registered proof evidence uses the following baseline vocabulary:

```text
mechanized_proof
checked_certificate
formal_derivation
exhaustive_finite_check
property_test
adversarial_corpus
contract_assertion
```

Minimum interpretation:

- `mechanized_proof`, `checked_certificate`, or a profile-accepted `formal_derivation` MAY support `proven` assurance;
- `property_test`, `adversarial_corpus`, and `exhaustive_finite_check` support `tested` or profile-defined `validated` assurance;
- `contract_assertion` supports `contract_asserted` assurance;
- prose without a checked derivation MUST NOT support `proven` assurance.

Every mandatory rewrite rule SHOULD ship with:

1. a human-readable derivation;
2. machine-checkable property tests over generated finite instances;
3. at least one adversarial corpus case that fails when a key precondition is removed; and
4. where practical, a mechanized proof or checked certificate.

The small mandatory Phase 4 rule kernel SHOULD be prioritized for mechanization.

## 25.7 Rule provenance

When auditability is requested, the logical-plan record MUST list every applied rewrite rule and the expression location at which it was applied.

The record SHOULD include the effective assurance and proof-evidence references used at application time.

## 25.8 Experimental rules

An implementation MAY support experimental rules. Results relying on an unverified rule MUST NOT be labeled exact or certified solely on that rule unless another independent current verification establishes the required properties.

## 25.9 Substrait and Calcite relationship

The canonical AST SHOULD map cleanly to established relational intermediate-representation concepts. A reference implementation SHOULD consider:

- mapping standard relational nodes to Substrait equivalents;
- mapping or implementing planning rules through Apache Calcite or another rule-based planner;
- representing Sol-specific semantics as declared extensions.

Neither Substrait nor Apache Calcite is a normative dependency. SOL-QRY semantics remain authoritative.

---

# 26. Semantic Evaluators and Materialized Assessments

## 26.1 Semantic evaluation as data production

A semantic evaluator MUST produce a typed assessment relation rather than silently act as exact equality or truth.

Candidate relation:

```text
SemanticAssessment(
    evaluation_id,
    left_ref,
    right_ref,
    label,
    score,
    evaluator_actor,
    model_id,
    configuration_digest,
    evidence_ref,
    created_at
)
```

## 26.2 Evaluator contract

An evaluator contract SHOULD declare:

```json
{
  "evaluator_id": "sol:evaluator/semantic_equivalence/v1",
  "input_schema": "object:sha256:...",
  "output_schema": "object:sha256:...",
  "determinism": "stochastic",
  "guarantee": "heuristic",
  "model_actor": "agent:semantic_matcher_001",
  "configuration_digest": "digest:sha256:...",
  "monotonicity": "unknown",
  "side_effects": "materializes_assessment",
  "rewrite_class": "barrier",
  "evaluation_key_schema": "object:sha256:..."
}
```

## 26.3 Materialized evaluator mode

In materialized mode, the evaluator runs once and creates an immutable assessment relation.

Subsequent logical plans query that relation as ordinary committed or query-run data.

This is the preferred mode for:

- committed results;
- audit-sensitive queries;
- repeated evaluation;
- cross-plan comparison;
- and rewrite-heavy optimization.

## 26.4 Inline evaluator mode

An inline evaluator remains an active boundary in the logical plan.

Unless its contract explicitly states otherwise, an inline evaluator is:

```text
not duplicable
not eliminable
not reorderable across another evaluator
not assumed deterministic
not assumed idempotent
not assumed monotone
```

## 26.5 Deterministic evaluation key

A semantic evaluator appearing in a rewritable plan MUST identify an immutable evaluation result through a complete key containing every input that may affect the output.

The key SHOULD include:

```text
evaluator contract ID
model identity and version
configuration digest
prompt-template digest
tool-policy digest
random seed or sampling identity
source commit
input object or tuple digests
visibility policy
authorization policy
leakage policy
assessment policy
output schema
external service version, where applicable
```

Example:

```json
{
  "evaluation_id": "semantic_eval_041",

  "evaluation_key": {
    "evaluator_id": "sol:evaluator/semantic_equivalence/v1",
    "model_id": "provider/model",
    "model_version": "2026-07-01",
    "configuration_digest": "digest:sha256:...",
    "prompt_template_digest": "digest:sha256:...",
    "tool_policy_digest": "digest:sha256:...",
    "source_commit": "commit:commit_042",
    "input_digests": [
      "digest:sha256:...",
      "digest:sha256:..."
    ],
    "random_seed": 48191,
    "visibility_policy": "policy:internal_full",
    "authorization_policy": "policy:internal_authorized",
    "leakage_policy": "policy:internal_standard",
    "output_schema": "object:sha256:..."
  },

  "result_object": "object:sha256:...",
  "created_by": "agent:semantic_matcher_001"
}
```

All logically repeated invocations with the same evaluation key MUST resolve to the same immutable result object.

A transient cache entry that may expire or vary does not satisfy this rule.

## 26.6 Evaluator guarantees

An evaluator MAY declare:

```text
exact
lower_bound
upper_bound
bounded
heuristic
```

A statistical accuracy statement is not automatically a relational lower or upper bound. The evaluator contract MUST explain how any statistical statement composes into the answer-bound algebra.

An evaluator used as a tuple-preserving semantic `Select` for §13.7.1 MUST declare that it:

- returns only input tuple identities;
- does not synthesize or expand tuples;
- preserves the input schema or a declared identity-preserving projection;
- and evaluates under the same source, temporal, visibility, authorization, and leakage contexts.

A certified-positive contract MUST separately define the conditions under which emitted positive tuples form a lower relation.

## 26.7 Materialization obligation

If a semantic evaluation contributes to a committed query result, its assessment tuples SHOULD be materialized with:

- actor identity;
- model identity and version;
- evaluator contract;
- evaluation key;
- configuration and prompt digests;
- source references and commits;
- result object;
- guarantee and assurance;
- and provenance.

## 26.8 Equality prohibition

The query engine MUST NOT replace exact equality with semantic similarity or entity-resolution output unless the query explicitly asks for a relation defined by that evaluator or policy.

## 26.9 Human judgment

Human review MAY be represented as a semantic evaluator. Human identity, review scope, source state, decision vocabulary, and result MUST be recorded with the same audit discipline applied to model evaluators.

---

# 27. Query Equivalence Contracts

SOL-QRY distinguishes several forms of equivalence:

```text
value-equivalent
multiplicity-equivalent
provenance-equivalent
order-equivalent
bound-equivalent
assurance-equivalent
diagnostic-equivalent
logical-disclosure-equivalent
evaluation-identity-equivalent
physical-side-channel-equivalent
```

Two plans may return the same set of IDs but different provenance.

Two plans may return the same rows while one has certified bounds and the other is heuristic.

Two plans may return the same bag but in different sequence order.

Two plans may disclose different tuple-existence, cardinality, error, or provenance information despite returning the same visible values.

Two physical realizations of the same logical plan may differ in timing, storage reads, cache behavior, resource use, or evaluator invocation count.

A query SHOULD declare which logical dimensions must be preserved:

```json
{
  "required_equivalence": [
    "value",
    "provenance",
    "answer_bounds",
    "logical_disclosure"
  ]
}
```

An optimizer MUST apply only registered rewrites that preserve every requested logical dimension.

A request for `physical-side-channel-equivalent` MUST identify a physical conformance profile. Without such a profile, that dimension is `not_claimed` rather than silently assumed.

---

# 28. Views and Materialized Views

## 28.1 Logical view

A logical view is a named query:

```text
VIEW CurrentVerifiedClaims AS ...
```

## 28.2 Materialized view

A materialized view SHOULD record:

- view identity;
- query identity and digest;
- source manifest;
- result schema;
- lower, upper, or exact result objects;
- dependency closure;
- source commits;
- freshness state;
- provenance mode;
- answer guarantee and assurance;
- creation actor;
- creation run;
- verification state;
- leakage policy.

## 28.3 Machine summary

A Sol machine summary is a natural built-in materialized view over bounded structural read levels.

An evaluator MAY substitute a validated machine summary when:

1. the summary source commit matches the selected source commit;
2. the query references only fields represented by the summary;
3. summary-artifact integrity has been validated;
4. requested provenance, guarantee, assurance, visibility, and leakage semantics are preserved;
5. no omitted record body or object payload is required.

The summary remains derived. It MUST NOT become canonical merely because it is cheaper to read.

## 28.4 Refresh and invalidation

Materialized views MUST become stale when any dependency relevant to their denotation, bounds, provenance, assurance, or policy context changes.

A view MAY be incrementally refreshed if the implementation can preserve the declared result and provenance contract.

## 28.5 View substitution rule

View substitution MUST occur through a registered rewrite rule. The rule MUST establish:

- query containment or equality under the required context;
- source-commit compatibility;
- freshness;
- field coverage;
- bound preservation;
- lower-membership and upper-bound provenance preservation;
- effective assurance preservation;
- logical-disclosure and policy compatibility.

---

# 29. Canonical Query AST and Query Record

## 29.1 Canonical representation

The canonical query form SHOULD be a typed AST stored as a semantic record or registered extension record.

Human-readable syntaxes may compile into the AST. The AST, not the surface syntax, is the unit of:

- canonicalization;
- hashing;
- signing;
- validation;
- plan caching;
- rewrite provenance;
- and execution identity.

## 29.2 Substrait-compatible core

The AST SHOULD map standard relational nodes to Substrait concepts where practical. Sol-specific semantics SHOULD be represented by declared extensions rather than by changing the meaning of standard relational nodes.

Required Sol extension areas include:

```text
commit-pinned sources
commit ancestry
world assumptions
certified answer bounds
structural one-sided bound rules
assurance evidence and dependencies
lower-membership and upper-bound provenance contracts
visibility and authorization policy
logical-disclosure and physical-side-channel policy
valid time
semantic evaluator barriers
materialized assessment relations
```

## 29.3 Query-record example

```json
{
  "record_id": "query_decisions_needing_review",
  "record_type": "sol:record/query",
  "query_version": "0.3",

  "sources": [
    {
      "artifact_id": "art_01j9x7k9k5m2c8v6h3p4q2r1s0",
      "commit_id": "commit:commit_042",
      "alias": "work"
    }
  ],

  "parameters": [],

  "semantics": {
    "collection_kind": "set",
    "world_mode": "asserted",
    "required_guarantee": "exact",
    "provenance": "why",
    "ordering": "unordered",
    "visibility_policy": "policy:internal_full",
    "authorization_policy": "policy:internal_authorized",
    "leakage_policy": "policy:internal_standard"
  },

  "required_equivalence": [
    "value",
    "provenance",
    "answer_bounds",
    "logical_disclosure"
  ],

  "result_schema": [
    {
      "name": "decision_id",
      "type": "Ref<Decision>",
      "optional_state": "required"
    }
  ],

  "expression": {
    "op": "project",
    "fields": ["decision_id"],
    "input": {
      "op": "join",
      "inputs": [
        {"relation": "Decision"},
        {"relation": "DecisionBasis"},
        {
          "op": "select",
          "predicate": {
            "or": [
              {"eq": ["staleness", "stale"]},
              {
                "eq": [
                  "verification",
                  "needs_reverification"
                ]
              }
            ]
          },
          "input": {"relation": "RecordStatus"}
        }
      ]
    }
  },

  "created_by": "agent:query_compiler_001",

  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

## 29.4 Canonicalization

The query AST SHOULD support deterministic canonicalization and hashing.

A query digest SHOULD include:

- canonical expression;
- parameter types and bound values;
- source manifest;
- semantic modes;
- result schema;
- evaluator-contract identities;
- visibility, authorization, leakage, and assessment policies;
- required guarantee;
- required equivalence dimensions.

## 29.5 Extension handling

Unknown required AST extensions MUST cause validation failure. Unknown optional extensions MAY be preserved and ignored only if doing so cannot change the query denotation or requested guarantees.

---

# 30. Query Execution Record

A query execution MAY reuse the Sol run model or use a registered query-run subtype.

A query execution record SHOULD include:

```json
{
  "query_run_id": "query_run_008",
  "query_ref": "record:query_decisions_needing_review",
  "query_digest": "digest:sha256:...",
  "source_manifest": "object:sha256:...",
  "actor_id": "tool:sol_query_engine",
  "status": "success",

  "guarantee": {
    "kind": "exact",
    "result_object": "object:sha256:..."
  },

  "assurance": {
    "status": "validated",
    "effective_status": "validated",
    "evidence": ["record:verification_052"],
    "depends_on": [
      "record:verification_052",
      "sol:rewrite/push_exact_selection_through_join/v1"
    ]
  },

  "provenance_mode": "why",
  "started_at": "2026-07-27T10:00:00Z",
  "completed_at": "2026-07-27T10:00:00.080Z",
  "rows_returned": 3,

  "resource_usage": {
    "records_read": 27,
    "object_bytes_read": 0,
    "semantic_evaluations": 0,
    "wall_time_ms": 80
  },

  "logical_rewrites": [
    {
      "rule_id": "sol:rewrite/push_exact_selection_through_join/v1",
      "location": "/expression/input"
    }
  ]
}
```

## 30.1 Physical-plan recording

The physical plan MAY be recorded for reproducibility or audit, but it MUST NOT define query meaning.

## 30.2 Completion states

A budget-limited execution MAY return:

```text
complete
incomplete_with_continuation
failed
cancelled
```

An incomplete result MUST NOT carry the `exact` guarantee for the complete query unless the evaluator proves that omitted work cannot affect the result.

## 30.3 Continuations

A continuation token MUST bind to:

- the same query digest;
- the same source manifest;
- the same policies;
- the same evaluator identities;
- and the same partial-result state.

A continuation MUST NOT silently resume against a later branch head.

## 30.4 Query execution provenance

A committed query result SHOULD identify:

- source commits;
- query AST and digest;
- parameters;
- applied rewrite rules;
- physical plan, when retained;
- materialized views used;
- semantic evaluations used;
- result bounds;
- lower-membership and upper-bound derivation provenance;
- assurance evidence and effective assurance after staleness;
- actor and environment;
- resource budget and actual usage.

---

# 31. Relation, Evaluator, and Rewrite Catalogs

## 31.1 Relation catalog

A query environment SHOULD expose a relation catalog.

Example base relation declaration:

```json
{
  "relation_id": "sol:relation/RecordStatus",
  "schema": [
    {"name": "record_id", "type": "Ref<Record>"},
    {"name": "lifecycle", "type": "LifecycleStatus"},
    {"name": "staleness", "type": "StalenessStatus"},
    {"name": "verification", "type": "VerificationStatus"}
  ],
  "key": ["record_id"],
  "collection_kind": "set",
  "world_assumption": "closed",
  "completeness": "exact_at_snapshot",
  "temporal_model": "commit_snapshot",
  "lower_provenance_capability": "tuple",
  "upper_derivation_capability": "relation"
}
```

## 31.2 Derived relation catalog

Example derived and materialized relation:

```json
{
  "relation_id": "sol:relation/CurrentSupportingEvidence",
  "definition_query": "record:query_current_supporting_evidence",
  "materialized": true,
  "materialization_object": "object:sha256:...",
  "source_commit": "commit:commit_042",
  "dependencies": [
    "sol:relation/Evidence",
    "sol:relation/Supports",
    "sol:relation/RecordStatus"
  ],
  "staleness": "current",
  "guarantee": "exact"
}
```

## 31.3 Evaluator catalog

The evaluator catalog MUST expose the contract properties required by §26, including evaluation-key schema and rewrite class.

## 31.4 Rewrite catalog

The rewrite catalog MUST expose the rule properties required by §25 and MUST permit validators to determine which rules an optimizer is allowed to apply.

## 31.5 Logical versus physical metadata

Logical relation metadata MUST remain distinct from physical index metadata. Physical indexes, statistics, and access costs belong in SOL-IDX and SOL-PLAN.

---

# 32. Authorization, Redaction, and Leakage Policies

## 32.1 Query actor

A query MUST execute under a declared actor and authorization context.

## 32.2 Logical disclosure dimensions

A leakage policy SHOULD address at least these logical disclosure dimensions:

```text
values
tuple_existence
cardinality
provenance
diagnostics
error_class
unauthorized_reference_behavior
semantic_assessment_visibility
```

These properties can be compared at the logical result and policy-boundary level.

## 32.3 Physical side-channel dimensions

A physical leakage profile MAY address:

```text
timing
resource_usage
access_path
storage_reads
cache_behavior
evaluator_invocation_count
network_observables
```

These are properties of a physical realization, not solely of a logical rewrite pattern.

## 32.4 Example policy

```json
{
  "redaction_policy_id": "policy:restricted_claims",

  "logical_disclosure": {
    "values": "no_disclosure",
    "tuple_existence": "no_disclosure",
    "cardinality": "bucketed",
    "provenance": "redacted",
    "diagnostics": "uniform",
    "error_class": "uniform",
    "unauthorized_reference_behavior": "indistinguishable_from_missing"
  },

  "physical_side_channels": {
    "timing": "best_effort",
    "resource_usage": "suppressed",
    "access_path": "suppressed",
    "evaluator_invocation_count": "suppressed"
  },

  "count_buckets": [
    "0",
    "1-10",
    "11-100",
    "more_than_100"
  ],

  "residual_risk": [
    "correlation_inference_possible",
    "timing_inference_possible"
  ]
}
```

## 32.5 Baseline mandatory mechanisms

A baseline conforming service MUST:

- prevent direct disclosure of protected values;
- apply authorization policy to provenance as well as result values;
- avoid distinguishing nonexistent and unauthorized references unless policy permits it;
- use policy-consistent errors;
- enforce declared cardinality suppression or bucketing;
- suppress or generalize resource, evaluator-invocation, and access-path metadata when required;
- record residual inference risks.

## 32.6 No blanket non-inference claim

Access control alone does not establish general non-inference. A service MUST NOT claim that redacted values are impossible to infer unless it conforms to a profile that defines the adversary model, allowed query history, leakage channels, and verification method.

## 32.7 Provenance visibility

Provenance MAY reveal hidden relationships. A result MUST apply authorization and leakage policy independently to:

- lower-membership provenance;
- upper-bound derivation provenance;
- rewrite and evaluator identities;
- and any extension metadata for upper-only tuples.

## 32.8 Semantic evaluators

A semantic evaluator MUST NOT receive restricted source content unless its actor, model service, environment, and tool policy are authorized for that content.

A policy MAY protect whether an evaluator was invoked, which evaluator was selected, and how many evaluations occurred. Those properties require physical-plan enforcement.

## 32.9 Rewrite restrictions

A rewrite that crosses, removes, duplicates, reorders, or fuses a visibility, authorization, leakage, redaction, error-masking, or semantic-evaluator boundary is non-logical-disclosure-preserving unless a registered rule explicitly proves otherwise.

A rule that does not cross such a boundary MAY still change logical disclosure through cardinality, errors, diagnostics, or provenance and MUST declare those properties.

## 32.10 Physical side-channel claims

Timing, resource usage, storage reads, access paths, cache behavior, and evaluator invocation counts are properties of a physical plan and operator implementation.

A logical rewrite MUST NOT claim to preserve these properties unless a physical conformance profile defines:

- the observable channels;
- the operator implementations or equivalence classes;
- the adversary model;
- and the verification method.

Absent such a profile, physical side-channel preservation is `not_claimed` or `best_effort` as declared.

## 32.11 Safe opening

Querying or rendering a Sol artifact MUST NOT imply executing arbitrary code contained by the artifact.

---

# 33. Worked Examples

## 33.1 Exact decision-review query

Question:

> Return decisions that require review because they depend on a stale claim or a claim needing reverification.

### Set-theoretic denotation

Let:

- `D` be the set of decisions;
- `B ⊆ D × C` be the decision-basis relation;
- `S ⊆ C` be stale claims;
- `N ⊆ C` be claims needing reverification.

Then:

\[
NeedsReview
=
\{d \in D \mid
\exists c [
B(d,c) \land (c \in S \lor c \in N)
]\}
\]

### Relational-calculus form

\[
\{
d \mid
Decision(d)
\land
\exists c[
DecisionBasis(d,c)
\land Claim(c)
\land (
Staleness(c, stale)
\lor
Verification(c, needs\_reverification)
)
]
\}
\]

### Datalog-style form

```text
needs_review(D) :-
    decision(D),
    decision_basis(D, C),
    claim(C),
    record_status(C, _, stale, _).

needs_review(D) :-
    decision(D),
    decision_basis(D, C),
    claim(C),
    record_status(C, _, _, needs_reverification).
```

### Logical-algebra form

\[
\pi_{decision\_id}
\left(
Decision
\bowtie
DecisionBasis
\bowtie
\sigma_{
  staleness = stale
  \lor
  verification = needs\_reverification
}
(RecordStatus)
\right)
\]

### Possible physical executions

```text
status index
→ matching claim IDs
→ reverse decision-basis index
→ decision records
```

or:

```text
validated machine summary
→ status filter
→ decision-basis join
```

or:

```text
scan RecordStatus
→ scan DecisionBasis
→ hash join
```

These plans differ in cost, not meaning.

## 33.2 Bound composition through difference

Suppose query `A` has bounds:

```text
LA ⊆ A ⊆ UA
```

and query `B` has bounds:

```text
LB ⊆ B ⊆ UB
```

For:

```text
A EXCEPT B
```

SOL-QRY derives:

```text
lower = LA EXCEPT UB
upper = UA EXCEPT LB
```

A plan that instead computes `LA EXCEPT LB` as a lower bound is invalid because tuples omitted from `LB` may still belong to exact `B`.

## 33.3 Semantic evaluator materialization

Question:

> Find claims likely equivalent to claim_007.

The query does not replace equality. It first produces or references:

```text
SemanticAssessment(
    evaluation_id,
    claim_007,
    candidate_claim,
    equivalent,
    score,
    ...
)
```

The exact relational query then selects committed assessment tuples satisfying the requested threshold and evaluator contract. That query is exact with respect to the recorded assessment relation.

If the assessment is only heuristic with respect to the target semantic predicate, positive assessment tuples are not automatically a certified lower bound on true equivalence. When the evaluator is a tuple-preserving filter over an exact or upper-bounded candidate relation, §13.7.1 still permits the candidate upper relation to bound all true matches. A sound-positive evaluator contract may additionally certify selected positives as the lower relation.

## 33.4 Budget-limited count

Suppose a query asks for the count of matching claims and execution produces relation bounds `L` and `U` before the budget expires.

The correct result is:

```json
{
  "count_lower": 17,
  "count_upper": 29,
  "guarantee": "bounded",
  "completion": "incomplete_with_continuation"
}
```

It is invalid to return `17` labeled exact.

## 33.5 Provenance-bearing result

```json
{
  "decision_id": "record:decision_002",
  "provenance": {
    "derived_from": [
      "record:decision_002",
      "record:claim_007",
      "record:evidence_011",
      "cell:cell_014#metrics_table"
    ],
    "reason": "claim_needs_reverification"
  }
}
```

## 33.6 Heuristic semantic filter with a certified envelope

Let exact input relation `C` contain all candidate claims and let `p_semantic` be a heuristic relevance predicate.

Even if the evaluator certifies no positive matches:

\[
\varnothing
\subseteq
Select(p_{semantic},C)
\subseteq
C
\]

The result may therefore serialize:

```json
{
  "guarantee": {
    "kind": "bounded",
    "lower_object": "object:empty-claims",
    "upper_object": "object:all-candidates"
  },
  "assurance": {
    "status": "proven",
    "rule_id": "sol:bound/tuple_preserving_select_upper/v1"
  }
}
```

Heuristic candidate matches may be returned separately, but they do not enter the certified lower relation unless the evaluator contract establishes sound positive classifications.

## 33.7 Stratified recursive bounds

Suppose `reachable` is computed recursively and `blocked` is consumed negatively in a higher stratum:

```text
reachable(X) :- seed(X).
reachable(Y) :- reachable(X), edge(X, Y).
allowed(X) :- reachable(X), not blocked(X).
```

After computing lower and upper fixed points for `reachable`, the higher stratum applies difference:

```text
lower_allowed = lower_reachable EXCEPT upper_blocked
upper_allowed = upper_reachable EXCEPT lower_blocked
```

The negative relation is fully computed before use. A plan that feeds a partially evaluated `blocked` relation into the higher stratum is invalid.

## 33.8 Bounded-result provenance

For:

```text
L = {claim_007}
U = {claim_007, claim_011}
```

`claim_007` may carry ordinary why-provenance showing the exact evidence and transfer rules that certify membership.

`claim_011` MUST NOT carry the same assertion. It may carry upper-bound derivation such as:

```json
{
  "tuple": "record:claim_011",
  "bound_position": "upper_only",
  "upper_derivation": {
    "rule_id": "sol:bound/tuple_preserving_select_upper/v1",
    "source_upper": "object:all-candidates"
  }
}
```

This says why the tuple has not been excluded, not why it is an exact answer.

## 33.9 Certified AVG interval

Let mandatory values be:

```text
L = {4, 10}
```

and optional values be:

```text
O = {-8, 6, 20}
```

The minimum checks ascending prefixes:

```text
(14)/2
(14-8)/3
(14-8+6)/4
(14-8+6+20)/5
```

The maximum checks descending prefixes:

```text
(14)/2
(14+20)/3
(14+20+6)/4
(14+20+6-8)/5
```

The minimum and maximum of those finite candidate lists form the certified interval under `sol:bound/avg_optional_prefix/v1`.

---

# 34. Conformance Roles

## 34.1 Query Reader

A Query Reader can parse and inspect query records, source manifests, result schemas, semantic modes, bound requirements, policies, and query digests without executing them.

## 34.2 Query Validator

A Query Validator can validate:

- source coordinates;
- type correctness;
- relation and field resolution;
- safe variable binding;
- finite-domain requirements;
- legal negation;
- declared collection semantics;
- evaluator contracts and evaluation keys;
- result-schema compatibility;
- bound composition, including one-sided structural bounds;
- lower-membership and upper-bound derivation provenance;
- assurance dependency and staleness;
- rewrite-rule legality and proof-evidence class;
- logical-disclosure and physical-side-channel policy declarations;
- authorization metadata;
- canonicalization and digest integrity.

## 34.3 Query Compiler

A Query Compiler can translate a supported surface syntax into the canonical typed AST without changing the denotation.

## 34.4 Logical Planner

A Logical Planner can translate the canonical AST into logical algebra and apply registered rewrite rules.

## 34.5 Query Evaluator

A Query Evaluator can evaluate supported logical plans against commit-pinned sources and produce query execution records and result objects.

## 34.6 Bound-Capable Evaluator

A Bound-Capable Evaluator can propagate certified lower and upper relations independently through every supported inexact operator, apply structural one-sided rules, compute supported aggregate intervals, and produce validation evidence.

## 34.7 Materialized View Maintainer

A Materialized View Maintainer can create, validate, invalidate, and refresh materialized query results while preserving their source, dependency, provenance, policy, and guarantee contracts.

## 34.8 Rewrite Registry Consumer

A Rewrite Registry Consumer can validate rule identity, preconditions, preservation properties, proof-evidence classes, assurance freshness, policy-boundary behavior, and applied-rule provenance.

---

# 35. Proposed Validation Rules

Stable rule identifiers are recommended.

## QV0 — Syntax and Type System

```text
QV0-01  Query record parses and version is recognized.
QV0-02  Every relation, field, type, evaluator, and policy resolves.
QV0-03  Expression is type-correct.
QV0-04  Result schema matches expression output.
QV0-05  Query canonicalization and digest verify.
QV0-06  Unknown required extensions fail validation.
```

## QV1 — Source Semantics

```text
QV1-01  Every source resolves to an artifact and commit.
QV1-02  Branch references are resolved to commits before evaluation.
QV1-03  Source manifest is immutable for one execution.
QV1-04  Visibility, leakage, and authorization policies are declared.
QV1-05  Lower and upper relations use compatible source manifests.
```

## QV2 — Safety and Expressiveness

```text
QV2-01  Every output variable is positively or finitely bound.
QV2-02  Variables in negated subexpressions are bound outside them.
QV2-03  Aggregates range over finite relations.
QV2-04  Recursive rules conform to least-fixed-point and stratification rules.
QV2-05  No unsafe unbounded value generation.
QV2-06  Core query uses no recursion through negation or aggregation.
QV2-07  Complement names an explicit finite exact domain.
```

## QV3 — Set and Order Semantics

```text
QV3-01  Collection kind is declared or defaults to set.
QV3-02  Bag conversion is explicit.
QV3-03  Ordered result has a deterministic total order when required.
QV3-04  Limit is applied only to a sequence or marked nondeterministic.
QV3-05  Inexact top-k or limit has a registered position-certainty rule
         or is labeled heuristic.
```

## QV4 — Negation and Completeness

```text
QV4-01  Difference operands have compatible source and policy contexts.
QV4-02  Classical exact negation does not cross an open or incomplete boundary.
QV4-03  Assertion absence is not mislabeled epistemic negation.
QV4-04  Bounded difference uses lower-left/upper-right and upper-left/lower-right rules.
QV4-05  Completeness assertion is current and covers the negated predicate region.
QV4-06  Stratified negation consumes a fully evaluated lower stratum.
```

## QV5 — Answer Bounds and Assurance

```text
QV5-01  Every bounded result satisfies lower ⊆ upper.
QV5-02  Every certified side has a normative or registered transfer rule.
QV5-03  Guarantee kind matches the concrete available and unavailable bound sides.
QV5-04  Assurance status is present and supported as declared.
QV5-05  COUNT bounds equal |lower| and |upper| for set input.
QV5-06  Unsupported aggregate composition is rejected or downgraded to heuristic.
QV5-07  Budget truncation weakens the guarantee or marks the result incomplete.
QV5-08  A heuristic input or predicate contributes to a certified output side
         only through a normative or registered rule; heuristic candidate
         membership is not silently certified.
QV5-09  Structural one-sided bounds satisfy the declared containment relation,
         tuple-preservation contract, and context compatibility.
QV5-10  A stale or unverifiable assurance dependency makes effective assurance unknown.
QV5-11  Tighter registered bounds are accepted when their proof obligations hold.
QV5-12  Certified AVG intervals satisfy sol:bound/avg_optional_prefix/v1 or
         another supported rule with equal or stronger validity guarantees.
```

## QV6 — Semantic Evaluators

```text
QV6-01  Evaluator has a registered input and output schema.
QV6-02  Actor, model, version, configuration, and policy identity are recorded.
QV6-03  Rewritable evaluator has a complete deterministic evaluation key
         or references an immutable materialized assessment.
QV6-04  Stochastic or heuristic evaluation is not labeled exact without proof.
QV6-05  Rewrites do not duplicate, eliminate, or reorder evaluator calls illegally.
QV6-06  Committed semantic results are materialized or otherwise auditable.
QV6-07  An evaluator used as tuple-preserving Select does not invent tuples,
         alter tuple identity, or expand tuple cardinality.
```

## QV7 — Rewrite Rules

```text
QV7-01  Every applied rewrite has a registered rule ID.
QV7-02  Every rule precondition held at application time.
QV7-03  Rule preservation contract covers query-required logical equivalence dimensions.
QV7-04  Rule proof or verification evidence is supported and current.
QV7-05  Applied-rule provenance identifies expression location.
QV7-06  Experimental unverified rule cannot support exact or certified output by itself.
QV7-07  A rewrite spanning a policy or evaluator boundary has an explicit
         logical-disclosure preservation proof.
QV7-08  Assurance level is compatible with the classified proof-evidence forms.
QV7-09  Physical side-channel equivalence is not claimed without a conforming
         physical profile.
```

## QV8 — Provenance and Views

```text
QV8-01  Requested provenance mode is supported.
QV8-02  View substitution preserves value, bounds, provenance, policy, and freshness.
QV8-03  Materialized view source commits match or are validly reconciled.
QV8-04  Machine summary substitution is field-complete for the query.
QV8-05  Every lower-bound tuple carries the requested supported membership provenance.
QV8-06  Every bound object records required source bounds, transfer rules,
         contexts, evaluators, views, and rewrites.
QV8-07  An upper-only tuple is not represented as positively proven exact-answer membership.
QV8-08  Provenance disclosure obeys the selected authorization and leakage policy.
```

## QV9 — Leakage and Authorization

```text
QV9-01  Query actor is authorized for every source and evaluator input.
QV9-02  Values and tuple existence obey declared logical-disclosure policy.
QV9-03  Cardinality is suppressed, bucketed, or disclosed as declared.
QV9-04  Lower, upper, evaluator, and rewrite provenance obey independent visibility rules.
QV9-05  Errors and unauthorized-reference behavior obey policy.
QV9-06  Resource, timing, access-path, storage-read, and evaluator-invocation
         metadata obey the declared physical profile or are marked not_claimed.
QV9-07  Result records residual inference risks.
QV9-08  No general non-inference claim appears without a conforming profile.
QV9-09  Logical rewrites crossing policy boundaries are rejected unless explicitly proven.
QV9-10  A logical rewrite does not claim physical side-channel preservation by default.
```

---

# 36. Query Pathology Corpus

Each corpus entry SHOULD contain:

```text
query_case/
  source_artifacts/
  query.json
  expected_result.json
  expected_diagnostics.json
  README.md
```

Diagnostics SHOULD include:

```text
rule_id
category
severity
target
message
```

## 36.1 Golden cases

```text
QGOLD-001  Exact snapshot query over one artifact.
QGOLD-002  Exact join with tuple provenance.
QGOLD-003  Positive recursive dependency closure.
QGOLD-004  Stratified negation licensed by a local completeness assertion.
QGOLD-005  Exact machine-summary substitution with matching source commit.
QGOLD-006  Bounded union with correctly propagated lower and upper relations.
QGOLD-007  Bounded difference using L1\U2 and U1\L2.
QGOLD-008  COUNT_SET interval derived from relation bounds.
QGOLD-009  Materialized semantic assessment queried as ordinary data.
QGOLD-010  Registered rewrite with complete precondition and proof metadata.
QGOLD-011  Leakage policy with redacted values and bucketed cardinality.
QGOLD-012  Incomplete execution with continuation and honest bounded result.
QGOLD-013  Heuristic tuple-preserving semantic filter over exact input returns
           lower = typed empty and upper = input.
QGOLD-014  Semantic filter with certified positive classifications returns those
           positives as lower and the input upper as upper.
QGOLD-015  Intersection with one heuristic operand retains a certified upper
           from the other operand.
QGOLD-016  Difference with a heuristic right operand retains the certified
           upper relation of the left operand.
QGOLD-017  Positive recursive lower and upper fixed points feed a stratified
           difference with correctly swapped negative sides.
QGOLD-018  Bounded result carries membership provenance for lower tuples and
           bound-derivation provenance for the upper relation.
QGOLD-019  A tighter registered bound than the normative baseline is accepted.
QGOLD-020  sol:bound/avg_optional_prefix/v1 returns a certified interval and
           correctly records possible emptiness when lower is empty.
QGOLD-021  A policy-boundary rewrite with an explicit accepted disclosure proof
           is applied and recorded.
```

## 36.2 Pathological cases

```text
QPATH-001  The moving branch
           Query begins on branch main but records no resolved commit.
           Expected: QV1-02, QV1-03.

QPATH-002  The semantic equality forgery
           Vector similarity is substituted for exact `=`.
           Expected: QINV-04, QV6-04.

QPATH-003  The false exact result
           Approximate nearest-neighbor retrieval returns top-k rows labeled exact.
           Expected: QINV-06, QV5-03.

QPATH-004  The open-world negation
           Exact NOT EXISTS is used against externally incomplete evidence.
           Expected: QV4-02.

QPATH-005  The hidden redaction leak
           Raw COUNT reveals the number of restricted records under a bucketed policy.
           Expected: QV9-03.

QPATH-006  The unordered top ten
           LIMIT 10 is committed without deterministic ordering.
           Expected: QV3-04.

QPATH-007  The duplicated stochastic call
           Optimizer duplicates an inline stochastic evaluator.
           Expected: QV6-05, QV7-03.

QPATH-008  The stale materialized view
           A view from commit 41 answers a query pinned to commit 42.
           Expected: QV8-03.

QPATH-009  The truth-status collapse
           verification = unverified is rewritten as proposition = false.
           Expected: QINV-05.

QPATH-010  The unresolved object masquerade
           A named output is compared directly to an immutable object reference.
           Expected: type error under QV0-03.

QPATH-011  The unsafe universe
           Query asks for every value that is not a claim.
           Expected: QV2-01, QV2-05.

QPATH-012  The incomplete exact count
           Budget stops after 1000 records but COUNT is labeled exact.
           Expected: QV5-07.

QPATH-013  The provenance-dropping rewrite
           Rewrite returns value-equivalent rows but loses required lower-membership lineage.
           Expected: QV7-03, QV8-05.

QPATH-014  The timestamp time traveler
           Latest commit is selected by timestamp across divergent branches.
           Expected: temporal validation failure.

QPATH-015  The bag-set confusion
           Projection under bag semantics is treated as duplicate-eliminating
           without an explicit Distinct.
           Expected: QV3-02.

QPATH-016  The invalid lower difference
           LA EXCEPT LB is reported as a lower bound for A EXCEPT B.
           Expected: QV4-04, QV5-02.

QPATH-017  The unswapped negation
           Complement uses D\L as a lower bound instead of D\U.
           Expected: QV4-04, QV5-02.

QPATH-018  The friendly-label planner
           Planner composes lower_bound and upper_bound labels without concrete
           bound relations.
           Expected: QV5-02, QV5-03.

QPATH-019  The average fiction
           AVG over an inexact relation is labeled with a scalar lower_bound
           without a registered interval rule.
           Expected: QV5-06, QV5-12.

QPATH-020  The heuristic resurrection
           Heuristic semantic membership passes through a join and output is labeled exact.
           Expected: QV5-08.

QPATH-021  The unregistered rewrite
           Optimizer applies a transformation with no rule ID.
           Expected: QV7-01.

QPATH-022  The unmet precondition
           Selection pushdown crosses a stochastic evaluator barrier.
           Expected: QV7-02, QV6-05.

QPATH-023  The stale proof
           Rewrite rule relies on a verification whose dependencies are stale,
           but assurance remains validated.
           Expected: QV5-10, QV7-04.

QPATH-024  The transient memo
           Evaluator is declared deterministic-per-key, but repeated calls may
           recompute different results after cache eviction.
           Expected: QINV-13, QV6-03.

QPATH-025  The incomplete evaluation key
           Prompt-template digest is omitted from a semantic evaluator key.
           Expected: QV6-03.

QPATH-026  The policy-crossing rewrite
           Plan moves a filter across an authorization boundary and changes tuple
           existence disclosure.
           Expected: QV7-07, QV9-09.

QPATH-027  The verbose denial
           Error distinguishes nonexistent and unauthorized record IDs contrary
           to policy.
           Expected: QV9-05.

QPATH-028  The provenance side door
           Values are redacted but provenance reveals restricted record identities.
           Expected: QV8-08, QV9-04.

QPATH-029  The timing promise
           Service claims general non-inference while declaring timing protection
           only best-effort.
           Expected: QV9-08.

QPATH-030  The mismatched bounds
           Lower and upper relations come from different commits.
           Expected: QV1-05.

QPATH-031  The inverted bounds
           Lower relation contains a tuple absent from upper relation.
           Expected: QV5-01.

QPATH-032  The top-k certainty illusion
           An upper-bounded input is sorted and limited without a position-certainty rule.
           Expected: QV3-05.

QPATH-033  The hidden heuristic view
           Materialized view was produced heuristically but substituted into an
           exact query.
           Expected: QV8-02.

QPATH-034  The lossy summary
           Machine summary omits a field required by the query but is used as a
           covering exact view.
           Expected: QV8-04.

QPATH-035  The continuation drift
           Continuation resumes against a later branch head.
           Expected: QV1-03, continuation validation failure.

QPATH-036  The experimental theorem
           An unverified rewrite rule is the sole basis for an exact result.
           Expected: QV7-06.

QPATH-037  The possible-as-proven tuple
           A tuple occurring only in U is given ordinary why-provenance asserting
           exact-answer membership.
           Expected: QINV-14, QV8-07.

QPATH-038  The missing upper derivation
           A bounded result has an upper object but no transfer rule or source-bound
           provenance for it.
           Expected: QV8-06.

QPATH-039  The policy-boundary default bypass
           A rewrite spans a LeakagePolicy node with no explicit disclosure proof,
           even though visible values happen to match in the fixture.
           Expected: QINV-15, QV7-07.

QPATH-040  The fabricated selector
           A tuple-generating LLM operator is modeled as Select and inherits the
           input relation as an upper bound.
           Expected: QV5-09, QV6-07.

QPATH-041  The prose theorem
           A rewrite marks assurance as proven using only an unchecked prose reference.
           Expected: QV7-08.

QPATH-042  The invalid AVG prefix
           AVG interval omits an extremal optional prefix and excludes a feasible mean.
           Expected: QV5-12.

QPATH-043  The physical-leakage shortcut
           A logical rewrite declares evaluator-invocation-count equivalence without
           a physical conformance profile.
           Expected: QV7-09, QV9-10.
```

## 36.3 Corpus discipline

Every semantic defect discovered during implementation SHOULD become one of:

```text
erratum
new corpus entry
unfreeze candidate
```

The corpus SHOULD be treated as executable specification support rather than as illustrative documentation only.

Every mandatory rewrite rule SHOULD have at least one adversarial corpus case that fails when a required precondition is removed.

---

# 37. Reference Implementation Order

The initial implementation SHOULD prioritize semantic executability over physical optimization.

## 37.1 Phase 1 — Answer-bound algebra and bound provenance

Implement:

- lower and upper relation objects;
- componentwise and structural one-sided transfer rules;
- guarantee and assurance serialization;
- assurance dependencies and stale-assurance downgrade;
- validation of `lower ⊆ upper`;
- lower-membership and upper-bound derivation provenance;
- COUNT_SET, SUM, MIN, MAX, and `sol:bound/avg_optional_prefix/v1`;
- valid-versus-tight registered-rule acceptance;
- guarantee and provenance pathologies.

This phase is blocking because the remainder of the system cannot honestly label or explain inexact results without it.

## 37.2 Phase 2 — Typed AST and canonicalization

Implement:

- typed AST schema;
- deterministic canonicalization;
- query digests;
- source manifests;
- explicit policy-boundary nodes;
- Substrait mapping for standard nodes;
- Sol extension declarations.

## 37.3 Phase 3 — Exact evaluator over exploded artifacts

Implement scans over RFC-SOL-0001’s exploded debug representation.

The first evaluator does not need physical indexes. Correct scans over one artifact are sufficient to validate semantics.

## 37.4 Phase 4 — Rewrite registry and proof kernel

Implement a small rule library:

- exact selection pushdown;
- exact projection pruning;
- exact join associativity under declared conditions;
- union normalization;
- machine-summary view substitution.

Each mandatory rule MUST have:

- a registered rule ID;
- explicit preconditions and preservation dimensions;
- a human-readable derivation;
- machine-checkable property tests;
- at least one adversarial corpus case;
- and classified proof or verification evidence.

Mechanized proofs or checked certificates SHOULD be produced for this initial small rule kernel.

## 37.5 Phase 5 — Query pathology corpus

Run the validator and evaluator against every golden and pathological case. Diagnostics SHOULD be deterministic:

```text
same source + same query → same diagnostics → same ordering
```

## 37.6 Phase 6 — Materialized and bounded semantic evaluator

Implement one semantic evaluator end-to-end in two modes:

```text
finite input relation
→ complete evaluation key
→ immutable assessment object
→ assessment relation
→ ordinary exact query over that relation
```

and:

```text
exact or upper-bounded candidate relation
→ tuple-preserving heuristic semantic filter
→ certified empty or sound-positive lower
→ certified input-derived upper
```

This phase should demonstrate why materialized assessment is distinct from transient retrieval and why a heuristic predicate need not destroy every certified side.

## 37.7 Phase 7 — Machine-summary substitution

Demonstrate that eligible queries can be answered exactly from Levels 0–2 while ineligible queries are rejected or fetch deeper levels.

## 37.8 Phase 8 — SOL-IDX, SOL-PLAN, and physical leakage profiles

Only after the preceding phases pass should implementation proceed to:

- physical indexes;
- statistics;
- cost models;
- join algorithms;
- adaptive planning;
- paging and cache integration;
- and physical side-channel conformance profiles.

Physical optimization should improve a known-correct query engine rather than define its semantics.

---

# 38. Prior-Art and Terminology Map

This section is non-normative. It positions SOL-QRY relative to established fields and nearby systems. No listed system is a normative dependency.

## 38.1 Terminology translation

| SOL-QRY term | Field-standard analogue |
|---|---|
| Commit-pinned source; artifact time versus valid time | Bitemporal semantics; transaction time versus valid time; as-of queries |
| Lower and upper answer bounds | Sound and complete approximations; certain and possible answers |
| Open and closed relation declarations | Open-world assumption, closed-world assumption, local closed-world assumption, completeness assertions |
| Policy-scoped visibility | Fine-grained access control; filtered database views |
| Missing-value taxonomy | Multiple null marks; incomplete-information models |
| Four-state support model | Belnap-style four-valued logic and bilattices |
| Assertion versus accepted fact | Reification, named graphs, annotated knowledge bases, curation policy |
| Semantic evaluator | Semantic operator; learned predicate; ML-as-UDF |
| Canonical typed AST | Query intermediate representation |
| Tuple, why, and how provenance | Lineage and provenance semirings |
| Machine-summary substitution | Answering queries using views; view-based rewriting with freshness |
| Registered rewrite rules | Volcano/Cascades/Calcite-style rule systems and traits |
| Lower-membership versus upper-bound derivation provenance | Positive derivation provenance versus proof of enclosure or possibility |
| Assurance dependencies and stale assurance | Verification lineage and dependency-driven invalidation |
| Logical disclosure versus physical side-channel class | Access-control disclosure semantics versus implementation-level side channels |

## 38.2 Commit-pinned immutable databases

Datomic and XTDB demonstrate queries as functions of immutable database values, including history and as-of querying. Dolt, TerminusDB, and Fluree demonstrate versioned or branching data and commit-aware query behavior.

SOL-QRY generalizes the pinned-database-value idea to a federated manifest of computational artifacts whose records include claims, evidence, verification, staleness, provenance, actors, and runs.

## 38.3 Query IR and optimizer frameworks

Substrait demonstrates cross-engine logical-plan interchange. Apache Calcite demonstrates a logical algebra and registered equivalence-preserving rule system.

SOL-QRY SHOULD borrow their structural vocabulary where compatible while retaining independent semantics for commit pinning, epistemic state, answer bounds, leakage policy, and semantic-evaluator barriers.

## 38.4 Provenance-enabled engines

ProvSQL, GProM, and Perm demonstrate practical provenance-enabled relational evaluation. Their treatment of negation, difference, and aggregation illustrates why SOL-QRY restricts provenance guarantees for those operators to registered rules.

## 38.5 Completeness reasoning

Research on relative completeness, completeness statements, and obtaining complete answers from incomplete databases is directly relevant to QINV-09 and local completeness assertions.

SOL-QRY should reuse this body of results rather than treating every closed-world license as a bespoke Sol concept.

## 38.6 Approximate query processing

Online aggregation and systems such as BlinkDB demonstrate bounded-error or bounded-time query contracts.

SOL-QRY differs by making relation bounds, provenance, commit pinning, and semantic evaluators part of the same query contract.

## 38.7 Semantic and LLM query operators

LOTUS, Palimpzest, DocETL, ZenDB, Evaporate, and related work treat model calls as cost-bearing semantic operators rather than opaque application logic.

SOL-QRY adopts that direction but requires semantic results to be typed, attributed, commit-relative, policy-scoped, and either materialized or deterministically keyed before ordinary optimizer rewrites apply.

## 38.8 Consistent query answering

Consistent query answering provides formal machinery for certain answers over inconsistent or repaired data. This is relevant to future `CERTAIN UNDER <policy>` profiles and the distinction between stored assertions and policy-accepted facts.

## 38.9 Classical foundations

The relational model, relational calculus, relational algebra, Datalog, temporal databases, incomplete-information databases, and provenance semirings remain the principal mathematical foundations.

---

# 39. Feasibility and Known Limits

## 39.1 Feasible core

The core profile—commit-pinned finite sources, safe relational calculus, positive recursive Datalog, stratified negation, and nonrecursive aggregation—has mature evaluation strategies.

The primary engineering task is integration with Sol’s artifact model, not invention of a new general query theory.

## 39.2 Guarantee composition

Guarantee composition is normative in v0.3.

The current rules cover ordinary set-valued positive operators, structural one-sided containment, difference, finite complement, positive recursion, stratified negative use, and selected aggregates.

Every additional operator must define its bound transfer. A heuristic contribution does not force a blanket heuristic result when an independent structural rule certifies one side.

## 39.3 Bound provenance

Lower-membership provenance is tractable for the supported positive core and registered rules. Upper-bound derivation provenance is relation-level proof of enclosure, not proof that every upper-only tuple belongs.

Per-tuple explanations for `U \ L` remain an extension area.

## 39.4 Equivalence

Arbitrary equivalence checking is outside scope. Registered rewrite rules turn an undecidable general requirement into a finite conformance problem.

The registry is meaningful only if proof evidence is classified and current. Property tests are necessary engineering evidence but are not universal proofs.

## 39.5 Leakage control

General non-inference is not solved by access control. SOL-QRY therefore specifies declared logical-disclosure classes, conservative policy-boundary rules, physical side-channel profiles, mandatory baseline controls, and residual-risk disclosure rather than a universal secrecy theorem.

## 39.6 Semantic evaluators

A stochastic evaluator can break ordinary algebraic assumptions. Immutable materialized assessments and complete evaluation keys restore a stable object for query processing, but they do not make the evaluator semantically exact.

Tuple-preserving semantic filters nevertheless admit structural upper bounds inherited from their candidate relation.

## 39.7 Aggregate bounds

Finite exact-valued lower and upper sets support certified intervals for COUNT_SET, SUM, MIN, MAX, and the registered optional-prefix AVG rule.

Other aggregates require their own rules and preconditions.

## 39.8 Specification weight

A large specification without an executable validator risks becoming decorative. The typed AST, exact scan evaluator, bound algebra, bound provenance, rewrite kernel, and pathology corpus are therefore part of the freeze gate.

---

# 40. Novelty Delta

SOL-QRY does not claim novelty for:

- relational calculus;
- relational algebra;
- Datalog;
- bitemporal querying;
- immutable database values;
- provenance semirings;
- approximate query processing;
- rule-based query optimization;
- or semantic model operators individually.

The defensible contribution is the integration of:

1. **commit-pinned and bitemporal query semantics** over versioned computational artifacts;
2. **an epistemically stratified schema** in which assertion, support, verification, staleness, availability, confidence, and acceptance are normatively orthogonal;
3. **learned evaluators and execution budgets** incorporated into a certified answer-bound calculus rather than bolted onto retrieval;
4. **provenance and actor attribution** across exact operators, semantic assessments, rewrites, views, and query executions;
5. **bounded structural reads** that permit a query engine to exploit artifact summaries without allowing summaries to redefine truth.

The intended positioning is:

> Not an LLM connected to a database, but an LLM as one class of semantic operator inside a typed, versioned, provenance-preserving information architecture.

The novelty is architectural synthesis plus the normative invariant set, not any single mechanism.

---

# 41. Recommended v0.3 Scope

## 41.1 Include

A rigorous v0.3 SHOULD include:

1. pinned single-artifact sources;
2. small explicitly pinned federations;
3. normalized logical relations for core Sol entities;
4. typed scalar and reference values;
5. exact set semantics by default;
6. explicit exact bag and sequence conversion;
7. safe relational calculus;
8. the expressiveness profile in §6;
9. canonical logical-algebra AST;
10. selection, projection, rename, join, union, and intersection;
11. bounded difference and finite complement;
12. positive recursion and stratified negation;
13. exact aggregation plus the bound rules in §13;
14. structural one-sided bounds for tuple-preserving and containment-declared operators;
15. `sol:bound/avg_optional_prefix/v1` for claimed inexact AVG support;
16. commit-time and basic valid-time predicates;
17. typed query parameters and result schemas;
18. query canonicalization and digesting;
19. concrete lower and upper relation objects;
20. separate assurance metadata and dependency-driven assurance staleness;
21. lower-membership and upper-bound derivation provenance;
22. registered rewrite rules with classified proof evidence;
23. conservative policy-boundary rewrite semantics;
24. read-only evaluation;
25. materialized semantic-assessment contracts;
26. complete evaluator keys for rewritable plans;
27. validated machine-summary substitution;
28. declared logical-disclosure and physical-side-channel policies;
29. an executable query pathology corpus;
30. an exact reference evaluator over exploded Sol artifacts.

## 41.2 Defer

The following SHOULD be deferred:

- general probabilistic databases;
- unrestricted possible-world inference;
- unrestricted recursion through negation;
- recursion through aggregation;
- complete provenance through every form of negation and aggregation;
- normative per-tuple possibility explanations for `U \ L`;
- automatic entity resolution as identity;
- unrestricted natural-language query semantics;
- mutation statements;
- cost-based physical optimization;
- distributed query scheduling;
- physical page and cache policy;
- learned plan selection;
- approximate bag-bound semantics;
- general differential privacy;
- global catalog administration.

---

# 42. Companion Specifications

The following split preserves architectural boundaries.

## SOL-QRY

```text
Set-theoretic model
Typed logical schema
Declarative calculus
Logical algebra
Certified answer bounds and structural one-sided rules
Bound-aware provenance
Assurance dependencies and staleness
Rewrite-rule contracts
Query and result serialization
```

## SOL-IDX

```text
Index definitions
Index coverage
Statistics
Cardinality and selectivity
Approximation contracts
Recall and false-positive guarantees
```

## SOL-PLAN

```text
Registered logical rewrites
Cost model
Physical operators
Join strategies
View substitution
Adaptive replanning
Semantic-operator scheduling
```

## SOL-MEM

```text
Pages and blocks
Residency tiers
Buffer pool
Prefetching
Pinning
Eviction
Fault handling
Read amplification
```

## SOL-SEM

```text
Semantic evaluators
Entity resolution
Claim assessment policies
Contradiction and support models
Confidence and uncertainty
Possible-world profiles
Statistical guarantee adapters
```

## SOL-FED

```text
Cross-artifact catalog
Federated snapshots
Identity reconciliation
Distributed authorization
Query routing
Lineage selection
```

## SOL-PRIV

```text
Logical-disclosure profiles
Physical side-channel profiles
Inference-control assumptions
Cardinality protection
Differential privacy profiles
Query-history controls
Privacy verification
```

---

# 43. Open Questions

## 43.1 v0.3 blocking

1. What exact normalized base relations are mandatory?
2. What canonical schema language defines relation and type catalogs?
3. What exact AST encoding and Substrait mapping are required?
4. How are lower and upper relation objects serialized efficiently?
5. What proof artifact formats qualify as mechanized proofs, checked certificates, or accepted formal derivations?
6. Which rewrite rules are mandatory for baseline optimizer conformance?
7. What is the minimum lower-membership provenance mode?
8. What exact upper-bound derivation fields are mandatory?
9. What exact semantics should local completeness assertions use?
10. What minimum valid-time model is required?
11. Should query executions reuse `run` directly or use a registered subtype?
12. What exact result-object format is required?
13. What minimum logical-disclosure policy profile is mandatory?
14. Which physical side-channel profile, if any, is mandatory for a baseline service?
15. Which evaluation-key fields are universally mandatory versus evaluator-specific?
16. Which aggregate-bound rules are mandatory beyond COUNT_SET, SUM, MIN, MAX, and optional-prefix AVG?
17. Which evidence forms are sufficient for each assurance status under the baseline profile?
18. Which machine-summary fields are sufficient for the first exact substitution rules?
19. What reference syntax identifies rewrite rules, bound rules, evaluators, and policies?
20. Which golden and pathological cases are mandatory before freeze?

## 43.2 Post-v0.3

1. Should possible-world query modes become normative?
2. Should probabilistic annotations be standardized?
3. Should four-state claim assessment be part of SOL-SEM?
4. How should provenance interact with general negation and aggregation?
5. How should per-tuple possibility explanations for `U \ L` be standardized?
6. Should query-plan attestations be signable?
7. How should incremental view maintenance be standardized?
8. How should cross-artifact canonical identities be reconciled?
9. Should natural-language query compilation have a verification profile?
10. How should distributed partial results compose?
11. Should adaptive semantic evaluation produce reusable learned statistics?
12. How should approximate bag multiplicities be bounded?
13. Which privacy profiles should support repeated-query accounting?

---

# 44. v0.3 Freeze Gate

SOL-QRY MUST NOT be marked frozen until all of the following are complete:

```text
1. Bound-transfer rules are defined for every core logical operator.
2. Unsupported guarantee compositions deterministically reject or downgrade.
3. Canonical typed AST and canonicalization schemas are published.
4. At least one Substrait mapping profile is documented.
5. Rewrite-rule registration, proof-evidence classes, and assurance obligations are implemented.
6. Logical-disclosure baseline and validator rules are implemented.
7. Semantic evaluator materialization and evaluation-key contracts are implemented.
8. Exact evaluator runs over the exploded RFC-SOL-0001 representation.
9. Machine-summary substitution succeeds only for proven covering queries.
10. Every mandatory golden and pathological case passes with deterministic diagnostics.
11. Query and execution records validate against published schemas.
12. At least one end-to-end bounded query demonstrates honest budget degradation.
13. Structural one-sided bounds are implemented and pass QGOLD-013 through QGOLD-016.
14. Bounded-result provenance distinguishes lower-membership certification from
    upper-bound derivation and upper-only non-exclusion.
15. Assurance evidence participates in ordinary Sol staleness propagation, and
    stale assurance evaluates effectively as unknown.
16. Rewrites spanning policy or evaluator boundaries default to non-preserving
    unless explicitly proven.
17. sol:bound/avg_optional_prefix/v1 or an equal-or-stronger registered AVG rule
    passes its golden and pathological cases when inexact AVG support is claimed.
18. The mandatory rewrite kernel has machine-checkable property tests and at
    least one adversarial corpus case per rule; claimed proven rules meet the
    accepted proof-artifact profile.
19. Logical and physical leakage claims are separated, and no physical
    side-channel equivalence is inferred from logical rewriting alone.
```

Findings during the frozen implementation period SHOULD be triaged as:

```text
errata
corpus entry
unfreeze candidate
```

Unfreeze candidates SHOULD be accumulated and batched into the next semantic revision rather than changing the specification for every implementation surprise.

---

# 45. Summary

SOL-QRY proposes a database-grade semantic foundation for querying Sol artifacts.

Its principal commitments are:

```text
Committed Sol state denotes a finite logical database instance.
Every query is evaluated against pinned source commits.
Set semantics is the default.
Bag and sequence semantics are explicit.
Exact identity is not semantic similarity.
Artifact assertions are not automatically world facts.
Staleness, verification, confidence, availability, and truth are distinct.
Negation requires completeness or a certified bound rule.
Time has artifact-history and world-validity dimensions.
Queries are declarative and read-only.
Logical algebra is not a physical execution plan.
Rewrites come from registered rules, not arbitrary equivalence claims.
Learned evaluations produce immutable attributed relations.
Approximation is represented by independently available lower and upper answer bounds.
Structural containment may preserve a certified side through a heuristic suboperation.
Lower-membership provenance is distinct from upper-bound derivation and upper-only non-exclusion.
Normative bounds are valid baselines; registered rules may prove tighter bounds.
Assurance evidence is separate from the formal guarantee and becomes ineffective when stale.
Budgets affect execution and guarantees, not denotation.
Provenance can be part of the query contract.
Redaction is governed by declared logical-disclosure and physical side-channel policies, not blanket non-inference claims.
Materialized summaries remain derived views.
Physical indexes, paging, and caching may change cost but not meaning.
```

The resulting architecture is:

```text
Sol artifact state
        ↓
Normalized logical relations
        ↓
Set-theoretic query denotation
        ↓
Declarative logical expression
        ↓
Logical algebra
        ↓
Registered rewrite rules
        ↓
Cost-based physical plan
        ↓
Indexes, graph traversal, paging, caches, objects, and model calls
```

The foundational statement is:

> SOL-QRY defines relations over committed Sol state. Set-theoretic semantics defines the answer; logic defines declarative derivation; registered logical algebra enables equivalence-preserving transformation; independently certified bounds describe approximation; bound-aware provenance explains certification without confusing possibility with membership; and physical execution determines compute, I/O, and side-channel behavior.

---

# 46. Non-Normative References

1. E. F. Codd, “A Relational Model of Data for Large Shared Data Banks,” 1970.
2. E. F. Codd, “Relational Completeness of Data Base Sublanguages,” 1972.
3. Serge Abiteboul, Richard Hull, and Victor Vianu, *Foundations of Databases*, 1995.
4. Tomasz Imieliński and Witold Lipski Jr., “Incomplete Information in Relational Databases,” 1984.
5. Todd J. Green, Grigoris Karvounarakis, and Val Tannen, “Provenance Semirings,” 2007.
6. Stefano Ceri, Georg Gottlob, and Letizia Tanca, *Logic Programming and Databases*, 1990.
7. Richard T. Snodgrass, editor, *The TSQL2 Temporal Query Language*, 1995.
8. Research on Volcano and Cascades optimizer frameworks.
9. Apache Calcite documentation and relational planning model.
10. Substrait query-plan interchange specification.
11. Datomic and XTDB documentation on immutable database values and history queries.
12. Dolt, TerminusDB, and Fluree documentation on versioned and branching data.
13. ProvSQL, GProM, and Perm work on practical provenance-enabled query evaluation.
14. Research by Motro, Levy, Razniewski, Nutt, and others on completeness statements and complete answers over incomplete databases.
15. Research on online aggregation and BlinkDB-style bounded-time or bounded-error query processing.
16. LOTUS, Palimpzest, DocETL, ZenDB, Evaporate, and related semantic-operator systems.
17. Arenas, Bertossi, Chomicki, and related work on consistent query answering.
18. RFC-SOL-0001, “Sol — A Cooperative Computational Work Artifact,” v0.1.0-draft, frozen.


---

# 47. Review Disposition Matrix

This appendix records how the two external review rounds were incorporated.

## 47.1 First review — incorporated in Revision 2

| Review finding | Disposition |
|---|---|
| Guarantee composition is blocking in practice | Accepted and made normative through concrete lower and upper relations |
| Friendly guarantee labels do not compose safely | Labels became summaries of bound objects rather than the algebraic carrier |
| General equivalence checking is infeasible | Replaced by registered rewrite rules with proof obligations |
| Redaction non-leakage was over-promised | Replaced by leakage dimensions, mandatory controls, and residual-risk disclosure |
| Stochastic evaluators require stable per-key behavior | Strengthened to immutable materialization or complete deterministic evaluation keys |
| Expressiveness class should be explicit | Added in §6 |
| AST should borrow from Substrait and Calcite | Adopted as a mapping and implementation strategy without normative dependency |
| Prior-art map was incomplete | Expanded in §38 |
| Specification weight creates implementation risk | Addressed through the phased reference implementation and executable corpus |
| Novelty is architectural synthesis | Adopted in §40 |

## 47.2 Second review — incorporated in Revision 3

| Review finding | Disposition |
|---|---|
| F-1: Free one-sided bounds were omitted | Accepted in §13.7.1, §13.16, §13.17, validation, examples, and QGOLD-013 through QGOLD-016 |
| F-2: Provenance for bounded relations was unspecified | Accepted in §12 and QV8; lower-membership provenance is separated from upper-bound derivation and upper-only non-exclusion |
| F-3: Validity versus tightness was unstated | Accepted in §13.18; validators must accept tighter proven bounds |
| F-4: Leakage preservation mixed logical and physical obligations | Accepted in §§25, 27, and 32; policy-boundary rewrites are conservative by default and physical side channels require a profile |
| F-5: Corpus namespace and “useful” wording required correction | Corrected in §§13.2 and 25.2 |
| F-6: Assurance staleness should inherit Sol | Accepted in §13.3, QV5-10, and QPATH-023 |
| Stratified bounds needed a worked case | Added in §§13.10 and 33.7 plus QGOLD-017 |
| AVG interval is a tractable first registered aggregate extension | Added as `sol:bound/avg_optional_prefix/v1` in §13.14 and Phase 1 |
| Rewrite proof references need a real evidence discipline | Added classified proof evidence and assurance rules in §§13.3 and 25.6 |
| F-1 and F-2 should be freeze-blocking | Added to §44 freeze requirements |
