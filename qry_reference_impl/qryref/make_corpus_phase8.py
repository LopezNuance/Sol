"""Generate the Phase 8 normative corpus cases (spec 32, 36.1/36.2).

Unblocks the normative cases blocked by Phase 8 in
docs/qry/2026-09-10-phase5-corpus-gap.md:

* QGOLD-011: leakage policy with redacted values and bucketed
  cardinality (32.4, 32.5): the query executes under a declared
  logical-disclosure policy (values no_disclosure, cardinality
  bucketed with the reference baseline partition, provenance
  redacted); the result discloses the restricted count only as the
  policy-declared 10-19 bucket and carries redacted provenance;
* QPATH-005: the hidden redaction leak (QV9-03): the same policy,
  but the result discloses the raw count of the restricted records;
* QPATH-027: the verbose denial (QV9-05): the error distinguishes
  nonexistent and unauthorized record IDs contrary to the policy's
  indistinguishable-from-missing requirement;
* QPATH-028: the provenance side door (QV8-08, QV9-04): values are
  redacted but the claim's provenance cites the restricted source,
  in the lower-membership and upper-derivation categories (32.7);
* QPATH-029: the timing promise (QV9-08): the result claims general
  non-inference while the policy declares timing protection only
  best-effort and carries no conforming profile (32.6).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .certified import infer_certified
from .disclosure import BASELINE_COUNT_BUCKETS
from .make_corpus_phase6 import write_case
from .validate import validate_case_dir

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

F_ID = [{"name": "id", "type": "i64", "nullable": False}]
F_ID_NAME = [{"name": "id", "type": "i64", "nullable": False},
             {"name": "name", "type": "string", "nullable": False}]

# ---------------------------------------------------------------------------
# QGOLD-011 / QPATH-005: COUNT over a restricted source under a
# bucketed-cardinality policy (32.4, 32.5)

S_011 = {"schema": F_ID,
         "tuples": [[i] for i in range(1, 16)],
         "restricted": True}

POLICY_011 = {
    "policy_id": "policy:restricted_claims",
    "logical_disclosure": {
        "values": "no_disclosure",
        "tuple_existence": "no_disclosure",
        "cardinality": "bucketed",
        "provenance": "redacted",
        "diagnostics": "uniform",
        "error_class": "uniform",
        "unauthorized_reference_behavior": "indistinguishable_from_missing",
    },
    "count_buckets": BASELINE_COUNT_BUCKETS,
    "residual_risk": ["correlation_inference_possible"],
}

Q_GOLD_011 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QGOLD-011",
    "description": "Leakage policy with redacted values and bucketed cardinality.",
    "sources": {"r": S_011},
    "nodes": [
        {"id": "r", "op": "read", "source": "r"},
        {"id": "c", "op": "aggregate", "input": "r",
         "aggregates": [{"func": "count_set", "name": "n"}]},
    ],
    "root": "c",
    "leakage_policy": POLICY_011,
}


def _redacted_claim(query: dict, root: str) -> dict:
    """The inferred bound with redacted provenance: the emitted record
    carries no restricted-source citations (32.7)."""
    obj = infer_certified(query)[root].to_json()
    ud = (obj["provenance"].get("upper_derivation") or {})
    obj["provenance"] = {
        "lower_membership_mode": "none",
        "lower_memberships": [],
        "upper_derivation": {
            "rule_id": ud.get("rule_id"),
            "input_relations": [],
            "sources": [],
            "evaluators": [],
            "rewrites": [],
            "view_substitutions": [],
        },
    }
    return obj


RECORD_011 = {
    "schema_version": "qry.bounds.v0.3",
    "query_id": "QGOLD-011",
    "root": "c",
    "root_bound": _redacted_claim(Q_GOLD_011, "c"),
    # The count is 15: disclosed only as the policy-declared bucket.
    "cardinality_disclosure": {"mode": "bucketed", "bucket": "10-19"},
}

Q_PATH_005 = {**Q_GOLD_011,
              "query_id": "QPATH-005",
              "description": ("The hidden redaction leak: the raw COUNT "
                              "reveals the number of restricted records "
                              "under a bucketed policy.")}
RECORD_005 = {
    "schema_version": "qry.bounds.v0.3",
    "query_id": "QPATH-005",
    "root": "c",
    "root_bound": _redacted_claim(Q_PATH_005, "c"),
    "cardinality_disclosure": {"mode": "raw", "value": 15},
}

# ---------------------------------------------------------------------------
# QPATH-027: the verbose denial (QV9-05)

S_027 = {"schema": F_ID, "tuples": [[1], [2], [3]], "restricted": True}

POLICY_027 = {
    "policy_id": "policy:restricted_claims",
    "logical_disclosure": {
        "values": "no_disclosure",
        "tuple_existence": "no_disclosure",
        "cardinality": "disclosed",
        "provenance": "visible",
        "diagnostics": "uniform",
        "error_class": "uniform",
        "unauthorized_reference_behavior": "indistinguishable_from_missing",
    },
    "residual_risk": ["correlation_inference_possible"],
}

Q_PATH_027 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-027",
    "description": ("The verbose denial: the error distinguishes "
                    "nonexistent and unauthorized record IDs contrary "
                    "to policy."),
    "sources": {"r": S_027},
    "nodes": [{"id": "r", "op": "read", "source": "r"}],
    "root": "r",
    "leakage_policy": POLICY_027,
}
RECORD_027 = {
    "schema_version": "qry.bounds.v0.3",
    "query_id": "QPATH-027",
    "root": "r",
    "root_bound": infer_certified(Q_PATH_027)["r"].to_json(),
    "error_behavior": "distinguished_from_missing",
}

# ---------------------------------------------------------------------------
# QPATH-028: the provenance side door (QV8-08, QV9-04)

S_028 = {"schema": F_ID_NAME,
         "tuples": [[1, "a"], [2, "b"], [3, "c"]],
         "restricted": True}

POLICY_028 = {
    "policy_id": "policy:restricted_claims",
    "logical_disclosure": {
        "values": "no_disclosure",
        "tuple_existence": "no_disclosure",
        "cardinality": "disclosed",
        "provenance": "redacted",
        "diagnostics": "uniform",
        "error_class": "uniform",
        "unauthorized_reference_behavior": "indistinguishable_from_missing",
    },
    "residual_risk": ["correlation_inference_possible"],
}

Q_PATH_028 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-028",
    "description": ("The provenance side door: values are redacted but "
                    "provenance reveals restricted record identities."),
    "sources": {"r": S_028},
    "nodes": [{"id": "r", "op": "read", "source": "r"}],
    "root": "r",
    "leakage_policy": POLICY_028,
}
CLAIM_028 = {
    "guarantee": "bounded",
    "lower": {"fields": F_ID_NAME, "tuples": [[1, "a"]]},
    "upper": {"fields": F_ID_NAME,
              "tuples": [[1, "a"], [2, "b"], [3, "c"]]},
    "lower_object": None,
    "upper_object": None,
    "result_object": None,
    "assurance": {"status": "contract_asserted", "evidence": ["source:r"],
                  "depends_on": ["source:r", "sol:bound/relation/v1"],
                  "stale": False},
    "provenance": {
        # Both the lower-membership cite and the upper-derivation
        # source name the restricted source (32.7: independent
        # visibility per category).
        "lower_membership_mode": "why",
        "lower_memberships": [
            {"tuple": [1, "a"], "mode": "why", "cites": ["source:r"]},
        ],
        "upper_derivation": {
            "rule_id": "sol:bound/relation/v1",
            "input_relations": [],
            "sources": ["source:r"],
            "evaluators": [],
            "rewrites": [],
            "view_substitutions": [],
        },
    },
    "may_be_empty_groups": [],
    "order": [],
    "intervals": [],
    "bound_rule": "sol:bound/relation/v1",
}
RECORD_028 = {"schema_version": "qry.bounds.v0.3", "query_id": "QPATH-028",
              "root": "r", "root_bound": CLAIM_028}

# ---------------------------------------------------------------------------
# QPATH-029: the timing promise (QV9-08)

S_029 = {"schema": F_ID, "tuples": [[1], [2]], "restricted": True}

POLICY_029 = {
    "policy_id": "policy:restricted_claims",
    "logical_disclosure": {
        "values": "no_disclosure",
        "tuple_existence": "no_disclosure",
        "cardinality": "disclosed",
        "provenance": "redacted",
        "diagnostics": "uniform",
        "error_class": "uniform",
        "unauthorized_reference_behavior": "indistinguishable_from_missing",
    },
    "physical_side_channels": {"timing": "best_effort"},
    "residual_risk": ["timing_inference_possible"],
}

Q_PATH_029 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-029",
    "description": ("The timing promise: the service claims general "
                    "non-inference while declaring timing protection "
                    "only best-effort."),
    "sources": {"r": S_029},
    "nodes": [{"id": "r", "op": "read", "source": "r"}],
    "root": "r",
    "leakage_policy": POLICY_029,
}
RECORD_029 = {
    "schema_version": "qry.bounds.v0.3",
    "query_id": "QPATH-029",
    "root": "r",
    "root_bound": _redacted_claim(Q_PATH_029, "r"),
    "non_inference_claim": True,
}

# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir", nargs="?", default="corpus")
    args = ap.parse_args(argv)
    cases_dir = Path(args.corpus_dir) / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    write_case(cases_dir / "QGOLD-011", "QGOLD-011",
               Q_GOLD_011["description"], [], Q_GOLD_011,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": RECORD_011}})
    write_case(cases_dir / "QPATH-005", "QPATH-005",
               Q_PATH_005["description"], ["QV9-03"], Q_PATH_005,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": RECORD_005}})
    write_case(cases_dir / "QPATH-027", "QPATH-027",
               Q_PATH_027["description"], ["QV9-05"], Q_PATH_027,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": RECORD_027}})
    write_case(cases_dir / "QPATH-028", "QPATH-028",
               Q_PATH_028["description"], ["QV8-08", "QV9-04"], Q_PATH_028,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": RECORD_028}})
    write_case(cases_dir / "QPATH-029", "QPATH-029",
               Q_PATH_029["description"], ["QV9-08"], Q_PATH_029,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": RECORD_029}})

    # Self-check: each case validates to exactly the expected
    # diagnostics (37.5 determinism).
    for name, expected in (("QGOLD-011", set()),
                           ("QPATH-005", {"QV9-03"}),
                           ("QPATH-027", {"QV9-05"}),
                           ("QPATH-028", {"QV8-08", "QV9-04"}),
                           ("QPATH-029", {"QV9-08"})):
        p = cases_dir / name
        manifest = json.loads((p / "manifest.json").read_text())
        got = {d.rule_id for d in validate_case_dir(p, check_match=not expected,
                                                    manifest=manifest)}
        assert got == expected, (name, got, expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
