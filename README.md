# Sol

Sol is a proposed self-contained, versioned computational work artifact for humans, software tools, and autonomous or semi-autonomous agents.

It preserves execution structure, source cells, outputs, provenance, actors, semantic records, failures, verification, history, and rendered views as parts of a canonical computational artifact rather than requiring the next reader to reconstruct that information from HTML, Markdown, or another terminal rendering.

> **This repository contains the frozen RFC-SOL-0001 v0.1.0
> specification, its companion RFC-SOL-QRY-0001 v0.3.0 query
> specification, executable reference implementations, and validating
> conformance corpora.**

## Naming note

Sol was independently named and publicly released as a computational
artifact project before OpenAI’s general public announcement of its
GPT-5.6 model names.

This project is unrelated to OpenAI and is not affiliated with, endorsed
by, or derived from OpenAI or its products.

“Sol” remains a provisional project name and is subject to namespace,
trademark, and ecosystem review.

## Authorship and publication identity

This repository is maintained under the GitHub handle **LopezNuance**.

The same author publishes explanatory articles on Medium under the name **Jamweba**. The Medium articles and this repository describe the same Sol project and were written by the same person.

Related articles:

- [Markdown Isn’t Enough. HTML Isn’t Either.](https://medium.com/codetodeploy/markdown-isnt-enough-html-isn-t-either-6336e9612462?source=friends_link&sk=265fa67996de8a899defba38e4ca3510)
- [The Sol System](https://jam2we5b3a.medium.com/the-sol-system-c05e5436e028?sk=05163c59ae16d07e7745edb4f0d34aeb)

The articles explain the motivation and architecture. The frozen RFC, executable validator, and conformance corpus in this repository are the technical reference and implementation materials.

## Repository contents

- `Sol_RFC.md` — RFC-SOL-0001 v0.1.0, "Sol — A Cooperative Computational
  Work Artifact" (promoted 2026-09-08; docx export in `documentation/`)
- `documentation/RFC-SOL-QRY-0001-v0.3.0.md` — companion query
  specification, FROZEN 2026-09-11 (19/19 freeze gate)
- `sol_validator/` — reference validator for the base RFC: the V0–V5
  validation catalog as executable checks, the published JSON Schemas
  (Appendix C), the `.solnb` container, a reference executor, a safe
  renderer, `.ipynb` import, and the 37-case conformance corpus
  (`sol_validator/corpus/`)
- `qry_reference_impl/` — QRY reference implementation: certified bound
  algebra, typed-AST canonicalization, exact evaluator, rewrite-rule
  registry with proof kernel, 136-case corpus, and the freeze-gate
  harness
- `corpus/` — exploded-representation artifact instances (31-case
  prototype lineage)
- `container_benchmark/` — evidence for the Q1 container decision
  (single-file ZIP, STORED entries)
- `docs/` — decision notes, errata log, reviews, and submission packages

## Run it

Python 3.12 or later is required, with the `jsonschema` package
(`pip install jsonschema`). The repository virtualenv (`.venv`,
uv-managed) already has it:

```bash
source .venv/bin/activate
```

Base RFC validator and corpus (run from `sol_validator/`):

```bash
python -m solval.validate_corpus corpus --strict-extra
python -m solval.mvp_demo
```

The first command should report that all 37 corpus cases satisfy their
expected diagnostics; the second runs the 12 recorded demonstration
checks.

QRY reference implementation (run from `qry_reference_impl/`):

```bash
python -m pytest -q
python -m qryref.validate_corpus corpus
python -m qryref.gate_check
```

The gate check re-evidences all 19 freeze conditions from the committed
artifacts and should report 19/19 with status FROZEN.

## Status

- RFC-SOL-0001: **v0.1.0** (promoted 2026-09-08 from the v0.1.0-draft
  freeze; internal submission stage complete)
- RFC-SOL-QRY-0001: **v0.3.0, FROZEN** (2026-09-11; 19/19 gate)
- Venue: internal (done) → public specification (in progress) →
  IETF-style (final); see `docs/decisions/2026-09-07-phase0-venue.md`
