# RFC-SOL-QRY-0001: Declarative Query Semantics for Sol

## Status

Design draft, v0.1.0

This document is a proposed companion specification to **RFC-SOL-0001: Sol — A Cooperative Computational Work Artifact**. It does not amend or unfreeze RFC-SOL-0001. It defines a candidate foundation for querying committed Sol state and is intended to be refined through implementation, examples, and a query pathology corpus.

Normative terms such as **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used in the sense of RFC 2119 and RFC 8174 when, and only when, they appear in uppercase.

---

## Abstract

Sol defines a self-contained, versioned computational work artifact whose structured state is canonical and whose rendered surfaces are derived. It provides stable identities for cells, semantic records, objects, runs, commits, branches, actors, and outputs; it also defines provenance, staleness, verification, internal history, and bounded structural reads.

This document proposes **SOL-QRY**, a declarative query model over committed Sol state.

The design separates four concerns:

1. **Set-theoretic and model-theoretic semantics** define what data exists and what a query result means.
2. **Declarative logic** defines which tuples belong to a result without prescribing an access path.
3. **Logical algebra** provides a compositional representation that can be transformed by an optimizer while preserving the query contract.
4. **Physical execution** chooses scans, indexes, graph traversals, materialized views, paging, caching, semantic evaluators, and model calls. Physical execution is intentionally outside the normative core of SOL-QRY.

The central rule is:

> Set-theoretic semantics defines the answer. Logic defines the requested relation. Logical algebra enables equivalence-preserving transformation. Physical execution determines compute and I/O cost.

SOL-QRY uses exact set semantics by default, explicit bag and sequence semantics where required, commit-pinned source snapshots, typed references, provenance-preserving evaluation, explicit open-world and closed-world assumptions, safe negation, temporal semantics, and declared answer guarantees. Learned or LLM-based semantic evaluations are modeled as attributed, typed computations that produce inspectable relations; they do not silently redefine equality or truth.

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

SOL-QRY is not a storage format, index format, page manager, vector-search protocol, agent orchestration language, or mutation language. It defines the logical meaning that those systems must preserve.

---

# 2. Relationship to RFC-SOL-0001

RFC-SOL-0001 already provides the substrate required for a database-style query layer:

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

The physical `.solnb` representation does not need to be relational. A conforming implementation may store Sol state in an embedded database, indexed package, content-addressed object graph, document store, or other representation. SOL-QRY defines a normalized logical projection over that state.

This specification preserves the RFC-SOL-0001 distinction between:

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
11. safe, finite, domain-independent queries;
12. positive recursion and stratified negation;
13. exact aggregation semantics;
14. a canonical logical-algebra representation;
15. provenance and annotation modes;
16. semantic-evaluator contracts;
17. exactness, soundness, completeness, and heuristic guarantees;
18. logical and materialized views;
19. canonical query and query-result records;
20. conformance requirements for readers, compilers, evaluators, and validators.

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
- automatic entity resolution policy;
- mutation statements;
- transaction commit mechanics beyond reuse of Sol commits;
- global cross-artifact catalog administration.

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
Equivalence-preserving rewrites
          ↓
Physical execution plan
          ↓
