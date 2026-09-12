# Derivation: prune_exact_projection_v1

Rule: `sol:rewrite/prune_exact_projection/v1`

## Statement

A projection $P$ whose output columns are never referenced by any node on
the path from $P$ to the root may be pruned to the used columns:

$$\pi_{U}(R) = \pi_{U}(\pi_{U \cup W}(R))$$

where $U$ is the set of used columns and $W$ the pruned ones.

## Derivation

Projection is idempotent on column selection: projecting to $U \cup W$ and
then to $U$ selects exactly the same tuples (column values are copied, not
computed), in the same order, with the same multiplicity. No downstream
node observes the pruned columns by the precondition, so no downstream
denotation changes.

## Preconditions (25.2)

- `columns_unused_downstream: true` — every pruned column is unreferenced
  by filter terms, sort keys, distinct keys, join conditions, aggregate
  fields, annotate expressions, and the root output.
- `evaluator_free`, `spans_policy_boundary: false`, same contexts (25.5).

## Preservation (25.3)

value, multiplicity, provenance, order, answer_bounds, assurance,
diagnostics, logical_disclosure. `physical_side_channel_class` not claimed.

## Evidence (25.6)

- formal derivation: this document.
- property test: 256 seeded finite instances, pre/post plans evaluated with
  the exact evaluator, row lists compared.
- adversarial corpus: QPATH-044 (supplemental: every column is used, so the
  precondition fails).
- checked certificate: `certificates/rewrites/projection-pruning.json`.
