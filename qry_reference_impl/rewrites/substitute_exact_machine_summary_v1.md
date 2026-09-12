# Derivation: substitute_exact_machine_summary/v1

Rule: `sol:rewrite/substitute_exact_machine_summary/v1`

## Statement

A query $Q$ may be answered from a committed machine summary $S$ (levels
0-2) in place of the underlying artifact iff $S$ is a *covering exact
view* of $Q$: every output field of $Q$ is present in $S$, and $S$'s
source commit matches the query's source commit.

## Derivation

Machine-summary levels 0-2 are committed, lossless projections of the
artifact (counts, field-presence, and exact aggregates over the committed
commit). If every output field of $Q$ is present in $S$ and the commits
match, then evaluating $Q$ over $S$ yields exactly the tuples the artifact
would yield (the summary carries the values, not a sample of them). If a
field is missing or the commits differ, the summary is lossy or stale for
$Q$ and substitution is rejected (Q18; QPATH-034).

## Preconditions (25.2)

- `covering_proof: true` — a committed covering proof attests field
  coverage for the specific query.
- `source_commit_match: true` — the summary's source commit equals the
  query's pinned commit.
- `summary_levels: [0, 1, 2]`.
- `evaluator_free`, `spans_policy_boundary: false` (25.5).

## Preservation (25.3)

value, multiplicity, provenance, answer_bounds, assurance,
logical_disclosure, evaluation_identity. `physical_side_channel_class`
not claimed.

## Evidence (25.6)

- formal derivation: this document.
- property test: 256 seeded instances of the covering decision procedure
  (field coverage x commit match), decision compared against the expected
  covering predicate.
- adversarial corpus: QPATH-034 (lossy summary: a required field is
  omitted).
- checked certificate:
  `certificates/rewrites/machine-summary-substitution.json`.