Indexes, scans, graphs, paging, caches, objects, and model calls
```

The upper layers define meaning. The lower layers define cost.

A larger artifact or federated source is not expected to execute with the same latency as a smaller resident source. Paging, indexing, and materialized views are capacity and performance mechanisms, not semantic mechanisms. A query remains the same query whether it is answered by an index lookup, a full scan, a graph walk, a cached summary, or a semantic evaluator.

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

## QINV-05: Orthogonal epistemic dimensions

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

A result requested with provenance MUST be able to identify the base tuples, records, objects, evaluations, and source commits from which it was derived.

## QINV-08: Semantic evaluation is recorded work

An LLM, embedding model, classifier, reranker, or other learned evaluator MUST be represented as an attributed typed computation. Its result MUST be representable as data.

## QINV-09: Safe negation

Classical negation and set difference MUST be used only where the relevant relation is declared complete under the selected snapshot, visibility policy, and assessment policy.

## QINV-10: Read-only query semantics

SOL-QRY derives relations. It MUST NOT directly mutate canonical artifact state.

A query result MAY be used to construct a proposal, execution request, verification request, or other Sol operation, but mutation remains governed by Sol authorization, review, execution, and commit semantics.

---

# 6. Terminology

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

A stored result of a named query, tied to source commits, dependencies, freshness state, and query identity.

## Assertion

A record that an actor, tool, or process has stated or represented a proposition.

## Accepted fact

A proposition regarded as true under an explicit assessment policy. An accepted fact is not the same as a stored claim record.

## Answer guarantee

A declaration of whether a result is exact, a sound subset, a complete superset, heuristic, or of unknown guarantee.

## Semantic evaluator

A typed computation that applies learned, probabilistic, heuristic, or human judgment and emits structured assessment tuples.

---

# 7. Typed Universe

## 7.1 Many-sorted domains

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

## 7.2 Parameterized reference types

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

## 7.3 Scalar equality

Scalar equality is defined within a type.

Cross-type numeric comparisons MAY be supported only through explicit coercion rules declared by the type system.

String comparison MUST declare its collation and normalization policy when the result depends on them.

## 7.4 Reference identity

Two immutable `object:` references are equal when their canonical content-addressed identities are equal.

Two logical references are equal when their canonical parsed identities are equal.

A named output reference is not equal to the immutable object to which it resolves. Resolution is a relation, not equality.

---

# 8. Source and Snapshot Model

## 8.1 Single-artifact instance

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

## 8.2 Branch resolution

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

## 8.3 Federated instance

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

## 8.4 Visibility policy

A source manifest MUST identify the authorization or visibility policy used to expose tuples.

A query over a filtered source answers questions about visible state, not necessarily the complete artifact state. The result metadata MUST disclose that distinction.

---

# 9. Logical Schemas

## 9.1 Snapshot schema

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

## 9.2 History schema

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

## 9.3 Normalized projection

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

## 9.4 Ordered arrays

If array order is semantically meaningful, the normalized relation MUST include an ordinal:

```text
LinearCellPosition(ordinal, cell_id)
DecisionCandidatePosition(decision_id, ordinal, candidate_ref)
```

If order is not semantically meaningful, the relation MUST be treated as a set.

## 9.5 Example normalized core

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

# 10. Set, Bag, and Sequence Semantics

## 10.1 Set semantics

The default relation is a finite mathematical set:

\[
R \subseteq D_{\tau_1} \times \cdots \times D_{\tau_n}
\]

A tuple occurs at most once.

Duplicate content does not imply duplicate identity. Two events with identical text remain distinct if they have distinct event or record IDs.

## 10.2 Bag semantics

A bag associates each tuple with a nonnegative multiplicity:

\[
R_B : Tuple \rightarrow \mathbb{N}
\]

Bag semantics MUST be requested explicitly.

## 10.3 Sequence semantics

A sequence is an ordered finite collection. A relation is not implicitly ordered.

`ORDER BY` transforms a set or bag into a sequence.

A committed sequence result MUST have a deterministic total order. If the declared sort keys do not form a total order, the evaluator SHOULD add a stable identity as a final tie breaker or MUST report nondeterminism.

## 10.4 Result kinds

A query result MUST declare one of:

```text
SET<T>
BAG<T>
SEQUENCE<T>
```

## 10.5 Limit and sampling

`LIMIT`, `FIRST`, and `TOP` MUST operate on a sequence.

Applying a limit without an explicit order MUST either:

- fail validation for a committed deterministic result; or
- be labeled an arbitrary nondeterministic sample.

---

# 11. Annotated Relations and Provenance

## 11.1 Finite-support annotated relation

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

## 11.2 Default annotation

The default is Boolean set membership:

\[
K = \mathbb{B} = \{0,1\}
\]

## 11.3 Positive algebra propagation

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

## 11.4 Provenance modes

A query MAY request:

```text
none
tuple
why
how
full_graph
```

A minimal implementation MAY support `none` and `tuple` only.

Provenance MUST identify source commits and SHOULD identify source records, objects, runs, semantic evaluations, and view substitutions where applicable.

## 11.5 Negation caveat

Provenance under unrestricted negation and aggregation is substantially more complex than positive relational provenance. SOL-QRY v0.1 SHOULD restrict provenance guarantees for such operations and MUST disclose any unsupported provenance mode.

---

# 12. Missing and Protected Values

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

## 12.1 Absent

The field is not applicable or was not supplied.

## 12.2 Unknown

A value may exist, but the artifact does not know it.

## 12.3 Redacted

A value exists or may exist, but policy prevents disclosure.

## 12.4 Unavailable

A referenced external resource is not currently retrievable.

## 12.5 Unresolved

A syntactically valid reference does not resolve in the selected source context.

## 12.6 Predicates

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

---

# 13. Assertion Semantics and World Assessment

## 13.1 Artifact truth

A tuple in the `Claim` relation means:

> The selected artifact state contains a claim record with these fields.

It does not by itself mean that the claimed proposition is true in the represented world.

Contradictory claims can coexist without making the artifact database structurally inconsistent. They represent competing assertions.

## 13.2 Status dimensions

Lifecycle, staleness, and verification are metadata about the record and its support state.

They MUST NOT be collapsed into binary truth.

Examples:

- `unverified` does not mean false;
- `failed_verification` does not necessarily prove the opposite proposition;
- `stale` means dependencies or context no longer support current use;
- `withdrawn` describes lifecycle;
- `confidence: 0.8` is not automatically a probability of truth.

## 13.3 World-assessment layer

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

## 13.4 Four-state support model

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

---

# 14. Open-World and Closed-World Semantics

## 14.1 Relation declarations

Each relation SHOULD declare a world assumption:

```text
closed
open
policy_scoped
approximate
externally_incomplete
```

## 14.2 Closed relation

For a closed relation, absence under the selected snapshot and policy may imply nonmembership.

## 14.3 Open relation

For an open relation, absence means only that no visible assertion is present.

## 14.4 Policy-scoped relation

For a policy-scoped relation, tuples may be hidden. Absence means “not visible under this policy,” not “does not exist.”

## 14.5 Approximate relation

An approximate relation may omit or add tuples according to its declared guarantee.

## 14.6 Externally incomplete relation

An externally incomplete relation represents a source known not to cover the full relevant world.

## 14.7 Negation forms

SOL-QRY SHOULD distinguish:

```text
NOT ASSERTED R(x)
NO VISIBLE R(x)
CERTAINLY NOT P(x) UNDER policy
```

These are not equivalent.

## 14.8 Possible-world profiles

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

SOL-QRY v0.1 MAY reserve the query modes:

```text
ASSERTED
CERTAIN UNDER <policy>
POSSIBLE UNDER <policy>
```

while requiring only `ASSERTED` as a baseline conformance feature.

---

# 15. Temporal Semantics

## 15.1 Artifact time

Artifact time describes when a tuple is present in committed Sol history.

The fundamental coordinate is commit identity and ancestry, not timestamp order.

## 15.2 Valid time

Valid time describes when a modeled proposition is asserted to hold in the represented world.

A temporal semantic record MAY declare:

```text
valid_from
valid_to
```

or another registered interval representation.

## 15.3 Combined query

A query may specify both:

```text
AT COMMIT commit_042
VALID AT 2026-07-21T14:00:00Z
```

This means:

> Using the knowledge recorded in commit 42, return propositions asserted to be valid at the given world time.

## 15.4 History operators

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

## 15.5 Latest

`LATEST` MUST NOT be interpreted solely by wall-clock timestamp in a branching history.

A latest query MUST specify:

- a branch or lineage;
- an ancestry relation;
- a deterministic tie or conflict rule.

---

# 16. Integrity Constraints

## 16.1 Constraint types

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

## 16.2 Examples

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

## 16.3 Optimizer trust

A logical rewrite MAY rely on a constraint only if that constraint is:

- normative for the relation;
- validated at the selected source commits; or
- backed by a current verification record whose dependencies are current.

An asserted but unverified constraint MUST NOT justify correctness-sensitive rewrites.

---

# 17. Declarative Logical Model

## 17.1 Canonical calculus

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

## 17.2 Query parameters

Queries MAY declare typed parameters:

```json
{
  "name": "target_commit",
  "type": "Ref<Commit>",
  "required": true
}
```

Parameter values MUST be bound before evaluation and included in the query execution identity.

## 17.3 Result schema

A query MUST declare or infer a result schema containing:

- field names;
- field types;
- optionality states;
- collection kind;
- ordering contract;
- provenance mode;
- answer guarantee.

---

# 18. Query Safety and Domain Independence

A conforming query MUST denote a finite result determined by the finite active domain of its sources and explicit finite domains.

## 18.1 Safety rules

At minimum:

1. Every returned variable MUST be bound by a positive relation atom or finite explicit domain.
2. Every variable appearing in a negated subformula MUST be bound outside that subformula.
3. Every aggregate input MUST range over a finite relation.
4. Universal quantification MUST be over an explicit finite domain.
5. Functions MUST NOT synthesize an unbounded domain.
6. Reference traversal MUST range over resolvable references in the source manifest.

## 18.2 Safe example

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

## 18.3 Unsafe example

```text
{ x | NOT Claim(x) }
```

This is unsafe because it ranges over every possible value outside the finite database instance.

---

# 19. Recursion

## 19.1 Need for recursion

Sol state contains recursive structures:

- commit ancestry;
- execution reachability;
- dependency closure;
- provenance chains;
- supersession chains;
- evidence graphs.

## 19.2 Least-fixed-point semantics

Positive recursive rules SHOULD use least-fixed-point semantics.

Example:

```text
ancestor(Older, Newer) :-
    commit_parent(Newer, Older).

