# Authoritative Exploded RFC-SOL-0001 Representation Profile

Date: 2026-09-08 (UTC)
Profile ID: `solqry-authoritative-exploded/v1`
Status: **published** (clears SOL-QRY v0.3 freeze-gate condition 8)
Machine-readable form: `docs/profiles/exploded-representation-profile.json`

## Purpose

SOL-QRY v0.3 freeze-gate condition 8 requires:

> Exact evaluator runs over the authoritative exploded RFC-SOL-0001
> representation.

The v0.3 gate run (`freeze_report.json`, 18/19) recorded the blocker:

> no authoritative RFC-SOL-0001 exploded representation profile was supplied

The reference scanning profile `solqry-reference-exploded/v1` already passed
its scan (`reference_profile_scan_passed: true`). What was missing is the
**authoritative designation**: a published profile that fixes *which* exploded
RFC-SOL-0001 representation the QRY evaluator runs against. This document is
that publication + designation step. It depends only on the base RFC's
representation decision (Phase 1, resolved) and is now anchored to the
promoted **RFC-SOL-0001 v0.1.0** baseline.

## Designation

The authoritative exploded representation is the `artifact.sol.d/` layout
defined by RFC-SOL-0001 §56 (Exploded Debug Representation) as instantiated by
the reference validator and corpus. It is non-normative: the physical `.solnb`
container (§14.6) is the normative interchange form. The exploded form is the
debug, validation, and corpus-construction representation.

Authoritative layout (the layout the reference validator consumes):

```text
artifact.sol.d/
  manifest.json
  execution_structure.json
  diagnostics.json
  cells/<cell_id>.json
  records/<record_id>.json
  actors/<actor_id>.json
  runs/<run_id>.json
  commits/<commit_id>.json
  objects/sha256/<sha256-hex>            # object payload, flat (full digest)
  objects/records/<sha256-hex>.json      # companion object record
  renders/<render_id>.json               # committed renders
  renders/machine_summary.json           # pseudo-render (machine summary)
```

Corpus-only (not part of the artifact): `expected_diagnostics.json` (the
expected diagnostic set for a pathology case).

## Reference profile and scan

- **Reference scanning profile:** `solqry-reference-exploded/v1`
- **Scan status:** passed (`reference_profile_scan_passed: true`, per
  `freeze_report.json` condition 8 evidence)

The reference profile is the QRY-side scanning contract; this authoritative
profile designates the Sol-side representation it scans.

## Instances

| Instance | Path | Cases | Notes |
|---|---|---|---|
| Prototype corpus | `corpus/` | 31 | Original 31-case corpus (GOLD-01..06, PATH-001..025); the OpenAI-sandbox 31/31 lineage |
| Current corpus | `sol_validator/corpus/` | 37 | Adds PATH-026..031 (V0-07..V0-13); GOLD-01 reassembled from spec examples with real digests |

Both instances use the authoritative layout above. The current corpus is the
authoritative instance for v0.1.0 conformance; the prototype corpus is retained
as the lineage ancestor.

## Finding: §56 example drift (errata-class)

The §56 illustrative example in `Sol_RFC.md` has drifted from the layout the
reference validator and corpus actually use:

| §56 example shows | Authoritative layout uses |
|---|---|
| `manifest.yaml` | `manifest.json` |
| `objects/sha256/1f/4c/1f4c9a...` (sharded) | `objects/sha256/<full 64-hex digest>` (flat) |
| (no object records) | `objects/records/<digest>.json` |
| `diagnostics/expected.json` | `diagnostics.json` (committed) + `expected_diagnostics.json` (corpus-only) |
| `renders/report.html` | `renders/<render_id>.json` (e.g. `render_012.json`) + `machine_summary.json` |

§56 is explicitly non-normative and marked "Example:", so this is
errata-class (example hygiene / non-normative clarification), not an unfreeze
candidate. The authoritative profile above is the source of truth for the
layout; the §56 example SHOULD be updated to match (recorded as a finding for
the next errata pass; not applied here to keep this change scoped to the QRY
unblock).

## Effect on the freeze gate

With this profile published and designated, condition 8's blocker
("no authoritative ... profile was supplied") is cleared at the
spec/designation level. The remaining gate work is the reproducibility of the
QRY implementation evidence (see
`docs/qry/2026-09-08-reproducibility-gap.md`), which requires exporting the
QRY implementation artifacts from the OpenAI sandbox and re-running the gate.
