# Decisions: RFC-SOL-0001 §59 v0.1-blocking open questions

Date: 2026-09-07 (UTC)
Status: Decided — all 11 blocking questions resolved
Change-control classification per the freeze review triage discipline:
**errata** (spec wording), **corpus entry** (new pathology), **unfreeze
candidate** (batched into the first unfreeze, which per the Phase 0 venue
decision promotes v0.1.0-draft to v0.1.0).

Normative text for the unfreeze candidates lands with the Phase 2 schema
publication and the v0.1.0 promotion; this file records the decisions now so
implementation proceeds against them.

---

## Q1: What physical container should the reference implementation use?

**Decision.** The v0.1 reference container is a **single-file ZIP archive**
(`.solnb`) with **STORED (uncompressed) entries** whose internal layout is
identical to the exploded `artifact.sol.d/` representation. The exploded
directory remains the non-normative debug representation (RFC §56).

**Rationale (evidence).** `container_benchmark/report.json` (2026-09-07)
measured REQ-014.1..REQ-014.5 for three candidates over the real GOLD-01
artifact and a 16 MiB synthetic variant:

- `tar` is disqualified: every bounded read requires a full sequential scan
  (manifest read at 20.98x artifact size on the 12 KB artifact; 2.61x on the
  16 MiB artifact). Fails REQ-014.1/REQ-014.2 in practice.
- `zip-flat` satisfies all five requirements: central-directory lookup makes
  manifest/index reads and random object access bounded (manifest read at
  0.02% of a 16 MiB artifact; worst-case object read at 99.94%, i.e., the
  object itself plus a constant central-directory overhead).
- `exploded-dir` has marginally lower I/O but is not a self-contained
  movable unit: it is fragile under partial copy, symlinks, and filesystem
  quirks, which conflicts with INV-06 (internal storage of required
  artifacts) and acceptance criterion 5 (artifact can be moved without
  losing required outputs).

STORED entries: objects are already compressed per §43 (registered codecs),
so container-level compression is redundant; STORED keeps byte-exact
integrity verification and random access simple. Container-level compression
is a post-v0.1 candidate, not a v0.1 requirement.

**Classification.** Unfreeze candidate (new normative requirement: reference
container definition).

---

## Q2: What minimum environment manifest is required?

**Decision.** The manifest `environment` object MUST contain:

- `environment_id` — stable identifier (already present in corpus manifests).
- `package_manifest` — digest of the resolved package manifest (lockfile
  digest). Answers "which exact dependencies" for acceptance criterion 11.
- `kernel` and `kernel_version` — required for artifacts containing code
  cells (the language declaration, MVP item 5, names the kernel family;
  these fields pin the runtime version).

SHOULD contain:

- `sbom_ref` — object reference to an SBOM (supply-chain metadata, §45; full
  supply-chain signatures are deferred in the MVP, so this stays SHOULD).

Run records reference `environment_id` (§30). Per-run deviations (a run
executed under a different kernel version than the manifest declares) MUST be
recorded in the run record, not silently absorbed into the manifest.
`random_seed` remains in the manifest `execution` block when execution is
non-deterministic (already present in corpus manifests).

**Rationale.** Acceptance criterion 11 requires committed outputs to record
"cell, run, commit, environment, and actor provenance." The minimum set above
is exactly what makes the environment legible to a machine reader at Level 0
(RFC §11) without loading Level 4 payloads: identity, dependency pin, and
runtime pin.

**Classification.** Unfreeze candidate (adds required manifest fields).

---

## Q3: Which compression codecs are mandatory?

**Decision.** Of the four registered identifiers in §43:

- MUST support (read and write): `sol:compression/none`,
  `sol:compression/gzip`.
- SHOULD support: `sol:compression/zstd` (preferred codec for new objects
  where available).
- MAY support: `sol:compression/brotli`.

Writers MUST declare the codec per object via the `compression` field (§42);
readers MUST reject objects whose declared codec they do not support rather
than guessing.

**Rationale.** v0.1 conformance must be reachable with standard libraries
(gzip is universal); zstd is the quality target and SHOULD so that the
ecosystem migrates without a v0.1 conformance cliff. MVP item 30 (lossless
object compression) is satisfied by the MUST set.

**Classification.** Unfreeze candidate (conformance floor over the §43
registry).

---

## Q4: How much branch support is required in v0.1?

**Decision.** The v0.1 branch floor:

- Branch records per §41 (`branch_id`, `name`, `base_commit`, `created_by`,
  `purpose`) — required.
- Every artifact has at least one branch (MVP item 8); the main branch is
  protected per §17.4.
- Multiple concurrent branches — required (branches exist to carry
  alternative paths, assumptions, or configurations; a single-branch
  conformance floor would make the authorization and staleness rules
  untestable).
- Commits record their branch; branch heads are part of the Level 1
  execution skeleton (RFC §11).
- **Branch merges are deferred** (MVP MAY-defer list). Merge records and the
  §41 conflict categories remain normative vocabulary for a later version;
  v0.1 validators do not validate merge records.

