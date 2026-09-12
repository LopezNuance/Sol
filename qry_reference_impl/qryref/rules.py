from __future__ import annotations

# Validator rule registry (QRY-SEM-* structural, QRY-BOUND-*, QRY-CERT-*,
# QRY-SUBSTRAIT-*, plus the spec's QV*/QINV* validator rules referenced by
# the §36.2 pathological cases).
VALIDATION_RULES = {
    "QRY-SCHEMA-001": "JSON Schema validation failure",
    "QRY-SEM-001": "Duplicate node id",
    "QRY-SEM-002": "Root node missing",
    "QRY-SEM-003": "Input node missing",
    "QRY-SEM-004": "Cycle detected",
    "QRY-SEM-005": "Unknown source",
    "QRY-SEM-006": "Missing field",
    "QRY-SEM-007": "Union schema mismatch",
    "QRY-SEM-008": "Invalid selectivity annotation",
    "QRY-SEM-009": "Invalid limit",
    "QRY-SEM-010": "Unknown operation",
    "QRY-SEM-011": "Duplicate field",
    "QRY-SEM-012": "Invalid join type",
    "QRY-SEM-013": "Unknown aggregate function",
    "QRY-SEM-018": "Undeclared required AST extension (29.5)",
    "QRY-SEM-019": "Invalid policy reference on a policy-boundary node",
    "QRY-BOUND-001": "Expected bounds mismatch",
    "QRY-CERT-000": "Missing or unreadable certificate",
    "QRY-CERT-001": "Certificate missing step",
    "QRY-CERT-002": "Certificate step bound mismatch",
    "QRY-CERT-003": "Certificate final bound mismatch",
    "QRY-CERT-004": "Certificate step order invalid",
    "QRY-CERT-005": "Certificate root mismatch",
    "QRY-SUBSTRAIT-001": "Operation outside QRY Substrait profile",
    # Spec validator rules (QV* = QRY validator, QINV-* = invariants).
    "QV5-01": "Inverted bounds: lower relation contains a tuple absent from the upper relation",
    "QV5-02": "Guarantee kind claims a certified side without a concrete bound relation",
    "QV5-03": "Exact label without a concrete certified bound relation or derivation",
    "QV5-04": "Certified positive set not contained in the input upper relation",
    "QV5-06": "Inexact aggregate labeled with a scalar bound without a registered interval rule",
    "QV5-10": "Stale assurance dependency must evaluate effectively as unknown",
    "QV5-12": "Aggregate bound does not conform to the registered rule's certified interval",
    "QINV-04": "Exact identity: semantic similarity is not interpreted as equality",
    "QINV-13": "Stable semantic assessment: rewritable evaluator needs a materialized assessment or a complete key",
    "QV5-08": "Heuristic input or predicate contributes to a certified output side without a normative or registered rule",
    "QV5-09": "Structural one-sided bound does not satisfy the declared containment relation",
    "QV6-01": "Evaluator has no registered input and output schemas",
    "QV6-02": "Evaluator actor, model, version, configuration, and policy identity are not recorded",
    "QV6-03": "Rewritable evaluator has no complete deterministic evaluation key or immutable materialized assessment",
    "QV6-04": "Stochastic or heuristic evaluation is labeled exact without proof",
    "QV6-05": "Rewrites duplicate, eliminate, or reorder evaluator calls illegally",
    "QV6-06": "Committed semantic result is not materialized or otherwise auditable",
    "QV6-07": "Evaluator used as tuple-preserving Select invents tuples",
    "QV7-03": "Rule preservation contract does not cover query-required logical-equivalence dimensions",
    "QV8-02": "View substitution does not preserve value, bounds, provenance, policy, and freshness",
    "QV8-03": "Materialized view source commits match or are validly reconciled",
    "QV8-04": "Machine summary substitution is field-complete for the query",
    "QV8-05": "Every lower-bound tuple carries the requested supported membership provenance",
    "QV8-06": "Bounded result upper object has no transfer rule or source-bound provenance",
    "QV8-07": "Upper-only tuple carries ordinary why-provenance asserting exact membership",
    "QV8-08": "Provenance disclosure does not obey the selected authorization and leakage policy",
    "QINV-14": "Bound-provenance honesty: upper-bound enclosure conflated with exact membership",
    "QV9-03": "Cardinality is not suppressed, bucketed, or disclosed as declared",
    "QV9-04": "Provenance does not obey the policy's independent visibility rules",
    "QV9-05": "Error or unauthorized-reference behavior does not obey policy",
    "QV9-08": "General non-inference claim appears without a conforming profile",
}

