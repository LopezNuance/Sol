# Container Benchmark (RFC-SOL-0001 §59 Q1)

Benchmarks candidate physical containers for the `.solnb` artifact against the
bounded-read requirements REQ-014.1..REQ-014.5 (RFC §14).

## Run

```bash
python3 container_benchmark/benchmark.py
```

Standard library only. Deterministic (synthetic payload seeded 20260907).
Outputs `report.json` (machine-readable) and a summary table on stdout.
Packed test containers land in `work/` (gitignored, regenerated on each run).

## Inputs

- `GOLD-01` — the real golden corpus artifact
  (`sol_validator/corpus/GOLD-01/artifact.sol.d`).
- `GOLD-01+16MiB-synthetic` — GOLD-01 plus one deterministic 16 MiB object,
  to expose the random-access contrast at realistic scale. Not part of the
  corpus; labeled synthetic in the report.

## Candidates

- `exploded-dir` — plain directory tree (current non-normative debug representation).
- `zip-flat` — single-file ZIP, STORED entries, layout mirrors `artifact.sol.d/`.
- `tar` — single-file tar (sequential; included as contrast).

## Metrics

Each operation opens the container fresh and counts bytes read via wrappers.
`amplification = bytes_read / artifact_bytes` is the primary metric: how much
of the artifact a bounded operation must touch.

## Result (2026-09-07)

- `tar` is disqualified: bounded reads require a full sequential scan
  (~21x amplification on the 12 KB artifact, ~2.6x on the 16 MiB one).
- `zip-flat` and `exploded-dir` both satisfy REQ-014.1..014.5 with bounded
  reads. ZIP's central-directory overhead is proportional to entry count, not
  artifact size: 0.02% amplification for a manifest read on the 16 MiB
  artifact.
- Decision (see `docs/decisions/2026-09-07-v01-blocking-questions.md`, Q1):
  the v0.1 reference container is a single-file ZIP with STORED entries and an
  internal layout identical to `artifact.sol.d/`; the exploded directory
  remains the non-normative debug representation.
