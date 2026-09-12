# QRY v0.3 Substrait Mapping Profile

Status: normative baseline (Phase 2 of the v0.3 implementation plan, 2026-09-09)
Machine-readable profile: `qry_substrait_profile.yaml`
Recorded content digest: `mapping_digest.json` (gate condition 4)

## Mapping rules

Standard relational nodes map to Substrait relation concepts; Sol-specific
semantics are carried by declared extensions rather than by changing the
meaning of standard nodes (spec 29.2).

| QRY op | Substrait relation | Notes |
|---|---|---|
| `read` | `ReadRel` | Pinned-instance data (tuples / certified lower/upper) is a QRY extension |
| `filter` | `FilterRel` | Exact deterministic predicate terms; selectivity annotations are bound metadata |
| `project` | `ProjectRel` | Field references, literals, exact computed columns |
| `rename` | `ProjectRel` | Field-name mapping only |
| `sort` | `SortRel` | |
| `limit` | `FetchRel` | Position certainty requires exact + ordered input (13.15) |
| `distinct` | `AggregateRel` | Logical uniqueness over declared keys |
| `aggregate` | `AggregateRel` | Certified numeric intervals are QRY bound annotations (13.11-13.14) |
| `join` | `JoinRel` | Inner joins over exact deterministic conditions; non-inner joins leave certified sides unavailable in the v0.3 baseline |
| `union_all` | `SetRel` (UNION) | Bag union (11.2) |
| `union_distinct` | `SetRel` (UNION_DISTINCT) | Set union (default, QINV-03) |
| `intersect` | `SetRel` (INTERSECT) | |
| `difference` | `SetRel` (MINUS) | |
| `annotate` | `ProjectRel` | Exact deterministic column computation |
| `evaluate` | `ExtensionRel` | Tuple-preserving semantic evaluator barrier (13.7.1) |
| `least_fixpoint` | `ExtensionRel` | Positive recursion; separate lower/upper lfp (13.10) |
| `temporal_slice` | `FilterRel` | Valid-time predicate (17) |
| `policy_boundary` | `ExtensionRel` | Policy-boundary marker; identity transfer |

## Sol extension areas (29.2)

Declared via the query's `extensions` list (URN syntax per the Q19 decision):

- `urn:qry:v0.3:commit-pinned-sources` — commit-pinned sources
- `urn:qry:v0.3:commit-ancestry` — commit ancestry
- `urn:qry:v0.3:world-assumptions` — world assumptions
- `urn:qry:v0.3:certified-answer-bounds` — certified answer bounds
- `urn:qry:v0.3:structural-one-sided-bounds` — structural one-sided bound rules
- `urn:qry:v0.3:assurance-evidence` — assurance evidence and dependencies
- `urn:qry:v0.3:bound-provenance` — lower-membership and upper-bound provenance contracts
- `urn:qry:v0.3:visibility-authorization` — visibility and authorization policy
- `urn:qry:v0.3:logical-disclosure` — logical-disclosure policy
- `urn:qry:v0.3:physical-side-channel` — physical side-channel policy
- `urn:qry:v0.3:valid-time` — valid time
- `urn:qry:v0.3:semantic-evaluator-barrier` — semantic evaluator barriers
- `urn:qry:v0.3:materialized-assessment` — materialized assessment relations
- `urn:qry:v0.3:positive-recursion` — positive recursive programs
- `urn:qry:v0.3:policy-boundary` — explicit policy-boundary nodes

Ops with Sol-specific semantics require their extension declared on the
query; an undeclared required extension fails validation (`QRY-SEM-018`,
29.5): `evaluate` → semantic-evaluator-barrier, `least_fixpoint` →
positive-recursion, `temporal_slice` → valid-time, `policy_boundary` →
policy-boundary.

## Unsupported in v0.3

Window functions, correlated subqueries, arbitrary scalar functions,
user-defined relations, embedded functions, and physical relation variants.

## Digest

`mapping_digest.json` records the sha256 of the canonical JSON of the parsed
YAML profile. The validator (`qryref.substrait_mapper.check_profile_digest`)
verifies the recorded digest against the profile content; the gate harness
recomputes it from the committed profile.
