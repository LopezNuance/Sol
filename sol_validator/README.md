# Sol Validator and Reference MVP (v0.1.0-draft)

Reference validator and MVP implementation surface for RFC-SOL-0001
v0.1.0-draft (frozen). The validator uses the non-normative exploded debug
representation (RFC section 56) and the physical `.solnb` container
(decision Q1):

```text
artifact.sol.d/
  manifest.json
  execution_structure.json
  cells/*.json
  records/*.json
  actors/*.json
  runs/*.json
  commits/*.json
  objects/sha256/<digest>
  objects/records/<digest>.json
  renders/machine_summary.json
  diagnostics.json
  expected_diagnostics.json
```

## Quick start

```bash
python -m solval.make_corpus corpus
python -m solval.validate corpus/GOLD-01/artifact.sol.d
python -m solval.validate --profile strict corpus/PATH-003/artifact.sol.d
python -m solval.validate_corpus corpus --strict-extra
python -m solval.mvp_demo
```

GOLD-01 is assembled from the RFC's own spec examples (sections 15, 16, 18,
21-27, 30, 41, 42, 47, 48) with real sha256 digests; it is the Change
Control "examples must validate" gate (see
`docs/errata/RFC-SOL-0001-errata.md`, E-001).

## Schema enforcement

The published normative schemas in `schemas/` (see `schemas/README.md`) are
enforced by the validator via JSON Schema (draft 2020-12). Violations emit
stable rule IDs V0-07..V0-13 (plus V0-04 for status vocabulary). The corpus
exercises every new rule (PATH-026..PATH-031).

## MVP surface (RFC section 57, Phase 4)

- `solval/container.py` — physical `.solnb` container (decision Q1):
  single-file ZIP, STORED entries, layout identical to `artifact.sol.d/`.
  Bounded reads (REQ-014.1/014.2), random object access (REQ-014.3),
  integrity verification (REQ-014.4). The validator accepts `.solnb` files
  directly.
- `solval/render.py` — safe HTML/Markdown rendering from selected commits
  (section 47): identifies the source commit, discloses stale/invalidated/
  unverified content and incomplete import provenance, never executes code,
  emits no scripts or event handlers (INV-07).
- `solval/executor.py` — reference executor (section 12.5): linear execution
  in committed order against a declared kernel model (registered operations;
  unregistered source is a failure, never executed), partial-success prefix
  commits, failure records paired to the same run (sections 30/31/32).
- `solval/import_ipynb.py` — `.ipynb` import (section 53, decision Q6):
  visible cell order preserved, outputs into the internal object store,
  provenance declared incomplete, imported outputs classified
  `staleness: unknown` / `verification: unverified`, initial import commit,
  no fabricated run records.
- `solval/mvp_demo.py` — deterministic demonstration driver; writes recorded
  evidence to `demos/` (container, executor, render, import) and
  `demos/manifest.json`.

## Scope

Implemented to exercise the frozen pathology corpus and the MVP surface:

- references: `cell:`, `record:`, `run:`, `commit:`, `branch:`, `render:`,
  `object:sha256:`, `digest:sha256:`, named outputs
- object store resolution and hash checking
- execution order validation for linear artifacts
- declared dependency consistency
- partial-success prefix checks
- semantic staleness checks for claim/evidence/decision chains
- proposal application linkage and changeset matching
- authorization/protected branch checks and self-review checks
- machine summary generation and comparison (RFC section 48 components per
  decision Q11)
- render honesty checks
- published-schema enforcement (V0-07..V0-13)
- `.solnb` container, safe renderer, reference executor, `.ipynb` import
  (MVP items 1, 35-38)

Not yet implemented (section 57 MAY-defer list and post-v0.1): explicit
graph execution, branch merges, multi-language execution, Work Server
Protocol, state checkpoints, container-level compression.
