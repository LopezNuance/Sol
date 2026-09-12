"""Generate the Phase 7 normative corpus cases (spec 36.1/36.2, 37.7).

Unblocks the normative cases blocked by Phase 7 in
docs/qry/2026-09-10-phase5-corpus-gap.md:

* QGOLD-005: exact machine-summary substitution with a matching source
  commit (28.3, 28.5, 37.7): a field-complete exact machine summary
  (levels 0-2) is a covering exact view, so the substitution applies and
  is recorded with the covering proof and the source-commit pin;
* QPATH-013: the provenance-dropping rewrite (12.4-12.5, 25.4.3): the
  claim is value-equivalent but its lower tuples carry no membership
  provenance in the requested mode (QV8-05), and the rewrite cited in
  its provenance does not cover the query-required provenance dimension
  (QV7-03);
* QPATH-014: the timestamp time traveler (17.1, 17.5, QV1-02): the
  latest commit is selected by wall-clock timestamp across divergent
  branches, with no ancestry relation or tie rule -- a temporal
  validation failure.

The remaining blocked cases (QGOLD-011, QPATH-005, QPATH-027,
QPATH-028, QPATH-029) unblock in Phase 8 and stay documented, not
shipped as failing directories (ground rule: green at every phase
boundary).
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

from .canonical import source_manifest
from .make_corpus_phase6 import write_case
from .make_rewrites_corpus import (
    A,
    PRED_Y,
    SUBST_RULE,
    gold_covering_proof_digest,
)
from .rewrites import EXPERIMENTAL_RULE, RULES, RewriteRequest, apply_rewrite
from .engine import semantic_diagnostics

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

A_MANIFEST = source_manifest({"sources": {"a": A}})["manifest_digest"]
GOLD_PROOF = gold_covering_proof_digest()

# ---------------------------------------------------------------------------
# QGOLD-005: exact machine-summary substitution (clean)

Q_GOLD_005 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QGOLD-005",
    "description": "Exact machine-summary substitution with matching source commit.",
    "sources": {"a": A},
    "nodes": [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "f", "op": "filter", "input": "ra", "predicate": PRED_Y},
    ],
    "root": "f",
}

REWRITE_005 = {
    "rule_id": SUBST_RULE,
    "location": "node:f",
    "covering_proof": GOLD_PROOF,
    "source_commit": A_MANIFEST,
}

REWRITTEN_005 = copy.deepcopy(Q_GOLD_005)
REWRITTEN_005["sources"]["a"]["machine_summary"] = {
    "covering_proof": GOLD_PROOF,
    "source_commit": A_MANIFEST,
}

RECORD_005 = {
    "rule_id": SUBST_RULE,
    "location": "node:f",
    "assurance": RULES[SUBST_RULE].assurance,
    "preserved_dimensions": list(RULES[SUBST_RULE].preserves),
    "proof_evidence_kinds": [k for k, _ in RULES[SUBST_RULE].proof_evidence],
    "disclosure_proof": None,
    "source_commit": A_MANIFEST,
    "covering_proof": GOLD_PROOF,
}

EXPECTED_005 = {"applied": True, "rewritten_query": REWRITTEN_005,
                "record": RECORD_005}

# ---------------------------------------------------------------------------
# QPATH-013: the provenance-dropping rewrite (QV7-03, QV8-05)

S_013 = {"schema": [{"name": "id", "type": "i64", "nullable": False},
                    {"name": "name", "type": "string", "nullable": False}],
         "tuples": [[1, "a"], [2, "b"], [3, "c"]]}
F_013 = [{"name": "id", "type": "i64", "nullable": False},
         {"name": "name", "type": "string", "nullable": False}]

Q_PATH_013 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-013",
    "description": ("The provenance-dropping rewrite: value-equivalent rows "
                    "lose the required lower-membership lineage."),
    "required_dimensions": ["value", "provenance"],
    "sources": {"s": S_013},
    "nodes": [{"id": "r", "op": "read", "source": "s"}],
    "root": "r",
}

CLAIM_013 = {
    "guarantee": "bounded",
    "lower": {"fields": F_013, "tuples": [[1, "a"]]},
    "upper": {"fields": F_013, "tuples": [[1, "a"], [2, "b"], [3, "c"]]},
    "lower_object": None,
    "upper_object": None,
    "result_object": None,
    "assurance": {"status": "contract_asserted", "evidence": ["source:s"],
                  "depends_on": ["source:s", "sol:bound/relation/v1"],
                  "stale": False},
    "provenance": {
        # The requested mode is `why`, but the rewrite dropped the
        # lineage: no lower tuple carries a why membership entry (QV8-05).
        "lower_membership_mode": "why",
        "lower_memberships": [],
        "upper_derivation": {
            "rule_id": "sol:bound/relation/v1",
            "input_relations": [],
            "sources": ["source:s"],
            "evaluators": [],
            # The cited rewrite preserves value and multiplicity only;
            # the query requires provenance (QV7-03).
            "rewrites": [EXPERIMENTAL_RULE],
            "view_substitutions": [],
        },
    },
    "may_be_empty_groups": [],
    "order": [],
    "intervals": [],
    "bound_rule": "sol:bound/relation/v1",
}

BOUNDS_013 = {"query_id": "QPATH-013", "root": "r", "root_bound": CLAIM_013,
              "schema_version": "qry.bounds.v0.3"}

# ---------------------------------------------------------------------------
# QPATH-014: the timestamp time traveler (QV1-02)

Q_PATH_014 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-014",
    "description": ("The timestamp time traveler: the latest commit is "
                    "selected by wall-clock timestamp across divergent "
                    "branches, with no ancestry relation or tie rule."),
    "sources": {"s": {
        "schema": [{"name": "id", "type": "i64", "nullable": False}],
        "tuples": [[1], [2]],
        "branch": "main",
        "commit": "object:sha256:" + "00" * 32,
        "latest": {"branch": "main"},
    }},
    "nodes": [{"id": "r", "op": "read", "source": "s"}],
    "root": "r",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir", nargs="?", default="corpus")
    args = ap.parse_args(argv)
    cases_dir = Path(args.corpus_dir) / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    # Self-check: the kernel applies the substitution and the outcome
    # matches the committed expectation exactly.
    outcome = apply_rewrite(Q_GOLD_005, RewriteRequest.from_dict(REWRITE_005))
    assert outcome.applied, [d.rule_id for d in outcome.diagnostics]
    assert not outcome.diagnostics, [d.rule_id for d in outcome.diagnostics]
    assert outcome.record == RECORD_005, outcome.record
    from .canonical import canonicalize_query
    assert (canonicalize_query(outcome.rewritten_query)
            == canonicalize_query(REWRITTEN_005))

    # Self-check: the temporal declaration fails validation (17.5).
    got = {d.rule_id for d in semantic_diagnostics(Q_PATH_014)}
    assert got == {"QV1-02"}, got

    write_case(cases_dir / "QGOLD-005", "QGOLD-005",
               Q_GOLD_005["description"], [], Q_GOLD_005,
               extra={"manifest": {},
                      "files": {"rewrite.json": REWRITE_005,
                                "expected.json": EXPECTED_005}})
    write_case(cases_dir / "QPATH-013", "QPATH-013",
               Q_PATH_013["description"], ["QV7-03", "QV8-05"], Q_PATH_013,
               extra={"manifest": {}, "files": {"expected_bounds.json": BOUNDS_013}})
    write_case(cases_dir / "QPATH-014", "QPATH-014",
               Q_PATH_014["description"], ["QV1-02"], Q_PATH_014)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
