# Derivation: push_filter_across_policy_with_disclosure_proof/v1

Rule: `sol:rewrite/push_filter_across_policy_with_disclosure_proof/v1`

## Statement

An exact selection $P$ directly above a policy boundary $B$ may be pushed
below $B$ (applied on the protected side) iff an accepted disclosure proof
establishes that the move does not change the logical-disclosure behavior
under the selected policy.

## Derivation

A policy boundary is identity on the relation: it marks a disclosure
context, not a data transformation. Pushing $P$ from above $B$ to below
$B$ leaves the output relation unchanged (the same tuples are visible to
the output in both plans). What the move *can* change is disclosure:
which tuples are *processed* on the protected side, and therefore what a
leaky implementation might observe. The registered rule is therefore
non-preserving by default (25.5) and may be applied only with a committed
disclosure proof. The proof's machine check (exhaustive finite instances):
for every instance, the visible output set before and after the push is
identical.

## Preconditions (25.2)

- `disclosure_proof: true` — the request carries a committed, verified
  disclosure proof (`certificates/rewrites/disclosure-proof.json`).
- `boundary_kind: [authorization, visibility, leakage]`.
- `predicate_determinism: exact`.
- `spans_policy_boundary: true` — this rule explicitly spans the boundary;
  the 25.5 default is lifted by the proof, not ignored.

## Preservation (25.3)

value, multiplicity, provenance, order, answer_bounds, assurance,
logical_disclosure (the proof establishes the disclosure dimension).
`physical_side_channel_class` not claimed.

## Evidence (25.6)

- formal derivation: this document.
- checked certificate: `certificates/rewrites/disclosure-proof.json`
  (visible-set equality over 256 seeded finite instances).
- adversarial corpus: QPATH-026 (no proof: default non-preserving),
  QPATH-039 (fixture value matching is not a proof).
