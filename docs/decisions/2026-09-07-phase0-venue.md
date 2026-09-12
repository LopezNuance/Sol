# Decision: Submission venue and sequencing

Date: 2026-09-07 (UTC)
Status: Decided (Phase 0 closed)
Decider: Project owner (Scott), via 2026-09-07 direction
Supersedes: Phase 0 open item in `NEXT_STEPS_2026-09-07T0315Z.md`

## Decision

Submission proceeds in three stages:

1. **Internal venue (now).** The submission package is produced and reviewed internally.
   Internal requirements that this stage must satisfy:
   - Promoted non-draft version of RFC-SOL-0001 with errata log and decision notes.
   - Published normative schemas (Phase 2) and a green validator corpus under schema enforcement.
   - Recorded demonstration of the 25 acceptance criteria (RFC §58).
   - Versioning policy: the frozen baseline is v0.1.0-draft. The first unfreeze promotes to
     **v0.1.0** and carries the errata plus the batched unfreeze candidates from Phase 1
     (per the freeze review's triage discipline: errata / corpus entry / unfreeze candidate;
     batch unfreeze candidates, do not unfreeze per-item).
   - No IANA or trademark actions at this stage; the Project Name section's
     "subject to namespace, trademark, and ecosystem review" remains open.
2. **Public specification (next).** After internal review closes:
   - Namespace/trademark/ecosystem review of "Sol", `.solnb`, `application/vnd.sol.notebook`.
   - IANA media-type registration for `application/vnd.sol.notebook` (vendor-suffixed type;
     registration requires the RFC to be citable, so this lands with or just after public release).
   - Public comment cycle on the promoted version; findings triaged the same way as internal.
3. **IETF-style (final).** Only after the public spec is stable:
   - Convert to the IETF submission format (BCP 78/79 boilerplate, abstract, author list,
     change log) if the venue is confirmed as an IETF working group or independent submission.
   - No content rewrites expected: the RFC already uses RFC 2119/8174 normative language.

## Rationale

- Internal-first de-risks the normative decisions (Phase 1) against a real review audience
  before external commitments (registration, trademark) are made.
- The three stages match the RFC's own escalation of commitment: draft freeze (done) →
  normative promotion (v0.1.0) → public standard → international standard.
- IETF-style is last because it imposes the heaviest process (AD sponsorship, WG consensus)
  and is only worth entering once the public spec has survived a comment cycle.

## Consequences

- Phase 1 (2026-09-07) proceeds now; its unfreeze candidates batch into v0.1.0.
- Phase 5's external-review step splits into: internal review (stage 1), public comment
  (stage 2), IETF conversion (stage 3).
