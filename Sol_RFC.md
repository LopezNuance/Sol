# RFC-SOL-0001: Sol — A Cooperative Computational Work Artifact

## Status

v0.1.0-draft, frozen

## Change Control

This draft is frozen for implementation.

Errata may correct spelling, formatting, example hygiene, appendix text, and non-normative clarification without changing the version.

Any change to an invariant, normative requirement, status vocabulary, legal transition table, reference grammar, conformance level, or validation rule unfreezes the draft and requires a version bump.

Complete examples intended for conformance use must validate. Partial examples and schema fragments should be marked as such when used outside this RFC.

## Project Name

Sol is a provisional project name.

Proposed file extension:

```text
.solnb
```

Proposed media type:

```text
application/vnd.sol.notebook
```

The project name, extension, and media type remain subject to namespace, trademark, and ecosystem review.

## Abstract

Sol is a proposed self-contained, versioned computational work artifact for humans, software tools, and autonomous or semi-autonomous agents.

Sol is motivated by a handoff problem. Computational work is often flattened into prose, Markdown, HTML, dashboards, or other rendered surfaces. Those views may be useful for humans, but they are often terminal formats: information about how a result was produced, what data supported it, what assumptions controlled it, what failed, what was rejected, and what requires review cannot be reliably reconstructed from the rendering.

Sol treats the artifact itself as the source of truth. A Sol artifact stores source cells, execution structure, runtime declarations, outputs, provenance, internal history, actors, semantic records, failure records, verification records, and rendered views. HTML, Markdown, PDF, slides, dashboards, machine summaries, and other outputs are derived views of committed artifact state, not the canonical product.

Sol’s execution invariant is:

> Visible execution structure is valid execution structure.

For a linear Sol artifact, cell order is execution order. If execution is nonlinear, the artifact must represent that nonlinearity explicitly as a visible graph, branch, merge, or gate structure. Hidden out-of-order execution is not a valid committed state.

Sol’s collaboration invariant is:

> A Sol artifact should be as legible to its next reader as it was to its last writer, whether either is human, tool, service, or agent.

---

# 1. Purpose

This RFC defines the initial Sol artifact model.

The goal is not to replace existing notebook systems. The goal is to specify a durable computational artifact that can serve as a structured handoff object across:

* humans,
* tools,
* CI systems,
* renderers,
* validators,
* execution engines,
* and agents.

A Sol artifact should allow a recipient to determine, without executing code and without parsing rendered output:

* what was done,
* in what order,
* by whom,
* under what environment,
* using which inputs,
* producing which outputs,
* making which claims,
* supporting those claims with which evidence,
* recording which decisions,
* encountering which failures,
* which work is stale,
* which work has been verified,
* and which work awaits review or re-execution.

---

# 2. Motivation

Computational notebooks combine prose, code, output, and interpretation. They are useful for exploration and communication, but they can become weak durable records when important state lives outside the artifact.

Common problems include:

* hidden kernel state,
* out-of-order execution,
* stale outputs,
* unclear runtime assumptions,
* missing or detached output files,
* weak provenance,
* external-only version history,
* poor diff and merge semantics,
* ambiguous authorship,
* weak support for alternate branches,
* and rendered outputs that cannot be reliably converted back into structured work.

In AI-assisted workflows, the problem is sharper. If Agent A produces an HTML report and Agent B must continue the work, Agent B must recover structure from a rendered surface. It must infer which data produced a chart, which assumptions controlled a conclusion, which sources supported a claim, and which alternatives were rejected.

Sol’s premise is that this structure should not be inferred from the rendering. It should be present in the artifact.

---

# 3. Prior Art and Related Systems

Sol is informed by several existing areas.

## 3.1 Computational notebooks

Jupyter provides the dominant JSON-based computational notebook model and a broad kernel ecosystem. It is widely adopted, but important semantics such as execution order discipline, environment capture, provenance, and versioning are often external conventions rather than artifact-level guarantees.

## 3.2 Reactive notebooks

Pluto, marimo, and Observable demonstrate that reactive dataflow notebooks can reduce hidden state and keep outputs synchronized with dependencies. Sol does not claim novelty for reactive execution. Sol generalizes the requirement that the valid execution structure must be visible and canonical.

## 3.3 Notebook review and execution tools

Jupytext improves text-based review of notebooks. Nbdime provides notebook-aware diff and merge. Papermill supports parameterized execution. These tools address important parts of the notebook lifecycle but do not make the notebook artifact itself the complete versioned source of truth.

## 3.4 Literate and rendered computational documents

Quarto, R Markdown, Org-Babel, and related systems support literate computational documents and multi-target rendering. Sol treats rendering as a derived view over a committed artifact state.

## 3.5 Research objects and reproducibility packaging

RO-Crate, ReproZip, Whole Tale, and related systems address reproducible research packaging, provenance, and environment capture. Sol should align with these models where practical rather than inventing incompatible provenance concepts.

## 3.6 Data and experiment versioning

DVC, DataLad, and similar tools version data, models, and experiment artifacts around computational work. Sol’s internal versioning is concerned with the notebook artifact’s semantic history: cells, runs, outputs, records, decisions, actors, and views.

## 3.7 Workflow DAGs and orchestration

Snakemake, Nextflow, Dagster, Kedro, and related systems represent computation as workflows, DAGs, or assets. Sol does not aim to replace workflow engines. It may record their inputs, outputs, and provenance.

## 3.8 Agent protocols and agent runtimes

MCP, A2A, LangGraph, and related systems address tool access, agent communication, graph execution, checkpointing, and persistence. Sol is not a replacement for these systems. It defines a durable artifact that such systems may read, write, validate, or render.

## 3.9 AI workspace and artifact interfaces

Claude Artifacts, ChatGPT Canvas, and similar interfaces demonstrate the value of editable and rendered AI-produced workspaces. Sol’s distinction is that the rendered or editable surface is not the source of truth. The structured artifact is.

---

# 4. Goals

Sol aims to provide:

1. A self-contained computational work artifact.
2. Language-agnostic runtime declaration.
3. Visible execution structure.
4. No hidden out-of-order committed execution.
5. Internal version history.
6. Internally stored outputs and large artifacts.
7. Structured actor attribution.
8. Machine-legible semantic records.
9. Conservative stale-output and stale-record detection.
10. Provenance records for committed outputs.
11. Cost-bounded reads for agents and tools.
12. Rendered views tied to source commits.
13. Safe rendering without code execution.
14. Machine summary rendering for handoff and bounded-context consumption.
15. A foundation for future structured coordination protocols.

---

# 5. Non-Goals

Sol does not attempt to:

1. Replace all existing notebooks.
2. Replace Jupyter, marimo, Pluto, Observable, Quarto, or workflow systems.
3. Require a specific programming language.
4. Require a specific UI.
5. Require a specific kernel protocol.
6. Require Git as the internal storage model.
7. Replace workflow engines.
8. Replace research-object packaging standards.
9. Replace agent communication protocols such as MCP or A2A.
10. Provide full database ACID semantics in v0.1.
11. Require code execution during rendering.
12. Require that humans read raw JSON.

---

# 6. Conventions

The keywords MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, MAY, and OPTIONAL are used as normative requirement language.

Normative invariants use identifiers of the form `INV-*`.

Normative requirements use identifiers of the form `REQ-*`.

Examples are non-normative unless explicitly stated.

---

# 7. Core Invariants

## INV-01: Artifact source of truth

The Sol artifact is the canonical computational record.

Rendered views are derived from committed artifact state.

## INV-02: Visible execution structure

A committed run MUST follow the artifact’s visible execution structure.

For a linear artifact, cell order is execution order.

For a graph artifact, the graph is the execution structure.

## INV-03: No hidden out-of-order execution

A Sol runtime MUST NOT commit results produced by executing cells in an order not represented by the artifact.

If a different execution order is desired, the user or agent MUST reorder cells, create a branch, or define an explicit execution graph.

## INV-04: Serialized state only

Only state serialized into the artifact is considered reproducible artifact state.

Live kernel memory, transient variables, local filesystem side effects, UI caches, and partial runtime snapshots are not authoritative unless captured as declared artifact objects with provenance.

## INV-05: Outputs are derived

An output is valid only relative to the cell source, inputs, environment, execution structure, actor context, and commit that produced it.

## INV-06: Internal storage of required artifacts

Required outputs and large artifacts MUST NOT depend on detachable sidecar files.

They SHOULD be stored in the artifact’s internal content-addressed object store.

## INV-07: Safe rendering

Rendering MUST NOT execute code by default.

## INV-08: Machine legibility without rendering

Every committed artifact state MUST be interpretable through structured metadata.

Information required to understand what was done, by whom, under what conditions, and with what result MUST NOT exist only inside a rendered view, prose cell, or opaque output blob.

Rendered views are projections. The structured layer is authoritative.

## INV-09: Attributed agency

Every commit, run, proposal, review, failure record, verification record, and signature MUST identify its actor.

Actors are typed:

```text
human
agent
tool
service
system
```

Agent actors MUST record sufficient identity to support audit and, where feasible, reproduction.

