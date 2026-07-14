# Sol

Sol is a proposed self-contained, versioned computational work artifact for humans, software tools, and autonomous or semi-autonomous agents.

It preserves execution structure, source cells, outputs, provenance, actors, semantic records, failures, verification, history, and rendered views as parts of a canonical computational artifact rather than requiring the next reader to reconstruct that information from HTML, Markdown, or another terminal rendering.

> **This repository contains an executable Python validator and a corpus generator that produces 31 conformance cases—6 golden cases and 25 pathological cases—in addition to the frozen RFC.**

## Run it

Python 3.10 or later is required.

From the repository root:

```bash
python -m solval.make_corpus corpus
python -m solval.validate corpus/GOLD-01/artifact.sol.d
python -m solval.validate --profile strict corpus/PATH-003/artifact.sol.d
python -m solval.validate_corpus corpus
```

The first command regenerates the `corpus/` directory from scratch. Permanent examples and manually maintained artifacts belong under `examples/`, not under the generated corpus directory.

The final command should report that all generated cases satisfy their expected diagnostics.

## Authorship and publication identity

This repository is maintained under the GitHub handle **LopezNuance**.

The same author publishes explanatory articles on Medium under the name **Jamweba**. The Medium articles and this repository describe the same Sol project and were written by the same person.

Related articles:

- [Markdown Isn’t Enough. HTML Isn’t Either.](https://medium.com/codetodeploy/markdown-isnt-enough-html-isn-t-either-6336e9612462?source=friends_link&sk=265fa67996de8a899defba38e4ca3510)
- [The Sol System](https://jam2we5b3a.medium.com/the-sol-system-c05e5436e028?sk=05163c59ae16d07e7745edb4f0d34aeb)

The articles explain the motivation and architecture. The frozen RFC, executable validator, and conformance corpus in this repository are the technical reference and implementation materials.

## Repository information

This repository includes:

- the frozen [RFC-SOL-0001 v0.1.0 draft](docs/RFC-SOL-0001-v0.1.0-draft-freeze.md);
- the `solval` prototype validator;
- a deterministic golden and pathology corpus generator;
- machine-summary generation and validation;
- an exploded debug artifact example under `examples/exploded-debug/`;
- deterministic diagnostics for the frozen V0–V5 validation catalog.

## Sol Validator Prototype

This is the initial reference validator and pathology corpus for RFC-SOL-0001 v0.1.0-draft.

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
