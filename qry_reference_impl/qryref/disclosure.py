"""Logical disclosure and leakage separation (spec 32).

Implements the logical-layer halves of gate conditions 6 and 19: the
logical-disclosure baseline (mandatory bucketed cardinality, redaction,
provenance visibility, error behavior) and the separation of logical
and physical leakage claims. Physical side-channel conformance
profiles (37.8) are post-gate and out of scope; the physical
separation already enforced by the rewrite kernel (QV7-09/QV9-10)
stays as is.

Checks (inert unless the query declares a leakage policy or the
record makes a disclosure commitment):

* QV9-03: cardinality is suppressed, bucketed, or disclosed as
  declared. A bucketed policy requires a well-formed count-bucket
  partition (the reference baseline is ``BASELINE_COUNT_BUCKETS``,
  which carries the mandatory 10-19 bucket); a raw count under a
  bucketed policy is the hidden redaction leak (QPATH-005).
* QV8-08 / QV9-04: the claim's provenance obeys the policy's
  provenance visibility, applied independently to lower-membership
  provenance, upper-bound derivation provenance, and rewrite and
  evaluator identities (32.7). Citing a restricted source under a
  redacted provenance policy is the provenance side door (QPATH-028).
* QV9-05: the declared error behavior for unauthorized references
  obeys the policy (32.5: avoid distinguishing nonexistent and
  unauthorized references unless policy permits it; QPATH-027).
* QV9-08: a general non-inference claim requires a conforming
  profile (32.6: adversary model, allowed query history, leakage
  channels, verification method) and no declared physical channel
  weaker than suppressed (QPATH-029).
"""
from __future__ import annotations

from typing import Any

from .diagnostics import Diagnostic, diag

# The reference baseline for the mandatory bucketed-cardinality
# mechanism (32.5): a partition of the non-negative counts that
# carries an explicit 10-19 bucket (plan Phase 8).
BASELINE_COUNT_BUCKETS = ["0", "1-9", "10-19", "20-99", "100+"]

_OPEN = float("inf")


def _bucket_range(bucket: Any) -> tuple[int, int | float] | None:
    """Parse one count bucket: 'N' (exact), 'A-B' (range), 'N+' or
    'more_than_N' (open at the top)."""
    if not isinstance(bucket, str):
        return None
    if bucket.startswith("more_than_"):
        rest = bucket[len("more_than_"):]
        if not rest.isdigit():
            return None
        return int(rest) + 1, _OPEN
    if bucket.endswith("+"):
        rest = bucket[:-1]
        if not rest.isdigit():
            return None
        return int(rest), _OPEN
    if "-" in bucket:
        a, _, b = bucket.partition("-")
        if not (a.isdigit() and b.isdigit()):
            return None
        lo, hi = int(a), int(b)
        if lo > hi:
            return None
        return lo, hi
    if bucket.isdigit():
        n = int(bucket)
        return n, n
    return None


def _valid_bucket_partition(buckets: Any) -> bool:
    """A well-formed partition of the non-negative integers: starts at
    0, contiguous, no overlaps, open at the top."""
    if not isinstance(buckets, list) or not buckets:
        return False
    ranges = [_bucket_range(b) for b in buckets]
    if any(r is None for r in ranges):
        return False
    ranges.sort(key=lambda r: r[0])
    if ranges[0][0] != 0 or ranges[-1][1] != _OPEN:
        return False
    for (lo, hi), (nlo, _nhi) in zip(ranges, ranges[1:]):
        if nlo != hi + 1:
            return False
    return True


def _names_restricted(cite: str, restricted: set[str]) -> bool:
    """A provenance citation names a restricted source when it is
    'source:<name>' or 'record:<name>:<id>' for a restricted <name>."""
    if cite.startswith("source:"):
        return cite[len("source:"):] in restricted
    if cite.startswith("record:"):
        name = cite[len("record:"):].split(":", 1)[0]
        return name in restricted
    return False