## INV-10: Bounded structural reads

A Sol artifact MUST support progressive disclosure.

A reader MUST be able to inspect the manifest, execution skeleton, cell summaries, staleness state, actor attribution, and semantic-record index without retrieving object-store payloads.

---

# 8. Ontology

Sol distinguishes between cells and semantic records.

This distinction is normative.

## 8.1 Cells

Cells provide document structure, execution structure, and narrative placement.

Examples:

* prose cell,
* code cell,
* data cell,
* display cell,
* anchor cell,
* gate cell.

Cells may appear in linear order or in an explicit execution graph.

## 8.2 Semantic records

Semantic records are first-class artifact objects with their own identity, schema, lifecycle, dependencies, and provenance.

Examples:

* task record,
* claim record,
* evidence record,
* decision record,
* proposal record,
* review record,
* failure record,
* verification record.

Semantic records exist independently of narrative position.

## 8.3 Anchor cells

An anchor cell places a semantic record into the notebook’s narrative flow.

An anchor cell MUST reference exactly one semantic record by ID.

An anchor cell MUST NOT duplicate the canonical content of the semantic record.

Example:

```json
{
  "cell_id": "cell_claim_anchor_007",
  "cell_type": "sol:cell/anchor",
  "anchors_record": "record:claim_007",
  "render_hint": {
    "style": "callout"
  }
}
```

A semantic record MAY have:

* zero anchors,
* one anchor,
* multiple anchors.

Deleting an anchor cell does not delete the record.

Records are removed, superseded, or withdrawn only through explicit committed operations. Prior record states remain available through artifact history.

## 8.4 Addressable units

The following are independently addressable:

```text
cells
records
named outputs
objects
runs
commits
branches
renders
actors
signatures
```

---

# 9. Reference Grammar

Sol supports short-form intra-artifact references and full cross-artifact references.

## 9.1 Artifact identity

Every Sol artifact MUST declare an `artifact_id`.

Example:

```yaml
artifact_id: "art_01j9x7k9k5m2c8v6h3p4q2r1s0"
artifact_did: "did:key:z6Mk..."
```

`artifact_id` MUST be stable for the artifact lineage.

`artifact_did` is OPTIONAL.

If an artifact is forked or copied into a new lineage, the new artifact SHOULD receive a new `artifact_id` and MAY declare:

```yaml
forked_from: "sol://art_01j9x7k9k5m2c8v6h3p4q2r1s0/commits/commit_042"
```

## 9.2 Short-form references

Short-form references are intra-artifact.

Examples:

```text
cell:cell_014
record:claim_007
run:run_008
commit:commit_042
branch:main
render:render_012
cell:cell_014#metrics_table
object:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403
digest:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403
```

## 9.3 Full references

Full references use:

```text
sol://<artifact_id>/<kind>/<id>
```

Examples:

```text
sol://art_01j9x7k9k5m2c8v6h3p4q2r1s0/cells/cell_014
sol://art_01j9x7k9k5m2c8v6h3p4q2r1s0/records/claim_007
sol://art_01j9x7k9k5m2c8v6h3p4q2r1s0/objects/sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403
```

Unresolvable cross-artifact references are treated as external references and MUST declare availability when used as evidence.

## 9.4 Named-output references

Named-output references have the form:

```text
cell:<cell_id>#<output_name>
```

Example:

```text
cell:cell_014#metrics_table
```

A named-output reference resolves through the current valid run on the selected branch or commit.

## 9.5 Object references and digest references

Sol distinguishes retrievable objects from bare digests.

```text
object:sha256:<digest>
```

means the referenced bytes MUST resolve inside the internal object store.

```text
digest:sha256:<digest>
```

means a content hash is asserted, but retrieval from the Sol object store is not implied.

Fields whose semantic is “retrieve this content” MUST use `object:`.

Fields whose semantic is “identify or verify content held inline or elsewhere” SHOULD use `digest:`.

Examples:

* `source_hash` uses `digest:`.
* `configuration_digest` uses `digest:`.
* `object_ref` uses `object:`.
* provenance output hashes use `object:` when the output is stored internally.
* external package lockfile hashes may use `digest:` unless the lockfile is stored as an object.

## 9.6 Named-output references versus digest references

Authored fields such as evidence `source_ref` and claim `supporting_evidence` SHOULD use named-output or record references when the intended meaning is “the current valid output of this cell” rather than a specific immutable object.

Provenance and verification records MUST use digest or object references for concrete identity.

---

# 10. Terminology

## Artifact

The complete self-contained Sol container.

## Cell

A typed unit of document structure or executable structure.

## Anchor cell

A cell that places a semantic record into narrative or rendered flow.

## Display cell

A cell that places an output or object into narrative or rendered flow.

## Gate cell

A structural cell that routes execution according to a decision record.

## Semantic record

A first-class artifact object representing a task, claim, evidence item, decision, proposal, review, failure, verification, or other semantic unit.

## Execution structure

The visible structure that determines valid execution. This may be linear or graph-shaped.

## Actor

A human, agent, tool, service, or system that performs an action recorded in the artifact.

## Run

An attempt to execute one or more cells under a specific artifact state and runtime manifest.

## Failure record

A committed record of an attempted run or operation that failed.

## Verification record

A committed record that verifies, refutes, reruns, checks, signs, or otherwise evaluates another artifact object.

## Commit

An immutable artifact history checkpoint.

## Branch

An alternate artifact history.

## Object store

The internal content-addressed store for outputs and large artifacts.

## Rendered view

A derived output such as HTML, Markdown, PDF, slides, dashboard, machine summary, or audit view.

---

# 11. Bounded Read Model

A Sol artifact SHOULD be readable in increasing cost layers.

## Level 0: Manifest

Artifact identity, version, required features, runtime declarations, security policy, and packaging metadata.

## Level 1: Execution skeleton

Cell IDs, cell types, ordering or graph edges, branch heads, commit heads, staleness state, and object references.

## Level 2: Structured summaries

Cell summaries, semantic-record summaries, actor records, proposal states, evidence indexes, decision indexes, run summaries, failure summaries, diagnostic summaries, and machine-summary metadata.

## Level 3: Full sources and records

Complete cell source, prose, code, configuration, and full semantic-record bodies.

## Level 4: Object payloads

Plots, tables, logs, rendered views, datasets, binary outputs, media, and other large objects.

A conforming artifact MUST permit Levels 0–2 to be read without retrieving Level 4 object payloads.

---

# 12. Conformance Levels

## 12.1 Reader

A Reader can open an artifact, inspect the manifest, list cells, inspect structural indexes, and read history metadata without executing code.

## 12.2 Validator

A Validator can validate schema, execution structure, commit ancestry, object references, digests, hashes, provenance, actor records, semantic-record dependencies, status transitions, authorization policy, and stale status.

## 12.3 Machine Consumer

A Machine Consumer can read structured summaries, semantic records, actor records, run records, failure records, and verification records without parsing rendered views.

## 12.4 Renderer

A Renderer can render selected committed states to one or more targets without executing code by default.

Renderer conformance REQUIRES support for:

```text
sol:render/machine_summary
```

## 12.5 Executor

An Executor can run cells according to visible execution structure and commit run records, outputs, provenance, and failure records.

## 12.6 Editor

An Editor can modify cells, reorder cells, create commits, manage branches, and produce structured diffs.

## 12.7 Server

A Server exposes artifact operations programmatically for CI, hosted execution, agent workflows, or future Work Server Protocol integration.

---

# 13. Artifact Structure

A Sol artifact is logically composed of:

```text
manifest
indexes
execution_structure
cells
records
actors
history
branches
runs
provenance
object_store
renders
signatures
diagnostics
```

Per-type record indexes MAY exist under `indexes`.

Examples:

```text
indexes/tasks
indexes/claims
indexes/evidence
indexes/proposals
indexes/decisions
indexes/failures
indexes/verifications
```

Semantic records themselves live in `records`.

The physical container format is not fixed in this RFC, but the container MUST support:

* safe manifest inspection without execution,
* bounded reads for Levels 0–2,
* random access to object metadata,
* range reads for large objects where feasible,
* integrity verification without full execution,
* and internal storage of required objects.

---

# 14. Container Requirements

Sol v0.1 does not mandate a single container, but the container MUST satisfy these requirements.

## REQ-014.1: Bounded manifest read

A reader MUST be able to read the manifest without scanning all object payloads.

## REQ-014.2: Structural index read

A reader MUST be able to read the execution skeleton and structured indexes without retrieving full object payloads.

## REQ-014.3: Random object access

A reader SHOULD be able to retrieve object metadata and individual object payloads without unpacking the full artifact.

## REQ-014.4: Integrity verification

A reader MUST be able to verify manifest, index, and object integrity through declared hashes or signatures.

## REQ-014.5: Progressive loading

A remote artifact SHOULD support progressive loading over range-capable storage.

## 14.6 Container guidance

The reference implementation SHOULD prefer a container with native random access, such as an embedded database or indexed package layout.

A stream-oriented container is acceptable only if paired with an index sufficient to satisfy bounded reads and random object access.