ancestor(Older, Newer) :-
    commit_parent(Newer, Middle),
    ancestor(Older, Middle).
```

## 19.3 Stratification

SOL-QRY v0.1 SHOULD support:

```text
positive recursion
stratified negation
stratified aggregation
```

Unrestricted recursion through negation SHOULD be deferred.

## 19.4 Termination

A recursive query MUST range over finite source relations and MUST have an evaluation strategy that reaches a finite fixed point or reports nonconformance.

---

# 20. Negation and Difference

## 20.1 Set difference

`A EXCEPT B` is valid when both operands are exact closed sets under the same source snapshot and visibility policy.

## 20.2 Assertion absence

`NOT ASSERTED R(x)` means that no visible tuple in the selected assertion relation matches.

## 20.3 Epistemic negation

`CERTAINLY NOT P(x) UNDER policy` means the negated proposition holds in every admissible world under the selected assessment policy.

## 20.4 No silent substitution

The evaluator MUST NOT rewrite one form of negation into another unless the relevant world, completeness, and policy assumptions prove equivalence.

---

# 21. Aggregation

## 21.1 Aggregate operators

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

## 21.2 Open and approximate relations

An aggregate over an open-world, policy-filtered, externally incomplete, or approximate relation MUST disclose what was counted.

Examples:

```text
COUNT ASSERTED Evidence
COUNT VISIBLE Evidence
```

Future profiles may define bounded uncertain aggregates:

```json
{
  "lower_bound": 7,
  "upper_bound": 12
}
```

## 21.3 Empty input

Each aggregate MUST define its result on empty input.

## 21.4 Determinism

Floating-point and statistical aggregates SHOULD declare numerical stability, precision, and ordering requirements when exact reproducibility is requested.

---

# 22. Logical Algebra

The logical algebra is implementation-independent. It is not a physical plan.

## 22.1 Core operators

| Operator | Meaning |
|---|---|
| `Relation(R)` | Extension of base or derived relation `R` |
| `Select(predicate, E)` | Tuples of `E` satisfying the predicate |
| `Project(fields, E)` | Selected attributes of tuples in `E` |
| `Rename(mapping, E)` | Attribute renaming |
| `Join(condition, E1, E2)` | Compatible tuple combinations |
| `Union(E1, E2)` | Tuples present in either operand |
| `Intersect(E1, E2)` | Tuples present in both operands |
| `Difference(E1, E2)` | Tuples in `E1` not in `E2`, subject to closed-world requirements |
| `Distinct(E)` | Convert bag semantics to set semantics |
| `Group(keys, aggregates, E)` | Grouping and aggregation |
| `LeastFixpoint(rules)` | Recursive derivation |
| `TemporalSlice(spec, E)` | Restriction by commit or valid time |
| `Annotate(mode, E)` | Request provenance or another annotation |
| `Order(keys, E)` | Convert a relation to a sequence |
| `Limit(n, sequence)` | Prefix of an explicitly ordered sequence |

## 22.2 Source-context operators

A small number of context-setting operators are justified:

```text
Snapshot(artifact, commit)
Federation(source_manifest)
ValidTime(interval)
AssessmentPolicy(policy)
VisibilityPolicy(policy)
```

These establish interpretation context rather than manipulating ordinary tuples.

## 22.3 Sol-specific derived relations

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

## 22.4 Rewrite preconditions

Every rewrite rule MUST declare the properties it requires, including:

- set or bag semantics;
- exactness;
- determinism;
- relation completeness;
- keys and functional dependencies;
- provenance preservation;
- sequence order preservation;
- semantic-evaluator purity.

---

# 23. Semantic Evaluators

## 23.1 Semantic evaluation as data production

A semantic evaluator MUST produce a relation rather than silently act as exact equality.

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

## 23.2 Evaluator contract

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
  "cache_key_fields": [
    "left_ref",
    "right_ref",
    "configuration_digest"
  ]
}
```

