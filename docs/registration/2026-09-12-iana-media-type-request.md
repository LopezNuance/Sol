# IANA Media-Type Registration Request (draft): `application/vnd.sol.notebook`

Date: 2026-09-12 (UTC)
Status: **draft** — to be submitted with or just after public release, per
`docs/decisions/2026-09-07-phase0-venue.md` (the RFC must be citable at
submission time)
Basis: RFC 6838 (guidelines for media type registration); vendor-specific
type per the `application/vnd.` namespace
Namespace check: `application/vnd.sol.notebook` verified available against
the current IANA `application` registry on 2026-09-12 (zero `vnd.sol.*`
entries; see `docs/reviews/2026-09-12-stage2-namespace-review.md`)

## Registration fields

**Media Type name:** `application/vnd.sol.notebook`

**Required parameters:** none

**Optional parameters:** none

**Intended usage:** common

Sol is a self-contained, versioned computational work artifact for humans,
software tools, and autonomous or semi-autonomous agents. A Sol artifact
stores source cells, execution structure, runtime declarations, outputs,
provenance, internal history, actors, semantic records, failure records,
verification records, and rendered views. Rendered views (HTML, Markdown,
PDF, slides, dashboards, machine summaries) are derived from committed
artifact state; the artifact is the source of truth. The media type
identifies the single-file container form of such an artifact.

**Fragment identifier considerations:** N/A. The container is an opaque
archive; there is no fragment syntax.

**Encoding considerations:** binary. A Sol container is a single-file ZIP
archive with STORED (uncompressed) entries; the entry layout is identical
to the exploded `artifact.sol.d/` debug representation (manifest at the
archive root, content-addressed objects under `objects/sha256/`). The
STORED-only requirement eliminates decompression amplification. Container
choice and rationale: `container_benchmark/report.json` (REQ-014.1..014.5
measured over the real GOLD-01 artifact and a 16 MiB synthetic variant;
tar disqualified at ~21x read amplification for bounded reads).

**Security considerations:**

- A Sol artifact contains source cells that may contain code. A conforming
  reader MUST NOT execute cell content; rendering is a derived view
  produced without code execution (RFC-SOL-0001 safe-rendering
  requirement).
- Implementers MUST apply standard ZIP security guidance: reject entry
  names with path traversal, and enforce size limits. The STORED-only
  entry requirement removes decompression-bomb amplification; the
  object-size floor (RFC-SOL-0001 section 43 / Q5 decision) bounds
  individual objects.
- Artifacts carry actor and authorization records. A reader MUST enforce
  the artifact's authorization model when exposing content (logical
  disclosure); content that is not authorized for the requesting actor
  MUST NOT be rendered or returned.
- Objects are content-addressed (sha256). A reader SHOULD verify object
  digests against the manifest and report mismatches as diagnostics
  rather than silently accepting corrupted content.

**Interoperability considerations:**

- The normative container layout, manifest, and object-store rules are
  defined in RFC-SOL-0001 v0.1.0, "Sol — A Cooperative Computational Work
  Artifact" (published specification below).
- A reference implementation of the container (read/write/validate) is
  available in the project repository (`sol_validator/solval/container.py`),
  together with a validating corpus (37 cases) and a safe renderer.
- The companion specification RFC-SOL-QRY-0001 v0.3.0 defines query
  semantics over Sol artifacts and is submitted alongside the base RFC.

**Published specification:** RFC-SOL-0001 v0.1.0, "Sol — A Cooperative
Computational Work Artifact". Public specification; URL to be filled in at
public release (the public repository is `github.com/LopezNuance/Sol`).

**Application/usage category:** registration (vendor-specific type,
RFC 6838 section 2.3)

**Container for:** N/A

**File extension:** `.solnb`

**Macintosh file type code/code:** N/A

**Person or email address to contact for further information regarding
the above:** Scott [surname], project owner — email to be filled in before
submission.

## Submission notes

- This is a draft. Per the venue decision, the registration is submitted
  with or just after public release, when the published specification is
  citable.
- Placeholders to fill before submission: (1) published-specification URL,
  (2) contact surname and email.
- The vendor string `sol` is a project identifier; registration does not
  assert trademark rights (see the trademark section of
  `docs/reviews/2026-09-12-stage2-namespace-review.md`).