---

# 15. Runtime Manifest

Every Sol artifact MUST include a runtime manifest.

Example:

```yaml
sol_version: "0.1"
artifact_type: "sol_notebook"
artifact_id: "art_01j9x7k9k5m2c8v6h3p4q2r1s0"
artifact_did: "did:key:z6Mk..."

required_features:
  - "sol:feature/linear_execution"
  - "sol:feature/internal_object_store"
  - "sol:feature/machine_summary"

optional_features:
  - "sol:feature/signatures"
  - "sol:feature/external_evidence"

title: "Model Evaluation Report"

runtime:
  primary_language: "python"
  language_version: "3.12"
  kernel_adapter: "sol-kernel-python"
  allowed_languages:
    - language: "python"
      kernel_adapter: "sol-kernel-python"
    - language: "sql"
      kernel_adapter: "sol-kernel-sql"

environment:
  environment_id: "env_001"
  package_manifest: "digest:sha256:1111111111111111111111111111111111111111111111111111111111111111"
  container_ref: "registry.example/sol-runner@sha256:2222222222222222222222222222222222222222222222222222222222222222"
  sbom_ref: "object:sha256:3333333333333333333333333333333333333333333333333333333333333333"

execution:
  structure: "linear"
  partial_execution_policy: "invalidate_downstream"
  deterministic: false
  random_seed: 1234

security:
  sandbox_profile: "sandbox_minimal"
  network_access: false
  execution_requires_confirmation: true

rendering:
  default_view: "html"
  allowed_views:
    - "html"
    - "markdown"
    - "pdf"
    - "audit"
    - "machine_summary"
```

The manifest is part of the artifact’s execution contract.

---

# 16. Actor Model

Every action that mutates, verifies, reviews, signs, or renders artifact state MUST identify an actor.

## 16.1 Actor types

Allowed actor types include:

```text
human
agent
tool
service
system
```

## 16.2 Actor immutability

Actor records are immutable after commit.

If an actor’s identity, configuration, model version, prompt template, or tool policy changes, the artifact MUST create a new actor record or actor version. Existing actor references continue to resolve to the original actor record.

## 16.3 Human actor

```json
{
  "actor_id": "human:alice",
  "actor_type": "human",
  "display_name": "Alice",
  "auth_ref": "identity_provider:user_123"
}
```

## 16.4 Agent actor

```json
{
  "actor_id": "agent:eval_reviewer_001",
  "actor_type": "agent",
  "model_id": "provider/model-name",
  "model_version": "2026-01-01",
  "configuration_digest": "digest:sha256:4444444444444444444444444444444444444444444444444444444444444444",
  "prompt_template_digest": "digest:sha256:5555555555555555555555555555555555555555555555555555555555555555",
  "tool_policy_digest": "digest:sha256:6666666666666666666666666666666666666666666666666666666666666666",
  "delegated_by": "human:alice",
  "autonomy_level": "review_required"
}
```

## 16.5 Tool actor

```json
{
  "actor_id": "tool:pytest",
  "actor_type": "tool",
  "tool_name": "pytest",
  "tool_version": "8.0.0",
  "environment_id": "env_001"
}
```

Anonymous committed actions are invalid.

---

# 17. Authorization Model

Sol artifacts SHOULD include an authorization policy for actor actions.

Validators MUST flag commits that violate the declared authorization policy.

## 17.1 Capabilities

At minimum, an implementation SHOULD distinguish:

```text
read
write_cell
write_record
execute
commit
create_branch
apply_proposal
review
approve
render
sign
redact
export
```

## 17.2 Autonomy levels

Agent autonomy levels are defined as:

```text
read_only
propose_only
review_required
autonomous_commit
```

Recommended default mappings:

```text
read_only:
  read

propose_only:
  read, create_branch, write_cell, write_record

review_required:
  read, create_branch, write_cell, write_record, execute, review, commit

autonomous_commit:
  read, create_branch, write_cell, write_record, execute, commit, apply_proposal
```

Write capabilities without `commit` manifest through proposal changesets.

The `review_required` level permits commits to branches where the authorization policy allows them. Protected branch rules still apply.

## 17.3 Imported or unknown actors

Unknown or imported actors SHOULD default to `propose_only` or stricter capabilities.

## 17.4 Protected branches

Artifacts MAY define protected branches.

Example:

```json
{
  "branch": "main",
  "protected": true,
  "required_capabilities": ["approve"],
  "allowed_committers": ["human:alice"]
}
```

An actor with `commit` capability MAY still be barred from committing to a protected branch.

## 17.5 Self-review rule

An actor MUST NOT be the sole accepting reviewer of a proposal it created unless the authorization policy explicitly permits self-application.

The `autonomous_commit` autonomy level MAY permit self-application if the policy declares it.

## 17.6 Authorization diagnostics

Unauthorized actions MUST produce an `unauthorized_action` diagnostic and MUST NOT be accepted as valid commits by a conforming Validator.

---

# 18. Cell Schema

A Sol cell MUST have a stable ID, type, summary, and source hash.

The `produces` array is an output contract, not a concrete run binding. It declares named outputs that a run may bind to concrete objects.

Example:

```json
{
  "cell_id": "cell_014",
  "cell_type": "sol:cell/code",
  "title": "Compute Evaluation Metrics",
  "summary": "Computes loss, accuracy, and EOS rate for each checkpoint.",
  "language": "python",
  "source": "metrics = compute_metrics(results)",
  "source_hash": "digest:sha256:7777777777777777777777777777777777777777777777777777777777777777",
  "contract_hash": "digest:sha256:9999999999999999999999999999999999999999999999999999999999999999",
  "depends_on": ["cell:cell_010", "cell:cell_011"],
  "produces": [
    {
      "name": "metrics_table",
      "mime_type": "application/x-parquet",
      "schema_ref": "object:sha256:8888888888888888888888888888888888888888888888888888888888888888"
    }
  ],
  "actor_id": "human:alice",
  "metadata": {}
}
```

Executors MUST NOT update the authored cell when binding a named output to a concrete object.

Concrete output bindings live in run records and output indexes.

Changing the authored output contract is a source change and participates in staleness.

Authored output contract changes are detected by commit diff over the `produces` array. Implementations MAY also store `contract_hash` to accelerate this check.

A cached `object_ref` inside a cell’s `produces` entry MAY exist as derived metadata, but it is non-authoritative, excluded from `source_hash`, excluded from `contract_hash`, and must be validated against the current run binding.

---

# 19. Cell Types

Core cell types include:

```text
sol:cell/prose
sol:cell/code
sol:cell/data
sol:cell/config
sol:cell/anchor
sol:cell/display
sol:cell/render
sol:cell/gate
sol:cell/branch
sol:cell/merge
```

Semantic types such as tasks, claims, evidence, decisions, proposals, reviews, failures, and verifications are records, not canonical cell types.

If a narrative document needs to display such a record, it uses an anchor cell.

If a narrative document needs to display an output object, it uses a display cell.

## 19.1 Data cells

A `sol:cell/data` cell declares inline data, structured data, or bindings to internal objects.

A data cell does not execute by default unless the runtime explicitly treats it as executable.

## 19.2 Display cells

A `sol:cell/display` cell places an output or object into narrative flow.

It MUST reference an object or named output.

```json
{
  "cell_id": "cell_display_metrics",
  "cell_type": "sol:cell/display",
  "display_ref": "cell:cell_014#metrics_table",
  "render_hint": {
    "style": "table"
  }
}
```

## 19.3 Gate cells

A `sol:cell/gate` cell represents a routing point in the execution structure.

A gate cell MUST reference a decision record.

```json
{
  "cell_id": "gate_003",
  "cell_type": "sol:cell/gate",
  "decision_ref": "record:decision_003"
}
```

## 19.4 Config cells

A `sol:cell/config` cell declares configuration used by later cells.

Changes to config cells participate in staleness and invalidation.

## 19.5 Render cells

A `sol:cell/render` cell declares a render target or render placement.

Rendered outputs remain derived products and must identify their source commit.

## 19.6 Branch and merge cells

`sol:cell/branch` and `sol:cell/merge` are reserved structural cell types for explicit graph execution or future branch-aware authoring. In v0.1 linear-only implementations may reject them unless graph execution is supported.

---

# 20. Status Model

Semantic records use a normalized status model.

Some status dimensions may be vacuous for some record types. Validators MUST NOT require verification of record types for which no verification method is registered.

## 20.1 Common status fields

```text
staleness:
  current | stale | unknown

verification:
  unverified | verified | failed_verification | needs_reverification
```

## 20.2 Lifecycle fields

The `lifecycle` vocabulary is record-type-specific.

Default lifecycle vocabulary:

```text
draft | active | superseded | withdrawn
```

Proposal lifecycle vocabulary:

```text
pending_review | accepted | rejected | amended | superseded | applied
```

## 20.3 Verification dependency

A record with:

```text
verification: verified
```

MUST be supported by at least one verification record with result `passed` whose dependencies are current.

A record MUST NOT become verified solely by setting a status field.

## 20.4 Staleness effect on verification

