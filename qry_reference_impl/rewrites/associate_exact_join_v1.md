# Derivation: associate_exact_join/v1

Rule: `sol:rewrite/associate_exact_join/v1`

## Statement

For inner equi-joins with unique field names and partitionable
on-conditions, reassociation preserves the denotation:

$$(R_A \bowtie_{\theta_{AB}} R_B) \bowtie_{\theta} R_C
 = R_A \bowtie_{\theta_{AB} \cup \theta_A} (R_B \bowtie_{\theta_B} R_C)$$

where $\theta = \theta_A \cup \theta_B$ partitions over $A$'s and $B$'s
output fields.

## Derivation

A triple $(a, b, c)$ appears on the left iff $\theta_{AB}(a, b)$ and
$\theta(a, b, c)$ hold. Since $\theta$ partitions into conditions over
$A \times C$ ($\theta_A$) and $B \times C$ ($\theta_B$), the right side
contains $(a, b, c)$ iff $\theta_B(b, c)$ (inner join) and
$\theta_{AB}(a, b) \cup \theta_A(a, c)$ (outer join) hold. The
conjunctions are identical; the result is equal as a bag. Row order is not
claimed: the nested-loop enumeration order differs between the two plans.

## Preconditions (25.2)

- `join_type: inner` for both joins.
- `on_partitionable: true` — every outer on-condition references a field of
  $A$ or of $B$ (not both), and the outer join retains at least one
  condition (the inner join's conditions move to the outer join).
- `field_names_unique: true` — $A$, $B$, $C$ have disjoint output column
  names, so on-references are unambiguous.
- `evaluator_free`, `spans_policy_boundary: false`, same contexts (25.5).

## Preservation (25.3)

value, multiplicity, provenance, answer_bounds, assurance,
logical_disclosure. `order` is NOT preserved (declared).
`physical_side_channel_class` not claimed.

## Evidence (25.6)

- formal derivation: this document.
- property test: 4096 seeded finite instances, pre/post plans evaluated
  with the exact evaluator, multisets compared (order not claimed).
- adversarial corpus: QPATH-045 (supplemental: non-partitionable
  on-conditions).
- checked certificate: `certificates/rewrites/join-associativity.json`.