# Bound-transfer rule registry (spec §13; reference syntax sol:bound/<slug>/v<N>
# per the Q19 decision). Normative rules implement the §13 baseline transfer;
# registered rules may produce tighter bounds under declared preconditions
# (§13.18).
BOUND_RULES = {
    "sol:bound/relation/v1": {
        "description": "Exact denotation of a pinned source relation (read).",
        "preconditions": ["source commit pinned", "source schema declared"],
    },
    "sol:bound/select/v1": {
        "description": "Componentwise Select transfer over exact deterministic predicate terms.",
        "preconditions": ["predicate terms exact and deterministic", "set semantics"],
    },
    "sol:bound/project/v1": {
        "description": "Componentwise Project transfer.",
        "preconditions": ["projected fields present in input schema"],
    },
    "sol:bound/rename/v1": {
        "description": "Componentwise Rename transfer.",
        "preconditions": ["rename mapping declared"],
    },
    "sol:bound/order/v1": {
        "description": "Ordering metadata; L/U relations unchanged.",
        "preconditions": ["order fields present in input schema"],
    },
    "sol:bound/limit/v1": {
        "description": "LIMIT over an exact, deterministically ordered input (position certainty).",
        "preconditions": ["input guarantee exact", "deterministic order declared"],
    },
    "sol:bound/distinct/v1": {
        "description": "Componentwise Distinct transfer under set interpretation.",
        "preconditions": ["distinct keys present in input schema"],
    },
    "sol:bound/union/v1": {
        "description": "Union transfer: L1 ∪ L2, U1 ∪ U2; any available lower side is a valid output lower; the upper ordinarily requires both uppers.",
        "preconditions": ["schema-compatible operands"],
    },
    "sol:bound/intersect/v1": {
        "description": "Intersect transfer: L1 ∩ L2, U1 ∩ U2; any available operand upper is an output upper (§13.7.1).",
        "preconditions": ["schema-compatible operands"],
    },
    "sol:bound/join/v1": {
        "description": "Componentwise Join transfer over exact deterministic join conditions.",
        "preconditions": ["inner join", "join conditions exact and deterministic"],
    },
    "sol:bound/difference/v1": {
        "description": "Difference transfer: L_R = L1 \\ U2, U_R = U1 \\ L2; U1 alone is a valid upper (§13.8, §13.7.1); typed empty lower valid when U2 unavailable.",
        "preconditions": ["schema-compatible operands", "compatible identity and policy contexts"],
    },
    "sol:bound/complement/v1": {
        "description": "Complement relative to an explicit finite exact domain D: L = D \\ U_R, U = D \\ L_R (§13.9).",
        "preconditions": ["explicit finite exact domain"],
    },
    "sol:bound/annotate/v1": {
        "description": "Annotate: exact deterministic column computation; row set unchanged.",
        "preconditions": ["annotation functions exact and deterministic"],
    },
    "sol:bound/structural_containment/v1": {
        "description": "Structural one-sided containment (§13.7.1): tuple-preserving Select keeps U_out = U_R; certified positive set P may replace the typed empty lower.",
        "preconditions": ["operator is tuple-preserving", "empty lower explicitly typed and context-compatible"],
    },
    "sol:bound/least_fixpoint/v1": {
        "description": "Positive recursion: separate lower/upper least fixed points (§13.10).",
        "preconditions": ["program is positive (monotone)"],
    },
    "sol:bound/temporal_slice/v1": {
        "description": "Temporal slice as an exact deterministic predicate over the time field.",
        "preconditions": ["time field present", "bounds explicit"],
    },
    "sol:bound/count_set/v1": {
        "description": "COUNT_SET interval: |L| <= COUNT_SET(R) <= |U| (§13.11).",
        "preconditions": ["finite set relation"],
    },
    "sol:bound/sum/v1": {
        "description": "SUM interval over O = U \\ L (§13.12).",
        "preconditions": ["values exact and finite", "set semantics", "tuple multiplicity one"],
    },
    "sol:bound/min_max/v1": {
        "description": "MIN/MAX intervals: MIN(U) <= MIN(R) <= MIN(L), MAX(L) <= MAX(R) <= MAX(U) (§13.13).",
        "preconditions": ["L nonempty per group", "values exact and finite"],
    },
    "sol:bound/avg_optional_prefix/v1": {
        "description": "Certified AVG interval over finite exact-valued bounds via extremal optional prefixes (§13.14).",
        "preconditions": ["L and U finite set relations", "L ⊆ U", "values exact, finite, present, visible", "tuple multiplicity one", "single numeric expression"],
    },
    "sol:bound/policy_boundary/v1": {
        "description": "Policy-boundary node: identity transfer; marks an explicit policy boundary in the plan (rewrites spanning it default to non-preserving, gate 16).",
        "preconditions": ["policy reference declared (policy:<name>)"],
    },
    # Registered (non-normative) rules.
    "sol:bound/select_certified/v1": {
        "description": "Registered: certified select bound from a proven predicate over named tuples (tighter than the structural-containment baseline).",
        "preconditions": ["predicate proven for the certified tuples", "predicate proven to exclude the remaining lower tuples"],
    },
}