If a dependency transitions from `current` to `stale`, dependent records MUST transition to:

```text
staleness: stale
verification: needs_reverification
```

unless a record-type-specific rule specifies otherwise, including the aggregate evidence rule in §37.2 and the historical-context rule in §37.4.

## 20.5 Legal status transitions

Implementations MUST validate legal status transitions.

Recommended transition constraints:

| From                 | To                   | Required authority                                                 |
| -------------------- | -------------------- | ------------------------------------------------------------------ |
| draft                | active               | creating actor or approve capability                               |
| active               | superseded           | creating actor, approve capability, or applying superseding record |
| active               | withdrawn            | creating actor or approve capability                               |
| active/current       | active/stale         | validator or executor                                              |
| stale                | current              | successful rerun or passed verification                            |
| unverified           | verified             | passed verification record                                         |
| unverified           | failed_verification  | failed verification record                                         |
| verified             | needs_reverification | dependency staleness                                               |
| needs_reverification | verified             | passed verification record                                         |
| verified             | failed_verification  | failed verification record                                         |
| failed_verification  | verified             | new passed verification record                                     |
| failed_verification  | needs_reverification | dependency staleness or new verification requested                 |

Unknown status values MUST fail validation.

---

# 21. Base Semantic Record Schema

All semantic records share a base structure.

```json
{
  "record_id": "claim_007",
  "record_type": "sol:record/claim",
  "summary": "M200 has lower EOS hazard than M0 on open-ended prompts.",
  "created_by": "agent:eval_reviewer_001",
  "created_at": "2026-01-01T00:00:00Z",
  "depends_on": [
    "cell:cell_014#metrics_table",
    "cell:cell_014"
  ],
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  },
  "supersedes": [],
  "superseded_by": null,
  "anchors": ["cell:cell_claim_anchor_007"]
}
```

Records are canonical. Anchor cells are placements.

Commit ancestry, not timestamps, is the ordering authority for artifact history. Timestamps are evidence and convenience metadata.

---

# 22. Task Records

A task record describes the instruction, trigger, delegation, or work request that caused a run, proposal, or branch.