## 23.3 Boundary operator

A logical plan MAY contain:

```text
Evaluate(evaluator_contract, input_relation)
```

The evaluator contract MUST disclose whether the operation is:

- deterministic or stochastic;
- exact, sound, complete, heuristic, or unknown;
- monotone or nonmonotone;
- side-effect-free or materializing;
- cacheable or noncacheable;
- safe to duplicate;
- safe to reorder.

## 23.4 Materialization

If a semantic evaluation contributes to a committed query result, its assessment tuples SHOULD be materialized with actor identity, model identity, configuration digest, source references, and provenance.

## 23.5 Equality prohibition

The query engine MUST NOT replace exact equality with semantic similarity or entity-resolution output unless the query explicitly asks for a relation defined by that evaluator or policy.

---

# 24. Answer Guarantees and Budgets

## 24.1 Guarantee vocabulary

A query execution MUST declare one of:

```text
exact
sound_subset
complete_superset
heuristic
unknown
```

## 24.2 Meanings

| Guarantee | Meaning |
|---|---|
| `exact` | Every returned tuple is valid and every valid tuple is returned. |
| `sound_subset` | Every returned tuple is valid, but some valid tuples may be omitted. |
| `complete_superset` | Every valid tuple is included, but extra tuples may be returned. |
| `heuristic` | No formal soundness or completeness guarantee. |
| `unknown` | The implementation cannot establish a guarantee. |

## 24.3 Resource budget