**Rationale.** This pins the floor that the existing MVP text already implies
("internal commit history with at least one branch" + "branch merges" in the
MAY-defer list). No new normative content beyond the deferral is introduced.

**Classification.** Errata-class clarification (pins existing MVP text).

---

## Q5: What is the minimum object-size support requirement?

**Decision.** A conforming object store MUST support objects from 0 bytes to
at least **1 GiB (2^30 bytes)** inclusive, with `get_range` valid for any
range within a supported object. Objects above 1 GiB MAY be split into
multiple registered objects (post-v0.1 candidate); a conforming v0.1
implementation MAY reject objects above 1 GiB at `put` time with a
diagnostic.

**Rationale.** 1 GiB covers realistic single outputs (datasets, checkpoints,
rendered media) while keeping the container index practical. The benchmark
shows random access scales with entry count, not object size (16 MiB object
read at 99.94% amplification in a 16 MiB artifact — the object itself).
§42's operation list (put/get/get_range/stat/exists/verify/list/pin/
garbage_collect) is unchanged; this decision only bounds the domain.

**Classification.** Unfreeze candidate (new normative bound).

---

## Q6: How should imported `.ipynb` outputs be classified?

**Decision.** Imported `.ipynb` outputs are committed to the internal object
store and classified as follows:

- **Staleness: `unknown`** — the original execution is not a Sol run, so
  `current` is unjustified; nothing is known to have changed upstream, so
  `stale` is unjustified. This is the only value consistent with §20.1.
- **Verification: `unverified`** — no Sol verification record exists for
  imported work.
- **Provenance: incomplete, declared.** The importer MUST create the initial
  import commit (§53), attach import metadata (`imported_from: "ipynb"`,
  import commit), and MUST NOT fabricate run records for imported outputs.
  Evidence records referencing imported objects carry `derived_from: []` and
  the import metadata serves as the explicit incomplete-provenance marker.
- **Render honesty:** any human-facing render of imported outputs MUST
  disclose "imported, provenance incomplete" (V5 render-honesty rules;
  acceptance criterion 15).

**Rationale.** §53 already requires importers to "mark provenance incomplete
where unavailable" and "classify outputs as historical or potentially stale
unless validated." This decision fixes the exact status values and the
no-fabricated-runs rule so the classification is mechanically checkable.

**Classification.** Unfreeze candidate (normative classification rule).

---

## Q7: How strict should the cell-summary requirement be?

**Decision.** `summary` is REQUIRED on every cell (RFC §18 already makes it
MUST). The v0.1 strictness floor:

- Non-empty string, at most **500 characters** (keeps Level 2 bounded reads
  small; RFC §11).
- MUST NOT be code or a byte-identical copy of `source` for code cells
  (a summary that duplicates the source defeats the purpose of the bounded
  read model).
- Validators enforce presence, non-emptiness, and the length bound
  (V0-class checks). The non-duplication rule is a SHOULD-level diagnostic
  in v0.1, not a hard failure, to avoid false positives on legitimately
  short cells.

**Classification.** Unfreeze candidate (strictness floor encoded in the cell
schema, Phase 2).

---

## Q8: Which actor fields are mandatory for agent-authored commits?

**Decision.** For `actor_type: "agent"`, the mandatory fields are:

- `actor_id`, `actor_type` (base actor identity; anonymous committed actions
  are invalid, §16.5).
- `model_id` and `model_version` — which model, pinned.
- `delegated_by` — the delegation chain (INV-09: attributed agency; an agent
  commits on behalf of a principal).
- `autonomy_level` — the authorization posture at commit time (§17.2).

