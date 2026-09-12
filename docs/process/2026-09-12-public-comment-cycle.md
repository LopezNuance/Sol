# Public Comment Cycle Process (venue stage 2)

Date: 2026-09-12 (UTC)
Status: process defined; channel and window pending owner confirmation
Subject: venue stage 2 checklist item 3, per
`docs/decisions/2026-09-07-phase0-venue.md`

## Purpose

The venue decision requires a public comment cycle on the promoted
versions, with findings triaged the same way as the internal review. This
document defines the channel, window, triage discipline, versioning policy,
and exit criteria.

## Scope

- RFC-SOL-0001 v0.1.0 (`Sol_RFC.md`; submission package
  `docs/submission/2026-09-08-v0.1.0-submission-package.md`)
- RFC-SOL-QRY-0001 v0.3.0 (`documentation/RFC-SOL-QRY-0001-v0.3.0.md`;
  submission package
  `docs/submission/2026-09-11-qry-v0.3.0-submission-package.md`),
  submitted alongside the base RFC as a companion specification (per
  `docs/decisions/2026-09-08-qry-submission-relationship.md`)

## Channel

**Proposed (pending owner confirmation):** issues on the public repository
`github.com/LopezNuance/Sol`. The repository is the public face of this
work and is synced from this local tree once the local work is complete
(owner direction 2026-09-12); the comment cycle therefore starts at public
release, after the sync.

## Window

**Proposed (pending owner confirmation):** 30 days from public release.
The venue decision does not fix a window. The window closes on a recorded
date; late findings are triaged the same way but are not part of the
cycle's exit criteria.

## Triage discipline

Identical to the internal review (venue stage 1,
`docs/reviews/2026-09-08-v0.1.0-internal-review.md`) and to the QRY §44
triage policy: every finding is triaged into exactly one bucket.

1. **errata** — spec wording, formatting, example hygiene, appendix text,
   non-normative clarification. Applied without a version bump; recorded in
   the errata log (`docs/errata/RFC-SOL-0001-errata.md` for the base RFC;
   the QRY spec's own errata record for the companion).
2. **corpus entry** — a new pathology or golden case. No spec change; the
   case is added to the corpus with its expected diagnostics, and the
   corpus is re-run to green.
3. **unfreeze candidate** — a normative change (invariant, requirement,
   status vocabulary, transition table, grammar, conformance level, or
   validation rule). Batched into the next minor version per Change
   Control; never applied per-item.

A finding that touches both specs is triaged once per spec (each spec has
its own baseline and change control).

## Versioning policy for findings

- **errata:** applied to the current baseline without a version bump;
  logged with date and disposition.
- **corpus entry:** corpus only; no spec version change.
- **unfreeze candidate:** batched into the next promotion (v0.2.0 for the
  base RFC; the QRY spec's next version for the companion), per each
  spec's Change Control. The promotion carries the batched candidates
  together with the errata log, as the v0.1.0 promotion did.

## Triage log

Maintained at `docs/reviews/2026-09-12-public-comment-triage.md` (created
when the cycle opens). Template:

```text
| # | Date | Source (issue) | Spec | Finding | Bucket | Disposition |
|---|------|----------------|------|---------|--------|-------------|
```

## Exit criteria

Per the Definition of Done (item 8,
`NEXT_STEPS_2026-09-07T0315Z.md`):

1. The comment window has closed (recorded date).
2. Every finding is triaged and recorded in the triage log.
3. No open unfreeze candidate blocks the submission version (candidates
   are either resolved or batched into a scheduled promotion).
4. All errata are applied and logged; all corpus entries are added and the
   corpus is green under the standard validation commands.

## Process notes

- The IANA registration
  (`docs/registration/2026-09-12-iana-media-type-request.md`) is
  submitted with or just after public release. It is independent of the
  comment-cycle outcome: the media type identifies the container format,
  and comment findings are triaged against the spec, not against the
  registration.
- The trademark search (open action,
  `docs/reviews/2026-09-12-stage2-namespace-review.md`) is a precondition
  for public release, not for the comment cycle.
- Stage 3 (IETF-style conversion) starts only after the comment cycle
  closes and the public spec is stable, per the venue decision.