A query MAY declare a budget:

```json
{
  "max_object_bytes": 104857600,
  "max_records_read": 100000,
  "max_semantic_evaluations": 20,
  "max_wall_time_ms": 5000,
  "max_memory_bytes": 1073741824
}
```

A budget does not change the query denotation.

If the budget prevents exact completion, the evaluator MUST either:

- fail without returning an exact result;
- return a result with a weaker declared guarantee; or
- return a continuation token and an incomplete status.

## 24.4 No false exactness

Top-k retrieval, approximate nearest-neighbor search, early stopping, sampling, truncated graph traversal, or limited model calls MUST NOT be reported as an exact evaluation unless the implementation can prove exactness for the specific query.

---

# 25. Query Equivalence

SOL-QRY distinguishes several forms of equivalence:

```text
value-equivalent
multiplicity-equivalent
provenance-equivalent
order-equivalent
guarantee-equivalent
diagnostic-equivalent
```

Two plans may return the same set of IDs but different provenance.

Two plans may return the same rows while one is exact and the other heuristic.

Two plans may return the same bag but in different sequence order.

A query SHOULD declare which dimensions must be preserved:

```json
{
  "required_equivalence": [
    "value",
    "provenance",
    "answer_guarantee"
  ]
}
```

An optimizer MUST apply only rewrites that preserve the requested equivalence contract.

---

# 26. Views and Materialized Views

## 26.1 Logical view

A logical view is a named query:

```text
VIEW CurrentVerifiedClaims AS ...
```

## 26.2 Materialized view

A materialized view SHOULD record:

- view identity;
- query identity and digest;
- source manifest;
- result schema;
- result object;
- dependency closure;
- source commits;
- freshness state;
- provenance mode;
- answer guarantee;
- creation actor;
- creation run;
- verification state.

## 26.3 Machine summary

A Sol machine summary is a natural built-in materialized view over bounded structural read levels.

An evaluator MAY substitute a validated machine summary when:

1. the summary source commit matches the selected source commit;
2. the query references only fields represented by the summary;
3. summary-artifact integrity has been validated;
4. the requested provenance and guarantee are preserved;
5. no omitted record body or object payload is required.

The summary remains derived. It MUST NOT become canonical merely because it is cheaper to read.

## 26.4 Refresh and invalidation

Materialized views MUST become stale when any dependency relevant to their denotation changes.

A view MAY be incrementally refreshed if the implementation can preserve the declared result and provenance contract.

---

# 27. Query Record

The canonical query form SHOULD be a typed AST stored as a semantic record or registered extension record.

Example:

