# Derivation: experimental_aggregate_fold/v1 (EXPERIMENTAL)

Rule: `sol:rewrite/experimental_aggregate_fold/v1`

Status: **experimental** (25.8). Registered for conformance testing only.

## Statement (unverified)

Adjacent exact aggregates over the same group keys may be folded into a
single aggregate.

## Why this is not a proof

No machine check, property test, or adversarial corpus currently verifies
the fold under all guarantee compositions (in particular, interval-valued
aggregates and `may_be_empty` groups are not covered). The rule therefore
carries `contract_asserted` assurance only, and results relying on it MUST
NOT be labeled exact or certified solely on this rule (25.8; QV7-06).

## Preconditions (25.2)

- `aggregate_determinism: exact`.
- `evaluator_free: true`.

## Preservation (25.3)

value, multiplicity (claimed, unverified). All other dimensions not
claimed.
