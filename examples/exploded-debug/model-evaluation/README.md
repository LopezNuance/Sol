# Exploded Sol example: model evaluation

This directory is a stable, human-readable example of the non-normative exploded
debug representation described by RFC-SOL-0001 section 56. It is stored under
`examples/`, not `corpus/`, because the repository's corpus directory is generated
and is deleted and rebuilt by `python -m solval.make_corpus corpus`.

The ZIP containing this directory is rooted at `examples/`. Extract it from the
repository root. It creates only:

```text
examples/exploded-debug/model-evaluation/
```

It does not overwrite or modify `corpus/`, `solval/`, `schemas/`, `docs/`,
`pyproject.toml`, or the repository README.

## Validate with the repository's existing code

From the repository root:

```bash
python -m solval.validate \
  examples/exploded-debug/model-evaluation/artifact.sol.d
```

Expected output:

```text
valid
```

The example can also be exercised through the existing corpus runner without
placing it in the generated corpus directory:

```bash
python -m solval.validate_corpus \
  examples/exploded-debug \
  --strict-extra
```

Expected result:

```text
PASS model-evaluation: expected=[] got=[]

1/1 cases satisfied expected diagnostics
```

## Safety and integration behavior

This package contains no Python package, module, generator, installer, or executable
script. The only Python source is the string stored in `cells/cell_014.json`; it is
artifact content and the validator does not execute it. Rendering also does not
execute code.

The directory layout intentionally matches what the current `Artifact.load()`
implementation consumes:

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
  renders/*.json
  renders/report.html
  expected_diagnostics.json
```

Objects use the flat SHA-256 layout produced by the current corpus generator. Every
`object:sha256:` reference resolves to a file whose name and contents match its
digest. `expected_diagnostics.json` uses the object shape required by the current
`validate_corpus` implementation:

```json
{
  "expected_rule_ids": []
}
```

## Example contents

The artifact demonstrates:

- a visible linear execution order;
- prose, configuration, data, code, display, and anchor cells;
- human, agent, and tool actors;
- a successful run with a named-output binding;
- internally stored, content-addressed data and rendered output;
- task, evidence, claim, decision, and verification records;
- a verified claim backed by a passed verification record;
- two internal commits on a protected `main` branch;
- a machine-summary render matching current validator output; and
- a script-free HTML report tied to `commit:commit_042`.

This is an example artifact, not an additional corpus generator and not a replacement
for the generated `corpus/GOLD-01` case.
