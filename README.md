# Repository Information

This repository includes both the Sol RFC (Sol_RFC_v1.md) as well as a prototype validator explained below.


# Sol Validator Prototype (v0.1.0-draft)

This is an initial reference validator and pathology corpus for RFC-SOL-0001 v0.1.0-draft.

It uses the non-normative exploded debug representation:

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
  renders/machine_summary.json
  expected_diagnostics.json
```

## Quick start

```bash
python -m solval.make_corpus corpus
python -m solval.validate corpus/GOLD-01/artifact.sol.d
python -m solval.validate --profile strict corpus/PATH-003/artifact.sol.d
python -m solval.validate_corpus corpus
```

The validator is intentionally conservative and schema-light. It implements the frozen RFC validation catalog V0-V5 as executable checks where possible, and emits deterministic JSON diagnostics.

## Scope

Implemented enough to exercise the frozen pathology corpus:

- references: `cell:`, `record:`, `run:`, `commit:`, `branch:`, `render:`, `object:sha256:`, `digest:sha256:`, named outputs
- object store resolution and hash checking
- execution order validation for linear artifacts
- declared dependency consistency
- partial-success prefix checks
- semantic staleness checks for claim/evidence/decision chains
- proposal application linkage and changeset matching
- authorization/protected branch checks and self-review checks
- machine summary generation and comparison
- render honesty checks

This is not yet a full Sol implementation: no physical `.solnb` container, no executor, no renderer beyond machine summary generation, and no JSON Schema enforcement beyond basic structural checks.