def disclosure_diagnostics(
    query: dict[str, Any],
    claim,
    record: dict[str, Any] | None = None,
) -> list[Diagnostic]:
    """Logical-disclosure checks over a claimed bound record (32).

    ``claim`` is a CertifiedBound; ``record`` is the full bound record
    (may be None in unit contexts where only the claim is available).
    """
    diags: list[Diagnostic] = []
    policy = query.get("leakage_policy")
    ld = (policy or {}).get("logical_disclosure") or {}
    restricted = {name for name, src in (query.get("sources") or {}).items()
                  if isinstance(src, dict) and src.get("restricted")}

    # QV9-03: cardinality is suppressed, bucketed, or disclosed as
    # declared (32.5). Suppression is always permitted: absence of a
    # disclosure declaration counts as suppressed.
    card = ld.get("cardinality")
    disc = record.get("cardinality_disclosure") if isinstance(record, dict) else None
    if card == "bucketed":
        buckets = (policy or {}).get("count_buckets")
        if not _valid_bucket_partition(buckets):
            diags.append(diag("QV9-03", "cardinality_policy_invalid",
                              "query.leakage_policy",
                              "Bucketed cardinality policy has no well-formed count-bucket "
                              "partition (must start at 0, be contiguous, and be open at "
                              "the top)"))
        if disc:
            mode = disc.get("mode")
            if mode == "raw":
                diags.append(diag("QV9-03", "raw_cardinality_under_bucketed_policy",
                                  "record.cardinality_disclosure",
                                  "Raw cardinality is disclosed under a bucketed "
                                  "cardinality policy"))
            elif mode == "bucketed" and isinstance(buckets, list) \
                    and disc.get("bucket") not in buckets:
                diags.append(diag("QV9-03", "undeclared_bucket",
                                  "record.cardinality_disclosure",
                                  f"Disclosed bucket {disc.get('bucket')!r} is not "
                                  "declared by the policy"))
    elif card == "suppressed" and disc and disc.get("mode") in {"raw", "bucketed"}:
        diags.append(diag("QV9-03", "cardinality_disclosed_under_suppression",
                          "record.cardinality_disclosure",
                          "Cardinality is disclosed although the policy suppresses it"))

    # QV8-08 / QV9-04: provenance visibility, applied independently to
    # lower-membership provenance, upper-bound derivation provenance,
    # and rewrite and evaluator identities (32.7).
    if ld.get("provenance") in {"redacted", "suppressed"} and restricted:
        prov = claim.provenance
        offending: list[str] = []
        for lm in prov.lower_memberships:
            for c in lm.cites:
                if _names_restricted(c, restricted):
                    offending.append(c)
        ud = prov.upper_derivation
        if ud is not None:
            for cat in ("sources", "evaluators", "rewrites"):
                for c in getattr(ud, cat):
                    if _names_restricted(c, restricted):
                        offending.append(c)
        if offending:
            diags.append(diag("QV8-08", "provenance_disclosure_policy_violation",
                              "root_bound.provenance",
                              "Provenance disclosure violates the selected leakage "
                              "policy: " + ", ".join(sorted(set(offending)))))
            diags.append(diag("QV9-04", "independent_visibility_violation",
                              "root_bound.provenance",
                              "Provenance does not obey the policy's independent "
                              "visibility rules for lower-membership, upper-derivation, "
                              "and rewrite/evaluator identities (32.7)"))

    # QV9-05: error and unauthorized-reference behavior obey policy
    # (32.5, 32.4).
    if (ld.get("unauthorized_reference_behavior") == "indistinguishable_from_missing"
            and isinstance(record, dict)
            and record.get("error_behavior") == "distinguished_from_missing"):
        diags.append(diag("QV9-05", "verbose_denial", "record.error_behavior",
                          "Error distinguishes nonexistent and unauthorized references "
                          "contrary to policy"))

    # QV9-08: no general non-inference claim without a conforming
    # profile (32.6). A conforming profile defines the adversary
    # model, allowed query history, leakage channels, and
    # verification method; a declared physical channel weaker than
    # suppressed defeats the claim.
    if isinstance(record, dict) and record.get("non_inference_claim"):
        profile = (policy or {}).get("non_inference_profile")
        complete = isinstance(profile, dict) and all(
            profile.get(f) for f in ("adversary_model", "query_history",
                                     "leakage_channels", "verification_method"))
        weak = sorted(c for c, v in ((policy or {}).get("physical_side_channels") or {}).items()
                      if v in {"best_effort", "visible"})
        if not complete or weak:
            why = []
            if not complete:
                why.append("no conforming non-inference profile (32.6)")
            if weak:
                why.append("declared physical channels weaker than suppressed: "
                           + ", ".join(weak))
            diags.append(diag("QV9-08", "non_inference_claim_without_profile",
                              "record.non_inference_claim",
                              "General non-inference claim appears without "
                              + " and ".join(why)))
    return diags