```json
{
  "record_id": "query_decisions_needing_review",
  "record_type": "sol:record/query",

  "sources": [
    {
      "artifact_id": "art_01j9x7k9k5m2c8v6h3p4q2r1s0",
      "commit_id": "commit:commit_042",
      "alias": "work"
    }
  ],

  "parameters": [],

  "semantics": {
    "multiplicity": "set",
    "world_mode": "asserted",
    "answer_guarantee": "exact",
    "provenance": "why",
    "ordering": "unordered"
  },

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

## 27.1 Canonicalization

The query AST SHOULD support deterministic canonicalization and hashing.

A query digest SHOULD include:

- canonical expression;
- parameter types and bound values;
- source manifest;
- semantic modes;
- result schema;
- evaluator-contract identities;
- visibility and assessment policies.

## 27.2 Human syntax

A human-readable syntax MAY compile to the canonical AST.

The AST, not the surface syntax, SHOULD be the unit of signing, validation, plan caching, and provenance.

---

# 28. Query Execution Record

A query execution MAY reuse the Sol run model.

A query execution record SHOULD include:

```json
{
  "query_run_id": "query_run_008",
  "query_ref": "record:query_decisions_needing_review",
  "query_digest": "digest:sha256:...",
  "source_manifest": "object:sha256:...",
  "actor_id": "tool:sol_query_engine",
  "status": "success",
  "answer_guarantee": "exact",
  "provenance_mode": "why",
  "started_at": "2026-07-27T10:00:00Z",
  "completed_at": "2026-07-27T10:00:00.080Z",
  "result_object": "object:sha256:...",
  "rows_returned": 3,
  "resource_usage": {
    "records_read": 27,
    "object_bytes_read": 0,
    "semantic_evaluations": 0,
    "wall_time_ms": 80
  }
}
```

## 28.1 Physical-plan recording

The physical plan MAY be recorded for reproducibility or audit, but it MUST NOT define query meaning.

## 28.2 Partial and continued results

A budget-limited execution MAY return:

```text
complete
incomplete_with_continuation
failed
cancelled
```

An incomplete result MUST NOT carry the `exact` guarantee for the complete query unless the implementation proves that the omitted work cannot affect the result.

---

# 29. Worked Example Across All Layers

Question:

> Return decisions that require review because they depend on a stale claim or a claim needing reverification.

## 29.1 Set-theoretic denotation

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

This defines the answer without specifying an access path.

## 29.2 Relational-calculus form

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

## 29.3 Datalog-style form

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

## 29.4 Logical-algebra form

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

## 29.5 Possible physical executions

A SOL-PLAN implementation may choose:

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

## 29.6 Provenance-bearing result

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

---

# 30. Relation Catalog

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
  "multiplicity": "set",
  "world_assumption": "closed",
  "completeness": "exact_at_snapshot",
  "temporal_model": "commit_snapshot",
  "provenance_capability": "tuple"
}
```

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
  "answer_guarantee": "exact"
}
```

The catalog SHOULD distinguish logical relation metadata from physical index metadata. Physical indexes belong in SOL-IDX.

---

# 31. Authorization and Security

## 31.1 Query visibility

A query MUST execute under a declared actor and authorization context.

## 31.2 Redaction preservation

A query MUST NOT infer or expose redacted values through projection, aggregation, errors, cardinality side channels, provenance, or diagnostics unless the policy explicitly permits it.

## 31.3 Provenance visibility

Provenance MAY reveal hidden relationships. A result MUST apply authorization policy to provenance as well as value tuples.

## 31.4 Semantic evaluators

A semantic evaluator MUST NOT receive restricted source content unless its actor and execution environment are authorized for that content.

## 31.5 Safe opening

Querying or rendering a Sol artifact MUST NOT imply executing arbitrary code contained by the artifact.

---

# 32. Conformance Roles

## 32.1 Query Reader

A Query Reader can parse and inspect query records, source manifests, result schemas, semantic modes, and query digests without executing them.

## 32.2 Query Validator

A Query Validator can validate:

- source coordinates;
- type correctness;
- relation and field resolution;
- safe variable binding;
- finite-domain requirements;
- legal negation;
- declared collection semantics;
- evaluator contracts;
- result-schema compatibility;
- guarantee consistency;
- authorization metadata;
- canonicalization and digest integrity.

## 32.3 Query Compiler

A Query Compiler can translate a supported surface syntax into the canonical typed AST without changing the denotation.

## 32.4 Logical Planner

A Logical Planner can translate the canonical AST into logical algebra and apply equivalence-preserving rewrites.

## 32.5 Query Evaluator

A Query Evaluator can evaluate supported logical plans against commit-pinned sources and produce query execution records and result objects.

## 32.6 Materialized View Maintainer

A Materialized View Maintainer can create, validate, invalidate, and refresh materialized query results while preserving their source, dependency, provenance, and guarantee contracts.

---

# 33. Proposed Validation Rules

Stable rule identifiers are recommended.

## QV0 — Syntax and Type System

```text
QV0-01  Query record parses and version is recognized.
QV0-02  Every relation, field, type, and evaluator resolves.
QV0-03  Expression is type-correct.
QV0-04  Result schema matches expression output.
QV0-05  Query canonicalization and digest verify.
```

## QV1 — Source Semantics

```text
QV1-01  Every source resolves to an artifact and commit.
QV1-02  Branch references are resolved to commits before evaluation.
QV1-03  Source manifest is immutable for one execution.
QV1-04  Visibility and authorization policies are declared.
```

## QV2 — Safety

```text
QV2-01  Every output variable is positively or finitely bound.
QV2-02  Variables in negated subexpressions are bound outside them.
QV2-03  Aggregates range over finite relations.
QV2-04  Recursive rules have finite-domain least-fixed-point semantics.
QV2-05  No unsafe unbounded value generation.
```

## QV3 — Set and Order Semantics

```text
QV3-01  Collection kind is declared or defaults to set.
QV3-02  Bag conversion is explicit.
QV3-03  Ordered result has a deterministic total order when required.
QV3-04  Limit is applied only to a sequence or marked nondeterministic.
```

## QV4 — Negation and Completeness

```text
QV4-01  Difference operands have compatible exact closed-world contracts.
QV4-02  Classical negation does not cross an open or policy-incomplete boundary.
QV4-03  Assertion absence is not mislabeled epistemic negation.
QV4-04  Approximate input does not silently support exact negation.
```

## QV5 — Semantic Evaluators

```text
QV5-01  Evaluator has a registered input and output schema.
QV5-02  Actor, model, version, and configuration identity are recorded.
QV5-03  Heuristic or stochastic evaluation is not labeled exact without proof.
QV5-04  Rewrites do not duplicate or reorder evaluator calls illegally.
QV5-05  Committed semantic results are materialized or otherwise auditable.
```

## QV6 — Provenance and Guarantees

```text
QV6-01  Requested provenance mode is supported.
QV6-02  Result guarantee is consistent with all operators and access methods.
QV6-03  Budget truncation weakens the guarantee or marks the result incomplete.
QV6-04  View substitution preserves requested value, provenance, order, and guarantee semantics.
```

---

# 34. Pathology Corpus Candidates

```text
QPATH-001  The moving branch
           Query begins on branch main but records no resolved commit.
           Expected: QV1-02, QV1-03.

