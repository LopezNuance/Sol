# Namespace, Trademark, and Ecosystem Review: "Sol", `.solnb`, `application/vnd.sol.notebook`

Date: 2026-09-12 (UTC)
Status: complete with one open action (trademark search, project owner)
Subject: venue stage 2 checklist item 1, per
`docs/decisions/2026-09-07-phase0-venue.md`; closes the Project Name
section's "subject to namespace, trademark, and ecosystem review" clause
for the namespace and ecosystem dimensions (see E-004,
`docs/errata/RFC-SOL-0001-errata.md`)

## Scope

The Project Name section of RFC-SOL-0001 v0.1.0 (`Sol_RFC.md`) declares a
provisional project name ("Sol"), a proposed file extension (`.solnb`), and
a proposed media type (`application/vnd.sol.notebook`), all subject to
namespace, trademark, and ecosystem review. This review covers:

1. IANA media-type namespace for `application/vnd.sol.notebook`.
2. File-extension namespace for `.solnb` (and the `.sol` collision it
   avoids).
3. Ecosystem and name landscape for "Sol".
4. Trademark status and the required search procedure.

## 1. IANA media-type namespace

**Finding: `application/vnd.sol.notebook` is available.**

Evidence (fetched 2026-09-12, this session):

- Source: `https://www.iana.org/assignments/media-types/application.csv`
  (the current `application` top-level registry; 1800 lines).
- Zero entries match the vendor string `vnd.sol.*`.
- The only near-match in the registry is
  `application/vnd.solent.sdkm+xml` (vendor string `solent`, a different
  vendor and a different type).
- Note for future checks: the IANA media-type registry is split per
  top-level type (`application.csv`, `audio.csv`, ...); there is no single
  `media-types.csv` (that URL 404s).

Consequence: no namespace collision. The registration request is drafted
at `docs/registration/2026-09-12-iana-media-type-request.md`. Per the
venue decision, the registration lands with or just after public release
(the RFC must be citable at submission time).

## 2. File-extension namespace

**`.sol` — established collision, already avoided.**

`.sol` is the source-file extension of Solidity, the Ethereum smart
contract language (established; `docs.soliditylang.org` references `.sol`
source files, confirmed 2026-09-12). This is the reason the Sol container
extension is `.solnb` rather than `.sol`: a `.sol` container would be
indistinguishable from Solidity source in any tooling, editor, or
repository context. No action required; the choice is recorded here as the
rationale.

**`.solnb` — no known usage found (2026-09-12), limited confidence.**

No known usage of `.solnb` was found. Caveat: web search from this
environment was blocked (search-engine anomaly page), so this negative
result has limited confidence. **Required action (project owner, before
public release):** re-verify `.solnb` with a normal browser search
(extension registries, file-extension databases, package ecosystems).

## 3. Ecosystem and name landscape

- **Solana / SOL.** Solana is a public blockchain platform whose token is
  "SOL". Different domain (public blockchain / DeFi); no technical overlap
  with a computational work artifact format. The similarity is a
  search/branding consideration, not a namespace collision. Documented; no
  action.
- **Solidity.** Different domain (smart contract language). The `.sol`
  extension collision is already avoided by `.solnb` (section 2).
- **"Sol" as a generic term.** "Sol" is a common word (solar, solstice;
  Spanish "sol" = sun). The name is therefore weak as a standalone
  identifier; differentiation comes from the full project identity
  ("Sol — a cooperative computational work artifact"), the vendor-suffixed
  media type, and the `.solnb` extension. This also shapes the trademark
  analysis in section 4.
- **Public repository.** `github.com/LopezNuance/Sol` ("Repository for the
  Sol RFC and related code") is the project owner's own public repository
  for this work (owner-confirmed 2026-09-12). It is the public face of this
  local project and is currently out of date relative to the local tree.
  Per owner direction (2026-09-12), the repository is updated once the
  local work is complete. Not a name collision.

## 4. Trademark

**Status: open required action (project owner, before public release).**

A legally meaningful trademark search cannot be performed from this
environment: web search is blocked, and the trademark databases below
require interactive access. This review documents the required procedure
rather than claiming a search that was not performed.

Required procedure:

1. **USPTO** (United States): search "Sol" in the relevant classes —
   Class 9 (software, downloadable) and Class 42 (software services,
   SaaS) — via the USPTO trademark search. Expect a crowded field
   (Solana and other "Sol" marks); the question is whether any live mark
   in these classes would likely cause confusion with a computational
   work artifact format.
2. **EUIPO** (European Union): eSearch plus, same classes.
3. **WIPO** (international): Global Brand Database, "Sol", all classes.
4. **Analysis.** "Sol" is a common word and likely weak as a standalone
   mark; the practical question is collision with live marks in the
   relevant classes, not strength. If a conflicting live mark is found,
   options are: proceed with a descriptive/weak-mark analysis, or rename.
5. **Record.** Record the search results and the conclusion in a dated
   note under `docs/decisions/` (or `docs/reviews/`), and update the
   Project Name section pointer (E-004) accordingly.

Note: the vendor string `sol` in the media type is a project identifier
for IANA registration purposes; IANA registration does not require a
trademark, and registering the media type does not assert trademark
rights.

## 5. Findings and disposition

| # | Finding | Disposition |
|---|---|---|
| 1 | IANA `application/vnd.sol.notebook` available (zero `vnd.sol.*` entries, 2026-09-12) | Registration request drafted (`docs/registration/2026-09-12-iana-media-type-request.md`); submit with or just after public release |
| 2 | `.sol` is established (Solidity) | Already avoided by `.solnb`; rationale recorded; no action |
| 3 | `.solnb` no known usage (2026-09-12; search blocked, limited confidence) | Owner re-verifies before public release |
| 4 | Solana/SOL name similarity | Different domain; documented; no action |
| 5 | Public repo `github.com/LopezNuance/Sol` is the owner's own, currently stale | Sync after local work completes (owner direction 2026-09-12) |
| 6 | Trademark search not performed | Open required action; procedure documented (section 4) |

## 6. Conclusion

- **Namespace:** clear. The IANA media type is available and the extension
  avoids the established `.sol` collision.
- **Ecosystem:** clear, with two documented caveats (`.solnb` negative
  result at limited confidence; Solana name similarity).
- **Trademark:** open required action for the project owner, with the
  procedure recorded above.
- The Project Name section of `Sol_RFC.md` is updated (E-004) to point to
  this review and to record the trademark search as the remaining open
  action.