SHOULD (required in practice when the agent's output drives a decision):

- `configuration_digest`, `prompt_template_digest`, `tool_policy_digest` —
  reproducibility of agent behavior; digests of the exact configuration that
  produced the work.

**Rationale.** The mandatory set answers the four questions INV-09 requires
of any committed action: who, which model version, on whose behalf, with what
authority. The digests are SHOULD because they are only meaningful when the
configuration is stable and recorded, and the MVP defers full supply-chain
signatures.

**Classification.** Unfreeze candidate (mandatory field set encoded in the
actor schema, Phase 2).

---

## Q9: What is the minimal claim/evidence schema?

**Decision.** Minimal **claim** = base semantic record schema (RFC §21:
`record_id`, `record_type`, `summary`, `created_by`, `created_at`,
`depends_on`, `status`, `supersedes`, `superseded_by`, `anchors`) plus:

- `statement` — required, non-empty (the assertion itself; `summary` is the
  bounded-read projection of it).
- `claim_type` — required, from a registered vocabulary.
- `supporting_evidence` — required array. A claim with
  `lifecycle: active` MUST reference at least one evidence record; this is
  what makes "claims intended to drive decisions MUST NOT exist only in
  prose" (§23) mechanically checkable. Draft claims MAY have an empty array.
- `confidence`, `confidence_basis` — SHOULD.

Minimal **evidence** = base schema plus:

- `evidence_type` — required.
- Exactly one of `source_ref` (internal: cell/named-output/object reference)
  or `external_ref` (external: URI + `retrieved_at` + `availability` per
  §24.2; `snapshot_object` SHOULD when the snapshot is stored internally).
- `supports` — required array of claim references.
- `source_object`, `derived_from` — SHOULD.

**Classification.** Unfreeze candidate (minimal schemas encoded in the record
schemas, Phase 2).

---

## Q10: Which semantic-record status fields are mandatory?

**Decision.** All three status dimensions are MANDATORY on every semantic
record: `status.lifecycle`, `status.staleness`, `status.verification`. No
record type is exempt.

- `staleness` and `verification` use the §20.1 common vocabularies.
- `lifecycle` uses the record-type-specific vocabulary (§20.2: default
  `draft | active | superseded | withdrawn`; proposals use the proposal
  vocabulary).
- Vacuous dimensions (the §20 vacuous-dimension rule: record types with no
  registered verification method) are present with a default value
  (`verification: unverified`), never omitted.

**Rationale.** The staleness-propagation machinery (§20.4, §37) and the
V0-04 validation rule operate on all three dimensions; a missing dimension is
indistinguishable from an unknown value, and unknown status values MUST fail
validation (§20.5). This decision pins what the RFC already implies.

**Classification.** Errata-class clarification (no new normative content).

---

## Q11: What exact machine summary schema is required?

**Decision.** The machine summary schema is published as a normative artifact
in Phase 2 (upgraded from the current draft `machine_summary.schema.json`).
It MUST require:

- `render_id`, `target`, `source_commit`, `artifact_id`, `sol_version`
  (identity and source-commit pinning; acceptance criterion 10).
- `execution_structure` — the Level 1 skeleton.
- `cells` — cell summaries (Level 2).
- `actors` — actor index.
- `records` — record index with full status blocks.
- `runs` — run summaries.
- Plus the §48 components missing from the current draft schema:
  `failures` (failure summaries), `diagnostics` (diagnostic summaries),
  `open_proposals` (proposal states), `stale` (status/staleness summary),
  `renders` (render list).

SHOULD: `manifest` (manifest summary block).

The schema is sufficient exactly when the summary alone answers the six
questions of §48 / acceptance criterion 21: what was done, what is claimed,
what supports it, what is stale, what failed, what awaits review. The
validator's `render_machine_summary` function (Appendix C) is the reference
implementation of this contract, and summary-artifact divergence remains
invalid (V5).

**Classification.** Unfreeze candidate (normative schema publication, Phase 2).

---

## Summary

| Q | Decision (one line) | Classification |
|---|---|---|
| 1 | Single-file ZIP, STORED entries, layout = `artifact.sol.d/` | Unfreeze candidate |
| 2 | env: `environment_id` + `package_manifest` + `kernel`/`kernel_version` MUST; `sbom_ref` SHOULD | Unfreeze candidate |
| 3 | MUST: none, gzip; SHOULD: zstd; MAY: brotli | Unfreeze candidate |
| 4 | Branches + protected main required; merges deferred | Errata-class |
| 5 | Object store MUST support 0 B .. 1 GiB, `get_range` anywhere | Unfreeze candidate |
| 6 | Imported outputs: `staleness: unknown`, `verification: unverified`, no fabricated runs, render disclosure | Unfreeze candidate |
| 7 | Summary required, <= 500 chars, non-duplication SHOULD | Unfreeze candidate |
| 8 | Agent actors: model pin + `delegated_by` + `autonomy_level` MUST; digests SHOULD | Unfreeze candidate |
| 9 | Claim: +`statement`/`claim_type`/`supporting_evidence` (active => >= 1); Evidence: +`evidence_type` + one source + `supports` | Unfreeze candidate |
| 10 | All three status dimensions mandatory on all records; vacuous = default value, not omission | Errata-class |
| 11 | Machine summary schema: current draft + `failures`/`diagnostics`/`open_proposals`/`stale`/`renders` | Unfreeze candidate |

All nine unfreeze candidates batch into the v0.1.0 promotion (Phase 5); the
two errata-class items land with the Phase 3 errata pass. No question
requires a corpus entry.

## Execution update (2026-09-07, Phase 2)

The decisions were encoded in the published normative schemas
(`sol_validator/schemas/`, v0.2 set; `object.schema.json` added, completing
the nine Appendix C classes) and enforced by the reference validator.
Schema enforcement introduces seven new stable rule IDs — **V0-07 through
V0-13** (cell, actor, record, object-record, machine-summary, manifest-
environment, and run/commit conformance) — which join the Appendix A
catalog at the v0.1.0 promotion (unfreeze candidate, batched with the
decisions above). The corpus now has 37 cases (PATH-026..PATH-031 exercise
the new rules) and passes with exact diagnostic match under strict mode.