QPATH-002  The semantic equality forgery
           Vector similarity is substituted for exact `=`.
           Expected: QINV-04, QV5-03.

QPATH-003  The false exact result
           Approximate nearest-neighbor retrieval returns top-k rows labeled exact.
           Expected: QINV-06, QV6-02.

QPATH-004  The open-world negation
           `NOT EXISTS` is used against an externally incomplete evidence relation.
           Expected: QV4-02.

QPATH-005  The hidden redaction leak
           COUNT reveals the number of restricted records to an unauthorized actor.
           Expected: authorization failure.

QPATH-006  The unordered top ten
           LIMIT 10 is committed without deterministic ordering.
           Expected: QV3-04.

QPATH-007  The duplicated stochastic call
           Optimizer duplicates a stochastic evaluator during predicate pushdown.
           Expected: QV5-04.

QPATH-008  The stale materialized view
           A view from commit 41 answers a query pinned to commit 42.
           Expected: QV6-04.

QPATH-009  The truth-status collapse
           `verification = unverified` is rewritten as proposition = false.
           Expected: QINV-05.

QPATH-010  The unresolved object masquerade
           A named output is compared directly to an immutable object reference.
           Expected: type error.

QPATH-011  The unsafe universe
           Query asks for every value that is not a claim.
           Expected: QV2-01, QV2-05.

QPATH-012  The incomplete exact count
           Budget stops after 1000 records but COUNT is labeled exact.
           Expected: QV6-03.

QPATH-013  The provenance-dropping rewrite
           Optimizer returns value-equivalent rows but loses required source lineage.
           Expected: QV6-04.

QPATH-014  The timestamp time traveler
           Latest commit is selected by timestamp across divergent branches.
           Expected: temporal validation failure.

QPATH-015  The bag-set confusion
           Projection under bag semantics is treated as duplicate-eliminating without DISTINCT.
           Expected: QV3-02.
```

---

# 35. Recommended v0.1 Scope

## 35.1 Include

A rigorous first version SHOULD include:

1. pinned single-artifact sources;
2. small explicitly pinned federations;
3. normalized logical relations for core Sol entities;
4. typed scalar and reference values;
5. exact set semantics by default;
6. explicit bag and sequence conversion;
7. safe relational calculus;
8. canonical logical-algebra AST;
9. selection, projection, rename, join, union, intersection;
10. restricted difference over exact closed relations;
11. exact grouping and aggregation;
12. positive recursion;
13. stratified negation;
14. commit-time selection;
15. basic valid-time predicates;
16. typed query parameters;
17. declared result schemas;
18. query canonicalization and digesting;
19. exactness and completeness declarations;
20. basic tuple provenance;
21. read-only evaluation;
22. materialized semantic-assessment contracts;
23. validated machine-summary substitution;
24. a query pathology corpus.

## 35.2 Defer

The following SHOULD be deferred:

- general probabilistic databases;
- unrestricted possible-world inference;
- unrestricted recursion through negation;
- complete provenance through all forms of negation and aggregation;
- automatic entity resolution as identity;
- unrestricted natural-language query semantics;
- mutation statements;
- cost-based physical optimization;
- distributed query scheduling;
- physical page and cache policy;
- learned plan selection;
- global catalog administration.

---

# 36. Companion Specifications

The following split preserves clean architectural boundaries.

## SOL-QRY

```text
Set-theoretic model
Typed logical schema
Declarative calculus
Logical algebra
Result guarantees
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
Logical rewrites
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

---

# 37. Implementation Guidance

This section is non-normative.

## 37.1 Keep durable semantics separate from transient optimization

Canonical or auditable state may include:

- query AST;
- source manifest;
- parameters;
- result schema;
- result object;
- guarantee;
- provenance;
- evaluator identities;
- selected physical plan when reproducibility requires it;
- execution diagnostics.

Transient state should normally remain outside canonical artifact truth:

- GPU addresses;
- current buffer slots;
- LRU counters;
- temporary decompression buffers;
- speculative prefetches;
- page replacement queues;
- low-level scheduler state.

## 37.2 Prefer exact machinery for exact predicates

Identifiers, dates, lifecycle values, authorization, commit ancestry, foreign keys, counts, and deterministic joins should be handled by deterministic machinery.

Learned evaluators are most useful for predicates that are inherently semantic, such as:

- likely paraphrase;
- conceptual relevance;
- likely contradiction;
- probable entity co-reference;
- qualitative comparison.

## 37.3 Treat model parameters as an approximate cache, not the system of record