AGGREGATE_RULES = {
    "sol:bound/count_set/v1",
    "sol:bound/sum/v1",
    "sol:bound/min_max/v1",
    "sol:bound/avg_optional_prefix/v1",
}

# Sol extension areas (spec 29.2): Sol-specific semantics are represented by
# declared extensions, not by changing the meaning of standard relational
# nodes. Unknown required extensions MUST fail validation (29.5).
EXTENSION_URNS = {
    "urn:qry:v0.3:commit-pinned-sources": "Commit-pinned sources",
    "urn:qry:v0.3:commit-ancestry": "Commit ancestry",
    "urn:qry:v0.3:world-assumptions": "World assumptions",
    "urn:qry:v0.3:certified-answer-bounds": "Certified answer bounds",
    "urn:qry:v0.3:structural-one-sided-bounds": "Structural one-sided bound rules",
    "urn:qry:v0.3:assurance-evidence": "Assurance evidence and dependencies",
    "urn:qry:v0.3:bound-provenance": "Lower-membership and upper-bound provenance contracts",
    "urn:qry:v0.3:visibility-authorization": "Visibility and authorization policy",
    "urn:qry:v0.3:logical-disclosure": "Logical-disclosure policy",
    "urn:qry:v0.3:physical-side-channel": "Physical side-channel policy",
    "urn:qry:v0.3:valid-time": "Valid time",
    "urn:qry:v0.3:semantic-evaluator-barrier": "Semantic evaluator barriers",
    "urn:qry:v0.3:materialized-assessment": "Materialized assessment relations",
    "urn:qry:v0.3:positive-recursion": "Positive recursive programs (least fixed point)",
    "urn:qry:v0.3:policy-boundary": "Explicit policy-boundary nodes",
}

# Ops whose semantics are Sol-specific and therefore require a declared
# extension (29.2, 29.5).
OP_REQUIRED_EXTENSIONS = {
    "evaluate": "urn:qry:v0.3:semantic-evaluator-barrier",
    "least_fixpoint": "urn:qry:v0.3:positive-recursion",
    "temporal_slice": "urn:qry:v0.3:valid-time",
    "policy_boundary": "urn:qry:v0.3:policy-boundary",
}
