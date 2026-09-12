# Derivation: normalize_union/v1

Rule: `sol:rewrite/normalize_union/v1`

## Statement

1. Flattening nested same-kind unions preserves the denotation:
   $\bigcup_{all}(R_A, \bigcup_{all}(R_B, R_C)) = \bigcup_{all}(R_A, R_B, R_C)$
   (and the distinct variant).
2. Collapsing duplicate inputs of a distinct union preserves the
   denotation: $\bigcup_{distinct}(R_A, R_A, R_B) = \bigcup_{distinct}(R_A, R_B)$.

## Derivation

Union is associative and idempotent in its input multiset: the flattened
concatenation enumerates the same tuples in the same order, and
duplicate-elimination (distinct) is a function of the set of enumerated
tuples, so removing a duplicate input changes neither the set nor the
first-occurrence order. Bag multiplicity is unchanged by flattening;
distinct unions are set-valued by definition.

## Preconditions (25.2)

- `schema_compatible: true` — all inputs share the union's output schema.
- `evaluator_free`, `spans_policy_boundary: false`, same contexts (25.5).

## Preservation (25.3)

value, multiplicity, provenance, order, answer_bounds, assurance,
logical_disclosure. `physical_side_channel_class` not claimed.

## Evidence (25.6)

- formal derivation: this document.
- property test: 512 seeded finite instances (flattening and duplicate
  collapse), pre/post plans evaluated with the exact evaluator, row lists
  compared.
- adversarial corpus: QPATH-046 (supplemental: nothing to normalize).
- checked certificate: `certificates/rewrites/union-normalization.json`.
