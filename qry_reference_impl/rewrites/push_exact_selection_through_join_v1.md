# Derivation: push_exact_selection_through_join/v1

Rule: `sol:rewrite/push_exact_selection_through_join/v1`

## Statement

For an exact (deterministic) selection $P$ whose fields are scoped to the
left input, pushing $P$ through an inner join is denotationally equivalent:

$$\sigma_P(R_A \bowtie_{\theta} R_B) = \sigma_P(R_A) \bowtie_{\theta} R_B$$

when $P$ references only columns of $R_A$ and $\theta$ is equi-join.

## Derivation

A tuple $(a, b)$ appears in $\sigma_P(R_A) \bowtie_\theta R_B$ iff $P(a)$
holds and $a \bowtie_\theta b$. A tuple $(a, b)$ appears in
$\sigma_P(R_A \bowtie_\theta R_B)$ iff $P(a)$ holds (the selection reads
only left-side columns of the joined tuple, which are exactly $a$'s
columns) and $a \bowtie_\theta b$. The two conditions are identical, so the
result relations are equal as sets and as bags (the join is a deterministic
product over matching pairs in both plans).

## Preconditions (25.2)

- `predicate_determinism: exact` — $P$ is a deterministic conjunction of
  exact comparisons; no heuristic selectivity range.
- `predicate_scope: [left_input]` — every field of $P$ resolves on the
  left input, so $P$ is well-defined on both sides of the equivalence.
- `evaluator_free` — no semantic-evaluator node in the span (25.5).
- `spans_policy_boundary: false` — no policy boundary in the span (25.5).
- Same temporal, visibility, authorization, and leakage contexts.

## Preservation (25.3)

value, multiplicity, provenance, order (the nested-loop join produces the
same pair order in both plans), answer_bounds, assurance,
logical_disclosure. `physical_side_channel_class` is not claimed (no
physical conformance profile is published).

## Evidence (25.6)

- formal derivation: this document.
- property test: 256 seeded finite instances, pre/post plans evaluated with
  the exact evaluator, row lists compared (order-sensitive).
- adversarial corpus: QPATH-022 (unmet precondition: the span contains a
  semantic-evaluator barrier).
- checked certificate: `certificates/rewrites/selection-pushdown.json`.
