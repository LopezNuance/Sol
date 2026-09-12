# Decision: SOL-QRY submission relationship to RFC-SOL-0001

Date: 2026-09-08 (UTC)
Status: Decided (companion-track step 5)
Decider: Project owner (Scott), via 2026-09-08 direction to unblock the QRY track

## Decision

RFC-SOL-QRY-0001 is submitted as a **separate RFC**, published as a **companion
specification** to RFC-SOL-0001 — a standalone, independently versioned
document that cross-references the base RFC, not an annex or appendix of it.

It is submitted alongside RFC-SOL-0001 at the public-specification venue stage
(stage 2 of the Phase 0 venue decision), after the base RFC's internal stage
closes. It does not amend or unfreeze RFC-SOL-0001.

## Rationale

- **Architectural boundary.** §42 of the v0.3.0 draft defines SOL-QRY as one
  of a family of companion specifications (SOL-IDX, SOL-PLAN, SOL-MEM,
  SOL-SEM, SOL-FED, SOL-PRIV) that "preserves architectural boundaries." A
  separate RFC is the natural unit for each family member.
- **Independent versioning.** SOL-QRY is at v0.3.0 while the base RFC is at
  v0.1.0; they evolve on different clocks. A companion annex would force
  coupled versioning.
- **Change-control isolation.** The v0.3.0 draft states it "does not amend or
  unfreeze RFC-SOL-0001." A separate RFC keeps the base RFC's change-control
  boundary intact.
- **Precedent.** The base RFC's post-v0.1 question #4 ("Should Work Server
  Protocol be a separate RFC?") sets the precedent for how Sol splits specs;
  a separate companion RFC is consistent with that direction.
- **IETF pattern.** A base RFC plus companion RFCs (cross-referenced,
  independently numbered) is the standard IETF structure, matching the
  eventual IETF-style venue stage.

## Consequences

- SOL-QRY keeps its own RFC number and change-control section.
- The base RFC's §59 post-v0.1 list and the QRY draft's §42 companion list
  cross-reference each other; no content moves between the documents.
- At the public-spec stage, both RFCs are submitted together with a
  cross-reference note; the IANA/trademark actions for the base RFC (stage 2)
  are unaffected by the QRY companion.
- The physical side-channel and privacy profiles (SOL-PRIV) and the
  index/plan/mem/sem/fed companions remain separate future RFCs, not part of
  this submission.
