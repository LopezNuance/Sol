# QRY Reference Implementation v0.1

This package is a reconstructed QRY reference implementation generated from the available thread context. It is **not guaranteed to be byte-identical** to the missing OpenAI sandbox package, but it contains the requested components:

- bound-algebra reference implementation
- validators
- three JSON Schemas
- a Substrait profile
- a 69-case QRY corpus
- proof certificates for valid corpus cases

## What QRY is in this reconstruction

QRY is a compact JSON intermediate representation for a bounded subset of relational algebra. It is intended to support static validation of query plans, conservative row/schema bound inference, and proof-certificate validation.

The focus is not execution. The focus is proving conservative bounds over query plans and producing machine-checkable certificates.

## Quick start

```bash
python -m qryref.make_corpus corpus
python -m qryref.validate corpus/cases/QRY-001
python -m qryref.validate_corpus corpus
```

Expected corpus result:

```text
69/69 cases satisfied expected diagnostics
```

The corpus harness treats expected diagnostics as a required subset, since malformed artifacts may trigger multiple related failures.

## Project layout

```text
qryref/                 Python reference implementation
schemas/                QRY query, bounds, and certificate JSON Schemas
substrait/              QRY Substrait profile and mapping notes
corpus/cases/           69 generated corpus cases
certificates/           proof certificates for valid cases
```

## Validator layers

- `QRY-SCHEMA-*` JSON Schema and shape failures
- `QRY-SEM-*` semantic query failures
- `QRY-BOUND-*` bound mismatch failures
- `QRY-CERT-*` proof certificate failures
- `QRY-SUBSTRAIT-*` profile mapping failures

## Caveat

The old QRY package was not available in the sandbox. This reconstruction uses the terms from the conversation — bound algebra, validators, three schemas, Substrait profile, 69-case corpus, proof certificates — and fills in a coherent v0.1 design around them.