Parametric model knowledge is difficult to inspect, update, delete, version, and attribute. SOL-QRY should favor committed structured state as the authority and use parametric knowledge as an evaluator or heuristic unless a policy explicitly says otherwise.

## 37.4 Allow global scans when the query requires them

Avoiding full scans is a performance objective, not a semantic axiom.

A query such as “return every inconsistency in all visible evidence” may require broad access. The system should pay that cost when necessary rather than silently weakening the query.

## 37.5 Make incomplete results useful but honest

A sound subset with provenance may be more useful than failure under a strict latency budget. The important requirement is that the result advertise its guarantee and continuation state accurately.

---

# 38. Feasibility and Prior Art

The individual foundations are established:

- the relational model separates logical data from physical organization;
- relational calculus provides declarative semantics;
- relational algebra provides a compositional transformation language;
- Datalog and least-fixed-point logic provide recursive query semantics;
- incomplete-information systems provide open-world, possible-world, and certain-answer models;
- temporal databases distinguish transaction time from valid time;
- provenance semirings provide a general account of annotations under positive relational operations.

The novel integration proposed here is their application to Sol’s artifact semantics:

- commit-relative source truth;
- content-addressed immutable objects;
- logical named outputs;
- first-class claims, evidence, decisions, verification, and failures;
- actor attribution;
- dependency-driven staleness;
- bounded structural reads;
- machine-summary materialized views;
- semantic evaluators as auditable computations;
- explicit answer guarantees under resource budgets.

The result is not “an LLM connected to a database.” It is a model in which an LLM or learned system is one class of semantic operator inside a typed, versioned, provenance-preserving information architecture.

---

# 39. Open Questions

## v0.1 blocking

1. What exact normalized base relations are mandatory?
2. Which scalar and reference types are core?
3. What canonical AST encoding should be used?
4. Which surface syntax, if any, should the reference implementation ship?
5. Which provenance modes are mandatory?
6. What exact semantics should restricted difference use?
7. What minimum recursion profile is required?
8. How are redacted cardinalities represented without leakage?
9. What relation-completeness declarations are required?
10. How should query records integrate with the existing Sol status model?
11. Should query executions reuse `run` directly or use a registered query-run subtype?
12. What exact result-object format is required?
13. Which temporal predicates are mandatory?
14. What is the minimum semantic-evaluator contract?
15. What guarantee combinations are valid for composed plans?

## Post-v0.1

1. Should possible-world query modes become normative?
2. Should probabilistic annotations be standardized?
3. Should four-state claim assessment be part of SOL-SEM?
4. How should provenance interact with negation and aggregation?
5. Should query-plan attestations be signable?
6. How should incremental view maintenance be standardized?
7. How should cross-artifact canonical identities be reconciled?
8. Should natural-language query compilation have a verification profile?
9. How should distributed partial results compose?
10. Should adaptive semantic evaluation produce reusable learned statistics?

---

# 40. Summary

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
Negation requires an explicit completeness contract.
Time has artifact-history and world-validity dimensions.
Queries are declarative and read-only.
Logical algebra is not a physical execution plan.
Learned evaluations produce attributed relations.
Approximation is explicit.
Budgets affect execution and guarantees, not denotation.
Provenance can be part of the query contract.
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
Cost-based physical plan
        ↓
Indexes, graph traversal, paging, caches, objects, and model calls
```

The foundational statement is:

> SOL-QRY defines relations over committed Sol state. Set-theoretic semantics defines the answer; logic defines declarative derivation; logical algebra enables equivalence-preserving transformation; physical execution determines compute and I/O cost.

---

# References

1. E. F. Codd, “A Relational Model of Data for Large Shared Data Banks,” *Communications of the ACM*, 1970. DOI: <https://doi.org/10.1145/362384.362685>
2. E. F. Codd, “Relational Completeness of Data Base Sublanguages,” 1972.
3. Serge Abiteboul, Richard Hull, and Victor Vianu, *Foundations of Databases*, Addison-Wesley, 1995.
4. Tomasz Imieliński and Witold Lipski Jr., “Incomplete Information in Relational Databases,” *Journal of the ACM*, 1984. DOI: <https://doi.org/10.1145/1634.1886>
5. Todd J. Green, Grigoris Karvounarakis, and Val Tannen, “Provenance Semirings,” *PODS*, 2007. DOI: <https://doi.org/10.1145/1265530.1265535>
6. Stefano Ceri, Georg Gottlob, and Letizia Tanca, *Logic Programming and Databases*, Springer, 1990.
7. Serge Abiteboul, Richard Hull, and Victor Vianu, chapters on Datalog and recursive query semantics in *Foundations of Databases*.
8. Richard T. Snodgrass, editor, *The TSQL2 Temporal Query Language*, Kluwer, 1995.
9. RFC-SOL-0001, “Sol — A Cooperative Computational Work Artifact,” v0.1.0-draft, frozen.