```json
{
  "record_id": "task_001",
  "record_type": "sol:record/task",
  "task_type": "human_instruction",
  "summary": "Compare checkpoints M0, M200, and M2000.",
  "instruction_ref": "object:sha256:9999999999999999999999999999999999999999999999999999999999999999",
  "created_by": "human:alice",
  "data_sensitivity": "internal",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

Task records MAY carry data-sensitivity labels because instructions frequently contain private context.

---

# 23. Claim Records

A claim is a structured assertion intended to be addressable by humans, tools, and agents.

```json
{
  "record_id": "claim_007",
  "record_type": "sol:record/claim",
  "statement": "Checkpoint M200 has lower EOS hazard than M0 on open-ended prompts.",
  "claim_type": "empirical_result",
  "supporting_evidence": ["record:evidence_011"],
  "confidence": 0.82,
  "confidence_basis": "computed from metric delta and bootstrap interval",
  "created_by": "agent:eval_reviewer_001",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

Claims intended to drive decisions MUST NOT exist only in prose.

---

# 24. Evidence Records

Evidence records link claims to sources, outputs, cells, runs, or external references.

## 24.1 Internal evidence

```json
{
  "record_id": "evidence_011",
  "record_type": "sol:record/evidence",
  "evidence_type": "metric_table",
  "source_ref": "cell:cell_014#metrics_table",
  "source_object": "object:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403",
  "supports": ["record:claim_007"],
  "derived_from": ["cell:cell_014", "run:run_008"],
  "created_by": "tool:eval_runner",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

## 24.2 External evidence

External citations and external datasets MAY be represented with `external_ref`.

```json
{
  "record_id": "evidence_012",
  "record_type": "sol:record/evidence",
  "evidence_type": "external_source",
  "external_ref": {
    "uri": "https://example.org/paper.pdf",
    "retrieved_at": "2026-01-01T00:00:00Z",
    "snapshot_object": "object:sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "availability": "archived"
  },
  "supports": ["record:claim_009"],
  "created_by": "human:alice",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

External evidence availability values:

```text
archived
live
unavailable
```

External citations are exempt from self-containment only if their availability is declared. If a snapshot exists, it SHOULD be stored in the internal object store.

---

# 25. Proposal and Review Records

A proposal is a structured suggested changeset.

```json
{
  "record_id": "proposal_003",
  "record_type": "sol:record/proposal",
  "base_commit": "commit:commit_041",
  "changes": [
    {
      "op": "modify_cell",
      "target": "cell:cell_014",
      "path": "/source",
      "value_ref": "object:sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    }
  ],
  "predicted_invalidations": [
    "cell:cell_015#eos_plot",
    "record:claim_007",
    "record:decision_002"
  ],
  "rationale": "Break EOS rate out by prompt category.",
  "created_by": "agent:eval_reviewer_001",
  "status": {
    "lifecycle": "pending_review",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

A review records a human, tool, or agent response.

```json
{
  "record_id": "review_004",
  "record_type": "sol:record/review",
  "proposal_id": "record:proposal_003",
  "reviewed_by": "human:alice",
  "review_status": "accepted",
  "comment": "Accepted. Rerun downstream plots after applying.",
  "created_at": "2026-01-01T00:00:00Z",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

When a proposal reaches `applied`, the resulting commit MUST reference the proposal and accepting review records.

---

# 26. Decision Records

A decision record captures a structured choice.

```json
{
  "record_id": "decision_002",
  "record_type": "sol:record/decision",
  "decision_type": "branch_selection",
  "candidates": ["branch:branch_a", "branch:branch_b"],
  "selected": "branch:branch_b",
  "decision_rule": "lowest_invalidated_outputs_then_human_review",
  "made_by": "human:alice",
  "based_on": ["record:claim_007", "record:evidence_011"],
  "created_at": "2026-01-01T00:00:00Z",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

Decision records MUST identify candidates, selected outcome, rule or rationale, actor, and supporting references.

---

# 27. Verification Records

A verification record describes a check applied to another artifact object.

## 27.1 Verification method vocabulary

Registered verification methods include:

```text
sol:verify/integrity
sol:verify/provenance_audit
sol:verify/reexecution
sol:verify/review
sol:verify/signature
```

## 27.2 Verification result vocabulary

Verification results include:

```text
passed
failed
inconclusive
not_reproducible
skipped
```

## 27.3 Concordance model

Re-execution verification MUST specify a concordance model.

Allowed concordance values:

```text
exact
tolerance
statistical
divergent
```

If the artifact manifest declares `deterministic: true`, `exact` SHOULD be the default expected concordance unless overridden by a cell-specific tolerance policy.

If the artifact manifest declares `deterministic: false`, `tolerance` or `statistical` concordance MAY be acceptable if declared.

Example:

```json
{
  "record_id": "verification_005",
  "record_type": "sol:record/verification",
  "target": "record:claim_007",
  "method": "sol:verify/reexecution",
  "performed_by": "tool:sol_executor",
  "result": "passed",
  "concordance": {
    "type": "tolerance",
    "metric": "eos_rate_delta",
    "tolerance": 0.001
  },
  "evidence": ["run:run_012", "object:sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"],
  "created_at": "2026-01-01T00:10:00Z",
  "status": {
    "lifecycle": "active",
    "staleness": "current",
    "verification": "unverified"
  }
}
```

A record SHOULD NOT be marked verified without a verification record or equivalent signed attestation.

## 27.4 Reproducibility status

Reproducibility status MUST be derived from verification records.

An artifact with no `sol:verify/reexecution` record has reproducibility status:

```text
unknown
```

Allowed reproducibility states:

```text
reproducible
partially_reproducible
not_reproducible
unknown
```

Profiles may refuse to accept or render `unknown` reproducibility status, but MUST NOT relabel untested work as `not_reproducible`.

---

# 28. Execution Structure

## 28.1 Linear execution

A linear Sol artifact has an ordered cell list.

```json
{
  "execution_structure": {
    "type": "linear",
    "cells": [
      "cell:cell_001",
      "cell:cell_002",
      "cell:cell_003"
    ]
  }
}
```

A committed run MUST execute cells in this order.

## 28.2 Explicit graph execution

A nonlinear Sol artifact MUST represent its graph.

```json
{
  "execution_structure": {
    "type": "explicit_graph",
    "nodes": [
      "cell:cell_001",
      "cell:cell_002a",
      "cell:cell_002b",
      "cell:gate_003",
      "cell:cell_004"
    ],
    "edges": [
      ["cell:cell_001", "cell:cell_002a"],
      ["cell:cell_001", "cell:cell_002b"],
      ["cell:cell_002a", "cell:gate_003"],
      ["cell:cell_002b", "cell:gate_003"],
      ["cell:gate_003", "cell:cell_004"]
    ]
  }
}
```

The graph is the execution structure.

---

# 29. Dependency Model

Sol defines three dependency layers.

## 29.1 Execution structure

Execution structure governs execution validity.

A run is valid only if it follows the visible execution structure.

## 29.2 Declared dependencies

A cell’s `depends_on` field is the authored dependency contract.

Declared dependencies MUST be consistent with the execution structure.

For a linear artifact, a cell MUST NOT declare a dependency on a later cell.

For a graph artifact, a cell MUST NOT declare a dependency on a node that is not reachable upstream.

Validators MUST reject declared dependencies that violate the execution structure.

## 29.3 Observed dependency hints

Dependency hints are runtime observations produced by kernels or tools.

They are evidence, not the execution contract.

Observed hints may widen invalidation. They MUST NOT narrow invalidation below what declared dependencies and execution structure require.

If a trusted kernel reports a read not covered by declared dependencies, the implementation MUST record an undeclared dependency diagnostic.

Strict validation profiles MAY fail on undeclared dependencies.

## 29.4 Precedence rule

The precedence order is:

```text
1. Execution structure governs valid execution.
2. Declared dependencies define the authored dependency contract.
3. Observed dependency hints provide evidence and may widen invalidation.
```

---

# 30. Run Records

A run record describes an execution attempt.

```json
{
  "run_id": "run_008",
  "source_commit": "commit:commit_041",
  "result_commit": "commit:commit_042",
  "actor_id": "tool:sol_executor",
  "task_ref": "record:task_001",
  "entry_point": "cell:cell_001",
  "status": "success",
  "cells_executed": [
    "cell:cell_001",
    "cell:cell_002",
    "cell:cell_003",
    "cell:cell_004",
    "cell:cell_005",
    "cell:cell_006",
    "cell:cell_007",
    "cell:cell_008",
    "cell:cell_009",
    "cell:cell_010",
    "cell:cell_011",
    "cell:cell_012",
    "cell:cell_013",
    "cell:cell_014"
  ],
  "environment_id": "env_001",
  "started_at": "2026-01-01T00:00:00Z",
  "completed_at": "2026-01-01T00:00:12Z",
  "output_bindings": [
    {
      "named_output": "cell:cell_014#metrics_table",
      "object_ref": "object:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403",
      "mime_type": "application/x-parquet"
    }
  ],
  "resource_usage": {
    "wall_time_ms": 12000,
    "cpu_time_ms": 8400,
    "peak_memory_bytes": 104857600
  }
}
```

Valid committed run statuses are:

```text
success
partial_success
failure
cancelled
```

The status `partial_uncommitted` is transient executor state and MUST NOT appear in artifact history.

---

# 31. Partial Results

A run that fails MAY commit a prefix result for a linear artifact or an ancestor-closed subgraph result for a graph artifact.

A prefix result contains the outputs of every cell that completed successfully before failure.

An ancestor-closed subgraph result contains the outputs of every completed cell whose upstream dependencies within the run also completed successfully.

A run with committed partial results has status:

```text
partial_success
```

Its committed completed-cell outputs are valid.

Cells at or beyond the failure point are marked unexecuted for that run.

Prior outputs for cells not executed in the partial run retain their existing staleness state.

The paired failure record MUST reference the same `run_id`.

Atomicity is preserved: the prefix result or ancestor-closed result commits atomically or not at all.

---

# 32. Failure Records

A failed execution MUST NOT partially commit invalid outputs as valid results.

A failure MAY be committed as a failure record.

```json
{
  "record_id": "failure_002",
  "record_type": "sol:record/failure",
  "run_id": "run:run_009",
  "source_commit": "commit:commit_042",
  "actor_id": "tool:sol_executor",
  "failed_cell": "cell:cell_014",
  "error_type": "ModuleNotFoundError",
  "message": "No module named 'example_package'",
  "trace_object": "object:sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "environment_id": "env_001",
  "created_at": "2026-01-01T00:02:00Z",
  "retryable": true
}
```

Failure records are useful for audit, debugging, agent handoff, and retry planning.

---

# 33. Consistency Model

Sol v0.1 uses:

```text
snapshot isolation for execution transactions
serializable commits per branch
```

A run reads from a stable committed artifact snapshot.

A run may commit only if its source commit remains valid and no conflicting branch-head update has invalidated its assumptions.

If a conflict exists, the runtime MUST reject the commit, create a branch, or require an explicit merge or rebase operation.

---

# 34. Atomic Execution Commits

A committed execution update MUST include, atomically:

* source commit reference,
* executed cells,
* run record,
* valid output bindings,
* object-store writes,
* provenance records,
* actor attribution,
* output-staleness updates,
* semantic-record-staleness updates,
* resulting commit.

If execution fails, a prefix result or ancestor-closed subgraph result MAY commit atomically as `partial_success`.

Invalid or incomplete outputs MUST NOT be committed as valid outputs.

---

# 35. Runtime Assumption Changes

A runtime assumption change is any change to fields under:

```text
runtime
environment
execution
security
assumptions
```

that may affect execution result, output validity, access rights, or reproducibility.

Such changes MUST participate in staleness and invalidation logic.

---

# 36. Output Staleness and Invalidation

Sol v0.1 uses conservative downstream invalidation.

If a cell changes in any of the following ways:

* source hash changes,
* authored output contract changes,
* runtime language changes,
* environment ID changes,
* declared input object hash changes,
* runtime assumption changes,
* upstream output object hash changes,
* security policy changes that affect execution,
* actor or tool configuration digest changes for executable agent/tool cells,

then every reachable downstream output MUST be marked invalidated.

For a linear artifact, all later cells are reachable unless trusted dependency analysis proves otherwise.

For an explicit graph, all graph descendants are reachable unless trusted dependency analysis proves otherwise.

Example:

```json
{
  "named_output": "cell:cell_014#metrics_table",
  "status": "invalidated",
  "invalidated_by": "cell:cell_014",
  "reason": "upstream_source_changed"
}
```

---

# 37. Semantic Record Staleness

Sol MUST propagate staleness beyond outputs.

Semantic records may depend on:

* cells,
* named outputs,
* objects,
* runs,
* other records,
* environment manifests,
* actor configurations,
* external references.

## 37.1 Computational dependency rule

If a computational dependency of a semantic record is invalidated, superseded, removed, or becomes unverifiable, the dependent record MUST be marked stale or requiring reverification.

Example:

```json
{
  "record_id": "claim_007",
  "status": {
    "lifecycle": "active",
    "staleness": "stale",
    "verification": "needs_reverification"
  },
  "stale_reason": {
    "dependency": "cell:cell_014#metrics_table",
    "reason": "supporting_computation_invalidated"
  }
}
```

## 37.2 Aggregate evidence rule

A claim’s staleness is a function of its supporting-evidence set.

If all supporting evidence is stale, unavailable, invalidated, or unverifiable, the claim MUST be marked:

```text
staleness: stale
verification: needs_reverification
```

If some supporting evidence is stale, unavailable, invalidated, or unverifiable, but at least one current evidence record still supports the claim, the claim MAY remain:

```text
staleness: current
```

but MUST transition to:

```text
verification: needs_reverification
```

and MUST produce a `degraded_support` diagnostic.

If all supporting evidence is current, the claim’s staleness is unchanged.

## 37.3 Decision propagation

Decision records based on stale claims or evidence MUST be marked stale.

## 37.4 Historical context records

Historical records such as reviews and failures are not deleted when stale context changes. Instead, their context may be marked stale.

Recommended `context_status` values:

```text
current_context
reviewed_object_changed_after_review
dependency_withdrawn
unknown_context
```

Example:

```json
{
  "record_id": "review_004",
  "context_status": "reviewed_object_changed_after_review"
}
```

---

# 38. Dependency Hints

Kernels and tools MAY emit dependency hints.

```json
{
  "cell_id": "cell_014",
  "run_id": "run_008",
  "reads": [
    "object:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "symbol:df",
    "env:CUDA_VISIBLE_DEVICES"
  ],
  "writes": [
    "symbol:metrics",
    "cell:cell_014#metrics_table"
  ]
}
```

If dependency hints are missing, incomplete, or untrusted, Sol MUST fall back to conservative downstream invalidation.

---

# 39. Diagnostics

Validators SHOULD emit diagnostics for artifact issues.

Diagnostic categories include:

```text
stale_output
stale_record
degraded_support
missing_object
undeclared_dependency
invalid_actor
unauthorized_action
unverified_claim
broken_provenance
unsafe_render
signature_failure
illegal_status_transition
dishonest_render
invalid_reference
invalid_proposal_application
invalid_partial_success
```

Example:

```json
{
  "diagnostic_id": "diag_023",
  "rule_id": "V3-08",
  "target": "record:claim_007",
  "severity": "warning",
  "category": "stale_record",
  "message": "Claim depends on invalidated evidence object."
}
```

Diagnostics are not records by default, but implementations MAY persist them as verification or audit records.

---

# 40. Internal Versioning

Sol artifacts contain internal version history.

A commit records a change to the artifact.

```json
{
  "commit_id": "commit_042",
  "parents": ["commit:commit_041"],
  "branch": "main",
  "author": "human:alice",
  "message": "Apply proposal_003 and rerun affected cells.",
  "applied_proposals": [
    {
      "proposal": "record:proposal_003",
      "accepted_by": ["record:review_004"]
    }
  ],
  "changes": [
    {
      "op": "apply_proposal",
      "proposal": "record:proposal_003"
    },
    {
      "op": "modify_cell",
      "cell_id": "cell:cell_014"
    },
    {
      "op": "bind_output",
      "named_output": "cell:cell_014#metrics_table",
      "object_id": "object:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403"
    },
    {
      "op": "update_record_status",
      "record_id": "record:claim_007"
    }
  ],
  "created_at": "2026-01-01T00:00:00Z"
}
```

The commit `author` MUST resolve to an actor record.

External version control may archive Sol artifacts, but internal history remains canonical for Sol semantics.

Commit ancestry, not timestamp order, is authoritative.

## 40.1 Proposal application validation

`apply_proposal` is a marker operation.

The constituent operations enumerate actual changes.

A Validator MUST check that the constituent operations match the proposal’s changeset against its `base_commit`.

A proposal application commit MUST reference:

* the applied proposal,
* the accepting review record or records,
* and the resulting changes.

---

# 41. Branches and Merges

Branches support alternative execution paths, assumptions, datasets, runtime configurations, or conclusions.

```json
{
  "branch_id": "branch_007",
  "name": "strict_metric_threshold",
  "base_commit": "commit:commit_042",
  "created_by": "human:alice",
  "purpose": "Test whether stricter pass criteria change the selected checkpoint."
}
```

Merge records SHOULD preserve both branches’ provenance and identify conflicts explicitly.

Conflict categories include:

* source conflict,
* order conflict,
* graph conflict,
* output conflict,
* environment conflict,
* assumption conflict,
* decision conflict,
* record conflict,
* actor attribution conflict.

---

# 42. Internal Object Store

Required outputs and large artifacts are stored inside the artifact.

Objects are content-addressed and immutable.

```json
{
  "object_id": "object:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403",
  "mime_type": "image/png",
  "compression": "zstd",
  "size_bytes": 1842032,
  "created_by": "cell:cell_014",
  "created_by_run": "run:run_008",
  "data_sensitivity": "internal"
}
```

The object ID MUST resolve inside the artifact.

The object store SHOULD support:

```text
put
get
get_range
stat
exists
verify
list
pin
garbage_collect
```

Objects MUST NOT be modified in place.

## 42.1 Garbage collection

Garbage collection MUST preserve objects reachable from:

* retained commits,
* branch heads,
* rendered views,
* provenance records,
* evidence records,
* failure records,
* verification records,
* signatures,
* pinned history,
* and protected audit snapshots.

---

# 43. Compression and Deduplication

Object storage SHOULD use lossless compression where useful.

Registered compression identifiers include:

```text
sol:compression/zstd
sol:compression/gzip
sol:compression/brotli
sol:compression/none
```

Objects with identical content SHOULD be stored once and referenced multiple times.

---

# 44. Provenance

Every committed output SHOULD include provenance sufficient to answer:

* Which cell produced this?
* Which run produced this?
* Which actor initiated the run?
* Which inputs were used?
* Which environment was used?
* Which commit contains this?
* Which downstream cells depend on this?
* Which semantic records depend on this?
* Which rendered views include this?
* Is this output stale relative to the current branch?

Example:

```json
{
  "cell_id": "cell:cell_014",
  "run_id": "run:run_008",
  "commit_id": "commit:commit_042",
  "actor_id": "tool:sol_executor",
  "input_hashes": ["object:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
  "output_hashes": ["object:sha256:1f4c9a2b7e6d5c4b3a291817161514131211100f0e0d0c0b0a09080706050403"],
  "environment_id": "env_003",
  "kernel": "python",
  "random_seed": 1234,
  "started_at": "2026-01-01T00:00:00Z",
  "completed_at": "2026-01-01T00:00:12Z"
}
```

Sol SHOULD align with existing provenance models where practical.

---

# 45. Supply-Chain Metadata

A Sol artifact MAY include:

* SBOM records,
* environment attestations,
* signed commits,
* signed rendered views,
* digest-pinned container references,
* package lockfile hashes,
* tool configuration digests,
* agent configuration digests.

Reproducibility status MUST be derived from verification records, not asserted independently.

---

# 46. Signatures and Integrity

Sol v0.1 requires SHA-256 support for content addressing.

Recommended baseline signature suite:

```text
hash: SHA-256
signature: Ed25519
canonicalization: RFC 8785 JSON Canonicalization Scheme for JSON records
```

A signature record SHOULD identify:

* signed object,
* canonicalization method,
* signature algorithm,
* public key reference,
* signature object,
* timestamp.

---

# 47. Rendering

Rendered views are derived products.

Supported views MAY include:

* HTML,
* Markdown,
* PDF,
* slides,
* dashboard,
* audit view,
* machine summary.

Renderer conformance REQUIRES:

```text
sol:render/machine_summary
```

A rendered view MUST identify its source commit.

```json
{
  "render_id": "render_012",
  "source_commit": "commit:commit_042",
  "target": "html",
  "created_at": "2026-01-01T00:00:00Z",
  "output_object": "object:sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
}
```

Rendering MUST NOT execute code by default.

HTML renderers SHOULD default to script-disabled output unless trusted interactivity is explicitly enabled.

Rendered views that include stale records, invalidated outputs, unverified claims, or stale decisions MUST disclose that status.

A human-facing render that hides stale records, invalidated outputs, or unverified claims is invalid.

---

# 48. Machine Summary Render

`sol:render/machine_summary` is a required Renderer target.

It is a standalone JSON serialization of read Levels 0–2:

* manifest summary,
* execution skeleton,
* cell summaries,
* actor index,
* record index,
* status and staleness summary,
* open proposals,
* run and failure summaries,
* diagnostics,
* render list,
* and source commit.

The machine summary is intended for:

* agent handoff,
* CI review,
* bounded-context evaluation,
* detached audit,
* and lightweight indexing.

A machine summary is not the full artifact and cannot replace the artifact, but it must be sufficient to answer:

* what was done,
* what is claimed,
* what supports it,
* what is stale,
* what failed,
* and what awaits review.

Summary–artifact divergence is invalid.

---

# 49. Security

Sol artifacts may contain executable code, private data, credentials, model artifacts, or sensitive outputs.

Implementations SHOULD support sandbox profiles.

| Profile                | Execution | Network            | GPU      | Secrets        | Default |
| ---------------------- | --------- | ------------------ | -------- | -------------- | ------- |
| `sandbox_minimal`      | None      | Blocked            | No       | Redacted       | Yes     |
| `sandbox_trusted`      | Allowed   | Blocked by default | Optional | Vault-injected | No      |
| `sandbox_unrestricted` | Allowed   | Allowed            | Optional | As-is          | No      |

Opening an artifact MUST NOT imply executing it.

Rendering an artifact MUST NOT imply executing it.

Imported artifacts SHOULD default to untrusted mode.

---

# 50. Data Governance

Cells, records, and objects MAY declare data sensitivity:

```text
public
internal
restricted
pii
```

Export policies MAY produce:

* full artifact export,
* public redacted export,
* audit export,
* render-only export,
* metadata-only export.

A redacted export MUST explicitly record removed or replaced objects and records.

---

# 51. Extension Registry

Core identifiers use the `sol:` namespace.

Examples:

```text
sol:cell/code
sol:cell/prose
sol:cell/anchor
sol:cell/display
sol:cell/gate
sol:record/task
sol:record/claim
sol:record/evidence
sol:record/decision
sol:record/proposal
sol:record/review
sol:record/failure
sol:record/verification
sol:render/html
sol:render/machine_summary
sol:compression/zstd
sol:sandbox/minimal
```

Third-party extensions SHOULD use URI or reverse-domain identifiers.

Unknown required extensions MUST cause validation failure unless supported.

Unknown optional extensions MAY be preserved and ignored.

---

# 52. External Version Control

Sol artifacts may be stored in Git or other external version-control systems.

A bridge may map:

```text
Sol commit        ↔ external commit
Sol branch        ↔ external ref
Sol semantic diff ↔ review artifact
```

External version control is not canonical for Sol semantics.

Recommended behavior:

1. Store the `.solnb` artifact as canonical.
2. Optionally export a plain-text review mirror.
3. Preserve Sol commit identifiers in external metadata.
4. Treat external diffs as convenience views.

---

# 53. Compatibility and Migration

Sol MAY import existing notebook formats.

When importing `.ipynb`, an importer SHOULD:

* preserve visible cell order,
* import outputs into the internal object store,
* preserve available metadata,
* mark provenance incomplete where unavailable,
* classify outputs as historical or potentially stale unless validated,
* create an initial import commit.

Export to `.ipynb` MAY be supported but SHOULD be considered lossy if internal history, object-store semantics, actor attribution, provenance, branches, proposals, claims, evidence, semantic records, or execution graphs cannot be represented.

---

# 54. Work Server Protocol Compatibility

A future Work Server Protocol may expose Sol artifacts over a structured service interface.

Possible operations:

```text
sol/open
sol/validate
sol/run
sol/commit
sol/branch
sol/diff
sol/render
sol/reportStaleness
sol/proposeChange
sol/requestReview
sol/listClaims
sol/listEvidence
sol/getActor
sol/getFailure
sol/getDiagnostics
```

This protocol is out of scope for this RFC, but the artifact model includes the records needed by such a protocol.

---

# 55. State Checkpoints

State checkpointing is not part of the v0.1 core.

A future RFC may define checkpoint objects for accelerated reruns, long-running computations, and agent workflows.

Open issues include:

* whether checkpoints are reproducible artifact state,
* whether checkpoints are trusted outputs,
* how checkpoint invalidation works,
* how checkpoint objects are signed,
* and whether checkpoints can be used across runtimes.

---

# 56. Exploded Debug Representation

This section is non-normative.

Implementations MAY support an exploded debug representation for development, validation, and corpus construction.

Example:

```text
artifact.sol.d/
  manifest.yaml
  execution_structure.json
  cells/
    cell_001.json
    cell_014.json
  records/
    claim_007.json
    evidence_011.json
    proposal_003.json
    review_004.json
  actors/
    human_alice.json
    agent_eval_reviewer_001.json
  runs/
    run_008.json
  commits/
    commit_041.json
    commit_042.json
  objects/
    sha256/
      1f/4c/1f4c9a...
  renders/
    machine_summary.json
    report.html
  diagnostics/
    expected.json
```

The exploded form is not the normative interchange container. It exists to let early validators, schemas, and pathology corpus artifacts be built before the physical `.solnb` container is finalized.

---

# 57. MVP Scope

A v0.1 MVP SHOULD include:

1. `.solnb` artifact container or exploded debug representation.
2. Required manifest.
3. `artifact_id`.
4. `required_features`.
5. Language declaration.
6. Linear execution structure.
7. No hidden out-of-order committed execution.
8. Internal commit history with at least one branch.
9. Actor records.
10. Authorization policy.
11. Cell summaries.
12. Named output contracts.
13. Run-level output bindings.
14. Anchor cells.
15. Display cells.
16. Gate cells.
17. Run records.
18. Partial-success runs.
19. Failure records.
20. Task records.
21. Proposal records with `base_commit`.
22. Proposal application linkage.
23. Review records.
24. Claim records.
25. Evidence records, including external evidence.
26. Decision records.
27. Verification records.
28. Normalized status model.
29. Internal content-addressed object store.
30. Lossless object compression.
31. Output hash verification.
32. Conservative output-staleness detection.
33. Conservative semantic-record-staleness detection.
34. Provenance records for committed runs.
35. Machine summary rendering.
36. HTML and Markdown rendering from selected commits.
37. Safe rendering without code execution.
38. Import from `.ipynb` with provenance warnings.
39. Validator conformance tests.

The MVP MAY defer:

* explicit graph execution,
* branch merges,
* multi-language execution,
* realtime collaboration,
* semantic diffs,
* Work Server Protocol,
* complex decision blocks,
* full supply-chain signatures beyond object hashing,
* state checkpoints.

---

# 58. Acceptance Criteria

A Sol MVP is acceptable if it can demonstrate:

1. A user cannot commit results from hidden out-of-order execution.
2. A machine reader can inspect manifest, skeleton, summaries, actors, semantic records, decisions, and staleness without loading outputs.
3. Claims, evidence, decisions, proposals, reviews, verifications, and failures are records, not merely prose.
4. Anchor cells can place semantic records into a narrative without duplicating canonical content.
5. A Sol artifact can be moved without losing required outputs.
6. Prior commits can be inspected without external version control.
7. Stored outputs can be verified by hash.
8. Upstream modification invalidates downstream outputs.
9. Upstream modification marks dependent semantic records stale or requiring reverification.
10. Rendered HTML or Markdown identifies the source commit.
11. Committed outputs record cell, run, commit, environment, and actor provenance.
12. Failed executions produce failure records without committing invalid partial outputs.
13. Partial-success runs commit only prefix or ancestor-closed valid outputs; the paired failure record references the same run.
14. Rendering can occur without code execution.
15. Imported notebooks clearly identify incomplete provenance.
16. A commit resulting from proposal application resolves to its proposal and review records.
17. No committed record carries a status value outside the registered vocabularies.
18. Illegal status transitions are rejected.
19. Reproducibility status changes only via verification records.
20. A human-facing render of an artifact containing stale records visibly discloses them.
21. The machine summary alone suffices for an evaluator to answer: what was done, what is claimed, what supports it, what is stale, what failed, and what awaits review.
22. A commit applying a proposal cannot be accepted when the constituent operations diverge from the proposal changeset.
23. An actor cannot be the sole accepting reviewer of its own proposal unless the policy explicitly permits self-application.
24. `object:` references resolve to internal objects; `digest:` references are well-formed but do not imply object-store resolution.
25. Cell output contracts are distinct from run-level output bindings.

---

# 59. Open Questions

## v0.1 blocking

1. What physical container should be used for the reference implementation?
2. What minimum environment manifest is required?
3. Which compression codecs are mandatory?
4. How much branch support is required in v0.1?
5. What is the minimum object-size support requirement?
6. How should imported `.ipynb` outputs be classified?
7. How strict should the cell-summary requirement be?
8. Which actor fields are mandatory for agent-authored commits?
9. What is the minimal claim/evidence schema?
10. Which semantic-record status fields are mandatory?
11. What exact machine summary schema is required?

## post-v0.1

1. Should graph execution be part of the core spec?
2. Should semantic diffs be standardized?
3. Should CRDT-based collaborative editing be supported?
4. Should Work Server Protocol be a separate RFC?
5. Should Sol support OCI artifact distribution directly?
6. Should dependency hints be required from kernel adapters?
7. How should private or unavailable external data be represented?
8. How should Sol interoperate with RO-Crate, W3C PROV, SPDX, SLSA, in-toto, MCP, A2A, and LangGraph-style checkpointing?
9. Should rendered interactive HTML be allowed inside signed artifacts?
10. Should agent-created claims require verification state before rendering?
11. Should state checkpointing be standardized?
12. Should `context_status` values be formalized as a registry?

---

# 60. Appendix A: Validation Rule Catalog

Validation rules are assigned stable IDs so diagnostics can remain diffable across validator versions.

## V0 — Container and Schema

```text
V0-01  Manifest present, parses, sol_version recognized.
V0-02  artifact_id present and well-formed.
V0-03  required_features all supported.
V0-04  All committed status values in registered vocabularies.
V0-05  All references parse under §9 grammar.
V0-06  Every object: ref resolves in store; digest: refs are well-formed.
```

## V1 — Referential Integrity

```text
V1-01  Commit ancestry acyclic; branch heads resolve.
V1-02  Commit author resolves to actor record; no anonymous actions.
V1-03  Anchor cells reference exactly one existing record; no content duplication.
V1-04  Gate cells reference existing decision records.
V1-05  Named-output refs resolve through a valid run binding.
V1-06  GC reachability: no object referenced by provenance, evidence, failure,
       verification, render, or signature records is absent.
V1-07  Object hashes verify.
```

## V2 — Structural Semantics

```text
V2-01  Committed runs follow execution structure.
V2-02  Declared depends_on is consistent with execution structure.
V2-03  partial_success runs are prefix / ancestor-closed; failure record shares run_id.
V2-04  partial_uncommitted does not appear in history.
V2-05  Staleness propagation reaches all reachable outputs and dependent records
       within the same commit.
V2-06  Undeclared-dependency diagnostics present where trusted hints report
       uncovered reads.
```

## V3 — Semantic-Record Integrity

```text
V3-01  verification:verified backed by a passed verification record with
       current dependencies.
V3-02  Status transitions legal per §20.5, including authority.
V3-03  Reproducibility status derived from verification records only.
V3-04  Reexecution verifications declare concordance consistent with manifest determinism.
V3-05  Applied proposals: commit references proposal + accepting review; constituent
       ops match proposal changeset against base_commit.
V3-06  Decision records complete: candidates, selected, rule, actor, based_on.
V3-07  Claims driving decisions exist as records, not only prose.
V3-08  External evidence availability declared; unavailable evidence propagates
       according to the aggregate evidence rule.
```

## V4 — Policy and Authorization

```text
V4-01  Commits conform to authorization policy; protected-branch rules enforced.
V4-02  No sole self-review application unless explicitly permitted.
V4-03  Capabilities sufficient for each recorded action type.
```

## V5 — Render Honesty

```text
V5-01  Every render identifies source commit.
V5-02  Renders containing stale, invalidated, or unverified content disclose it.
V5-03  Machine summary agrees with artifact state: every claim, status,
       staleness flag, open proposal, diagnostic, and failure in Levels 0–2 appears;
       nothing appears that is not in the artifact.
```

---

# 61. Appendix B: Pathology Corpus Manifest

Each corpus entry should contain:

```text
artifact.sol.d/
expected_diagnostics.json
README.md
```

Diagnostics should include:

```text
rule_id
category
severity
target
message
```

## Golden Artifacts

```text
GOLD-01  Minimal linear artifact, one run, one claim, verified, rendered.
GOLD-02  partial_success run with correct prefix commit and paired failure record.
GOLD-03  Full proposal lifecycle: propose → review → apply → rerun → reverify.
GOLD-04  Stale-then-recovered: upstream edit → propagation → rerun → statuses restored.
GOLD-05  External evidence with archived snapshot supporting a claim.
GOLD-06  Imported .ipynb with incomplete-provenance markings.
```

## Pathological Artifacts

```text
PATH-001  The hidden rerun
          Committed outputs from out-of-order execution.
          Expected: V2-01.

PATH-002  The silent read
          Trusted hint reports undeclared upstream read.
          Expected: V2-06.

PATH-003  The outlived conclusion
          Evidence invalidated; claim still current/verified.
          Expected: V2-05, V3-01.

PATH-004  The status forgery
          stale → current written directly, no rerun or verification.
          Expected: V3-02.

PATH-005  The orphan application
          Commit claims apply_proposal; proposal/review absent.
          Expected: V3-05.

PATH-006  The name-as-digest
          object: ref whose digest field is actually a name; unresolvable.
          Expected: V0-06.

PATH-007  The dishonest render
          HTML omits stale flags present in artifact.
          Expected: V5-02.

PATH-008  The anonymous hand
          Commit with no resolvable actor.
          Expected: V1-02.

PATH-009  The unauthorized merge
          propose_only agent commits to protected main.
          Expected: V4-01.

PATH-010  The self-approver
          Agent sole-accepts and applies its own proposal.
          Expected: V4-02.

PATH-011  The greedy partial
          partial_success commits outputs beyond failure point or not ancestor-closed.
          Expected: V2-03.

PATH-012  The detached sidecar
          Required output referenced by external path.
          Expected: INV-06 / V1-06.

PATH-013  The corrupted object
          Stored payload does not match its digest.
          Expected: V1-07.

PATH-014  The unearned badge
          verification:verified with no verification record.
          Expected: V3-01.

PATH-015  The asserted reproducer
          reproducibility:reproducible with zero reexecution records.
          Expected: V3-03.

PATH-016  The time traveler
          Linear cell depends_on a later cell.
          Expected: V2-02.

PATH-017  The ruleless gate
          Gate cell routes without decision record.
          Expected: V1-04.

PATH-018  The echoing anchor
          Anchor duplicates the record’s canonical content.
          Expected: V1-03.

PATH-019  The embellished summary
          Machine summary contains a claim not in records or omits a staleness flag.
          Expected: V5-03.

PATH-020  The vanished source
          External evidence availability unavailable; dependent claim unaffected.
          Expected: V3-08.

PATH-021  The swept evidence
          GC removed an object reachable from evidence.
          Expected: V1-06.

PATH-022  The divergent applier
          Commit ops do not match the applied proposal’s changeset.
          Expected: V3-05.

PATH-023  The drifted binding
          Named-output ref resolves to object from stale or invalid run.
          Expected: V1-05.

PATH-024  The unknown demand
          required_features includes unsupported feature; reader proceeds anyway.
          Expected: V0-03.

PATH-025  The mislabeled failure
          failed_verification record exists; target still verified.
          Expected: V3-02.
```

---

# 62. Appendix C: Validator Engineering Notes

A reference validator should produce deterministic diagnostics:

```text
same artifact → same diagnostic set → same ordering
```

Recommended exit classifications:

```text
valid
valid_with_warnings
invalid
unsupported
```

Recommended validator profiles:

```text
default:
  enforces specification MUSTs

strict:
  may fail on undeclared dependencies, unverified claims in renders,
  unknown reproducibility, and other policy-sensitive conditions
```

Profiles should be data-defined rather than hard-coded where practical.

The reference implementation should publish schemas for:

* manifest,
* cells,
* records,
* runs,
* commits,
* object records,
* actor records,
* machine summary,
* diagnostics.

The pathology corpus should be treated as executable specification support.

Propagation and summary honesty should use shared deterministic functions where possible:

```text
propagate(artifact_state, change) → closure
render_machine_summary(artifact_state, commit) → summary
```

Validators can then recompute propagation and machine summaries and compare canonicalized output.

---

# 63. Summary

Sol is a proposal for a self-contained, versioned computational work artifact.

Its main constraints are:

```text
Visible execution structure is valid execution structure.
The artifact is the source of truth.
Only serialized state is artifact state.
Machine legibility must not depend on rendered views.
Actors must be attributed.
Semantic records are canonical; cells may anchor them.
Outputs are internally stored and verifiable.
Named outputs are distinct from immutable object digests.
Output contracts are distinct from run bindings.
Committed outputs have provenance.
Semantic records have dependencies and staleness state.
Rendered views are derived products.
```

Sol’s purpose is not to replace existing notebook systems outright. Its purpose is to specify an artifact model for computational work that can survive handoff: from human to human, human to tool, tool to agent, agent to human, and agent to agent.

The motivating question is not only whether a notebook can run.

It is whether the next reader can understand, verify, continue, and render the work without reconstructing its structure from a terminal format.


# Final Freeze Review of RFC-SOL-0001 (v0.1.0-draft)

## Verification of Final Pass

All six items from the previous review landed, plus the process infrastructure:

| Item | Status |
|---|---|
| E-1: `review_required` includes `commit`; write-without-commit clarified; protected branches still govern | ✅ §17.2 |
| E-2: §20.4 exception explicitly references §37.2 and §37.4 | ✅ |
| E-3: §30 run example internally consistent (executes through cell_014, binds cell_014's output) | ✅ |
| Example hygiene: decision (§26), evidence (§24.1), and verification (§27.3) examples no longer show statuses they can't justify; verification records carry their own status block | ✅ |
| Vacuous-dimension rule for record types without registered verification methods | ✅ §20 intro |
| Blocking question 11 resolved via §37.4; `context_status` registry deferred to post-v0.1 #12 with recommended values published | ✅ |
| `contract_hash` with detection-by-commit-diff semantics | ✅ §18 |
| Change Control section with errata/unfreeze boundary and examples-must-validate gate | ✅ |
| Exploded debug representation (§56, non-normative); corpus retargeted to `artifact.sol.d/` | ✅ |
| Shared `propagate` / `render_machine_summary` function guidance | ✅ Appendix C |

I did a final scan against the freeze bar (invariants, requirements, vocabularies, transition table, grammar, conformance levels, validation rules). **Nothing remaining rises to that bar.** Two errata-class notes only, recorded here so they land in the errata log rather than blocking:

1. **Duplicate example digest.** §18's `contract_hash` and §22's `instruction_ref` share the digest `9999...` for different content. Harmless in fragments; will matter when GOLD-01 is assembled from spec examples per the Change Control gate. Fix during corpus construction.
2. **V0-04 scope vs. `context_status`.** V0-04 fails validation on status values outside registered vocabularies, but §37.4's `context_status` values are "recommended," not registered (pending post-v0.1 #12). One clarifying sentence — V0-04 applies to `lifecycle`/`staleness`/`verification`; `context_status` is open until the registry decision — prevents a validator implementer from over-enforcing. Errata-class because it clarifies rather than changes.

## Freeze Endorsement

**RFC-SOL-0001 v0.1.0-draft qualifies for freeze.** The invariants have been stable for three revisions, the semantic layer has survived adversarial review from multiple angles, every defect found across the review cycle exists as a named corpus entry with an expected diagnostic, and the change-control boundary is explicit. The document has also reached the state a freeze actually requires: the remaining open questions are ones that **implementation answers better than analysis** — the container question resolves by benchmarking against REQ-014.x, blocking questions 7–10 resolve when the JSON Schemas ship, and question 11 resolves when the machine summary schema is published as a normative artifact. None of them will be improved by another review round.

One discipline recommendation for the frozen period: when the validator and corpus start producing findings — and they will — triage every finding into exactly one of three buckets: **errata** (spec wording), **corpus entry** (new pathology, no spec change), or **unfreeze candidate** (accumulate these; batch them into v0.2 rather than unfreezing per-item). The temptation after freeze is to treat each implementation surprise as a spec emergency. Most aren't. The ones that are will be obvious because they'll break an invariant, and there should be very few of those or the freeze was premature — I don't believe it was.

## Closing Note on What This Document Became

It's worth stating plainly what six revisions produced, because it's more than an iteration on the original Medium argument.

The essay's claim was that agents should emit structured computational documents rather than rendered surfaces. That claim was correct but incomplete — it was an argument about *format*. What this RFC actually specifies is an argument about *trust*: a system in which every assertion is load-bearing only while its evidence stands, every actor is accountable through a delegation chain, every status is earned through a recorded act rather than written into a field, and every rendering is honest or invalid. The format is just the carrier for those guarantees.

That's also the correct framing for whatever you publish next. The five-revision arc itself demonstrates the thesis: the spec improved because each round's critique was converted into *addressable, testable structure* — rule IDs, corpus entries, transition tables — rather than prose commentary. The document was developed the way it proposes work should be done. PATH-003 remains the demo to lead with; the process is the proof to stand behind it.

Frozen. Build the validator, and let the corpus have the next word.