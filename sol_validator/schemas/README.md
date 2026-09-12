# Sol Normative Schemas (published 2026-09-07)

These JSON Schemas (draft 2020-12) are the published normative artifacts for
RFC-SOL-0001. They cover the nine schema classes required by Appendix C:

| Class | Schema | $id |
|---|---|---|
| Manifest | `manifest.schema.json` | `sol:schemas/manifest/v0.2` |
| Cells | `cell.schema.json` | `sol:schemas/cell/v0.2` |
| Records | `record.schema.json` | `sol:schemas/record/v0.2` |
| Runs | `run.schema.json` | `sol:schemas/run/v0.2` |
| Commits | `commit.schema.json` | `sol:schemas/commit/v0.2` |
| Object records | `object.schema.json` | `sol:schemas/object/v0.1` |
| Actor records | `actor.schema.json` | `sol:schemas/actor/v0.2` |
| Machine summary | `machine_summary.schema.json` | `sol:schemas/machine_summary/v0.2` |
| Diagnostics | `diagnostic.schema.json` | `sol:schemas/diagnostic/v0.2` |

The v0.1 draft set shipped eight of the nine classes; `object.schema.json`
completes the set. The v0.2 revision encodes the Phase 1 decisions
(`docs/decisions/2026-09-07-v01-blocking-questions.md`):

- **Q2** (manifest): `environment` is required with `environment_id` and
  `package_manifest` (digest-pinned package manifest). `kernel` /
  `kernel_version` are enforced by validator rule V0-12 when the artifact
  contains code cells. `imported_from` / `provenance_status` carry the Q6
  import classification.
- **Q3** (object records): `compression` is restricted to the four registered
  identifiers of RFC section 43. Conformance floor: `none` + `gzip`.
- **Q5** (object records): `size_bytes` is bounded 0..2^30 (1 GiB).
- **Q7** (cells): `summary` is required, non-empty, at most 500 characters;
  `cell_type` is restricted to the registered vocabulary (RFC section 19).
- **Q8** (actors): agent actors require `model_id`, `model_version`,
  `delegated_by`, `autonomy_level` (if/then on `actor_type`).
- **Q9** (records): claims require `statement`, `claim_type`,
  `supporting_evidence`; evidence requires `evidence_type`, `supports`, and
  exactly one of `source_ref` / `external_ref` (availability vocabulary per
  RFC section 24.2).
- **Q10** (records): `status.lifecycle`, `status.staleness`, and
  `status.verification` are required on every record; vacuous dimensions
  carry a default value, never an omission. Record-type-specific lifecycle
  vocabularies remain the job of validator rule V0-04.
- **Q11** (machine summary): the summary MUST carry `failures`,
  `diagnostics`, `open_proposals`, `stale`, and `renders` in addition to the
  v0.1 draft fields. The `renders` list covers the other committed renders
  (the summary does not list itself, keeping the generator a fixed point).
  Structural conformance is V0-11; summary-artifact divergence remains V5-03.

## Validator rule IDs added by schema enforcement

The reference validator enforces these schemas and emits stable rule IDs
(unfreeze candidates batched into the v0.1.0 promotion; the RFC Appendix A
catalog gains them at the promotion):

```text
V0-07  Cell schema conformance (Q7)
V0-08  Actor schema conformance (Q8)
V0-09  Semantic-record schema conformance (Q9, Q10)
V0-10  Object record conformance (Q3, Q5)
V0-11  Machine summary schema conformance (Q11)
V0-12  Manifest environment conformance (Q2)
V0-13  Run/commit schema conformance
```

Status-vocabulary violations surfaced by the run schema map to the existing
V0-04. The corpus exercises every new rule: PATH-026 (V0-07), PATH-027
(V0-08), PATH-028 (V0-09), PATH-029 (V0-10), PATH-030 (V0-11 + V5-03),
PATH-031 (V0-12).

## Exploded-representation layout notes

- Committed diagnostics (Level 2) live in `diagnostics.json` (a list of
  objects conforming to `diagnostic.schema.json`).
- Object records live in `objects/records/<digest>.json` in the exploded
  representation; in the physical `.solnb` container (decision Q1) they
  accompany each object entry.
