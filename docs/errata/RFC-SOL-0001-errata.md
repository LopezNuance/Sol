# Errata Log: RFC-SOL-0001

Per the Change Control section, errata may correct spelling, formatting,
example hygiene, appendix text, and non-normative clarification without
changing the version. This log records the two errata-class notes from the
Final Freeze Review of v0.1.0-draft. Both are batched into the v0.1.0
promotion (Phase 5) alongside the unfreeze candidates, per the freeze
review's triage discipline.

## E-001: Duplicate example digest in section 18 / section 22

- **Date recorded:** 2026-09-07 (Final Freeze Review, note 1)
- **Date applied:** 2026-09-07 (GOLD-01 assembly, Phase 4)
- **Class:** errata (example hygiene)
- **Finding.** Section 18's example `contract_hash` and section 22's example
  `instruction_ref` both use the placeholder digest `9999...` for different
  content.
- **Disposition.** The section 18 and section 22 examples are partial
  fragments and remain as published. The duplication is resolved in the
  assembled conformance artifact GOLD-01
  (`sol_validator/corpus/GOLD-01/`): `contract_hash` is the sha256 of the
  cell's `produces` contract, and `instruction_ref` is the internal object
  reference to the instruction content — distinct digests of distinct
  content. The assembled artifact validates with zero diagnostics, per the
  Change Control gate ("complete examples intended for conformance use must
  validate").

## E-002: V0-04 scope versus `context_status`

- **Date recorded:** 2026-09-07 (Final Freeze Review, note 2)
- **Date applied:** 2026-09-07 (Appendix A; this log)
- **Class:** errata (non-normative clarification)
- **Finding.** V0-04 fails validation on status values outside registered
  vocabularies, but section 37.4's `context_status` values are
  "recommended," not registered (pending post-v0.1 question #12).
- **Disposition.** Appendix A's V0-04 entry now states that V0-04 applies to
  `lifecycle`, `staleness`, and `verification` statuses, and that
  `context_status` is open until the registry decision. The reference
  validator already behaves this way (it checks only the three registered
  dimensions); the sentence prevents an implementer from over-enforcing.

## E-003: Unregistered compression identifier in section 42 example

- **Date recorded:** 2026-09-08 (Phase 5 internal review, venue stage 1)
- **Date applied:** 2026-09-08 (v0.1.0 promotion)
- **Class:** errata (example hygiene)
- **Finding.** The section 42 object-record example declared
  `compression: "zstd"`, a short name outside the section 43 registered
  identifier set; a conforming reader would reject the example (V0-10),
  breaking the Change Control examples-must-validate gate.
- **Disposition.** The example now declares `sol:compression/zstd`,
  matching the published object schema and the corpus object records.

## E-004: Project Name section review status

- **Date recorded:** 2026-09-12 (venue stage 2, namespace review)
- **Date applied:** 2026-09-12 (Project Name section; this log)
- **Class:** errata (non-normative clarification)
- **Finding.** The Project Name section stated that the name, extension,
  and media type "remain subject to namespace, trademark, and ecosystem
  review" without recording the review's outcome.
- **Disposition.** The section now points to the completed namespace and
  ecosystem review
  (`docs/reviews/2026-09-12-stage2-namespace-review.md`) and records the
  trademark search as the remaining required open action. No normative
  change.

## Promotion record

2026-09-08: the v0.1.0 promotion (Phase 5) carried both errata into the
promoted baseline alongside the batched unfreeze candidates. E-001's
resolution (GOLD-01 assembly) and E-002's Appendix A sentence are present
in the promoted document. The Phase 5 internal review (venue stage 1,
`docs/reviews/2026-09-08-v0.1.0-internal-review.md`) found one further
errata-class item (E-003) and Appendix B drift, both corrected in the
same promotion; no unfreeze candidates were raised.
