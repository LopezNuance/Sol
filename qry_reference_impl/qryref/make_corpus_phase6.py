"""Generate the Phase 6 normative corpus cases (spec 36.1/36.2, 37.6).

Unblocks the eight normative cases blocked by Phase 6 in
docs/qry/2026-09-10-phase5-corpus-gap.md:

* QGOLD-009: materialized semantic assessment queried as ordinary data
  (26.3, 26.7): an assessment source carries the immutable assessment
  relation plus the recorded evaluation (complete key, immutable result
  object); the query is an ordinary exact query over that relation;
* QPATH-002: the semantic equality forgery (26.8, QINV-04): vector
  similarity is substituted for exact `=`;
* QPATH-007: the duplicated stochastic call (26.4): the optimizer
  duplicates an inline stochastic evaluator;
* QPATH-020: the heuristic resurrection (13.7.1, 26.6): heuristic
  semantic membership passes through a join and the output is labeled
  exact;
* QPATH-024: the transient memo (26.5, QINV-13): a deterministic-per-key
  declaration backed by a transient cache;
* QPATH-025: the incomplete evaluation key (26.5, Q15): the
  prompt-template digest is omitted from the key;
* QPATH-033: the hidden heuristic view (28.5): a field-complete machine
  summary produced heuristically is substituted into an exact query;
* QPATH-040: the fabricated selector (13.7.1, 26.6): a tuple-generating
  evaluator is modeled as a tuple-preserving Select inheriting the input
  relation as an upper bound.

The remaining blocked cases (QGOLD-005, QGOLD-011, QPATH-005, QPATH-013,
QPATH-014, QPATH-027, QPATH-028, QPATH-029) unblock in Phases 7-8 and
stay documented, not shipped as failing directories (ground rule: green
at every phase boundary).
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .canonical import source_manifest
from .certified import RULE_JOIN, RULE_SELECT, RULE_STRUCTURAL, infer_certified
from .evaluators import assessment_relation_digest
from .make_corpus_phase5 import ORDERS_EXACT, USERS_EXACT
from .make_corpus_v3 import USERS_SCHEMA, assurance, bound, derivation, provenance, rel
from .make_rewrites_corpus import A, SUBST_RULE, heuristic_covering_proof_digest

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

VECTOR_SIM = "sol:evaluator/vector_similarity/v1"
SEM_EQ = "sol:evaluator/semantic_equivalence/v1"
TUPLE_GEN = "sol:evaluator/tuple_generator/v1"
BARRIER = "urn:qry:v0.3:semantic-evaluator-barrier"
MATERIALIZED = "urn:qry:v0.3:materialized-assessment"

# ---------------------------------------------------------------------------
# Evaluation keys (26.5, Q15)

COMMIT_42 = "commit:commit_042"


def _digest(name: str) -> str:
    import hashlib
    return "digest:sha256:" + hashlib.sha256(name.encode("utf-8")).hexdigest()


def full_key(evaluator_id: str, input_digests: list[str], transient: bool = False) -> dict:
    """A complete evaluation key: the Q15 universal fields plus the
    contract-declared evaluator-specific fields."""
    key = {
        "evaluator_id": evaluator_id,
        "source_commit": COMMIT_42,
        "input_digests": input_digests,
        "visibility_policy": "policy:internal_full",
        "authorization_policy": "policy:internal_authorized",
        "leakage_policy": "policy:internal_standard",
        "assessment_policy": "policy:internal_assessment",
        "output_schema": "object:sha256:" + "cd" * 32,
        "model_id": "provider/model",
        "model_version": "2026-07-01",
        "configuration_digest": _digest(f"{evaluator_id}:config"),
        "prompt_template_digest": _digest(f"{evaluator_id}:prompt"),
        "tool_policy_digest": _digest(f"{evaluator_id}:tool-policy"),
        "random_seed": 48191,
        "service_version": "v2026.07",
    }
    if transient:
        key["transient"] = True
    return key


# ---------------------------------------------------------------------------
# QGOLD-009: materialized semantic assessment queried as ordinary data

ASSESSMENT_SCHEMA = [
    {"name": "evaluation_id", "type": "string", "nullable": False},
    {"name": "left_ref", "type": "string", "nullable": False},
    {"name": "right_ref", "type": "string", "nullable": False},
    {"name": "label", "type": "string", "nullable": False},
    {"name": "score", "type": "decimal", "nullable": False},
    {"name": "evaluator_actor", "type": "string", "nullable": False},
    {"name": "model_id", "type": "string", "nullable": False},
    {"name": "configuration_digest", "type": "string", "nullable": False},
    {"name": "evidence_ref", "type": "string", "nullable": False},
    {"name": "created_at", "type": "string", "nullable": False},
]

ASSESSMENT_TUPLES = [
    ["semantic_eval_041", "cell:cell_001", "cell:cell_002", "equivalent", 0.97,
     "agent:semantic_matcher_001", "provider/model", _digest(f"{SEM_EQ}:config"),
     "object:sha256:" + "d1" * 32, "2026-07-02T10:00:00Z"],
    ["semantic_eval_042", "cell:cell_001", "cell:cell_003", "distinct", 0.31,
     "agent:semantic_matcher_001", "provider/model", _digest(f"{SEM_EQ}:config"),
     "object:sha256:" + "d2" * 32, "2026-07-02T10:00:00Z"],
    ["semantic_eval_043", "cell:cell_002", "cell:cell_003", "equivalent", 0.88,
     "agent:semantic_matcher_001", "provider/model", _digest(f"{SEM_EQ}:config"),
     "object:sha256:" + "d3" * 32, "2026-07-02T10:00:00Z"],
]

ASSESSMENT_SOURCE = {
    "schema": ASSESSMENT_SCHEMA,
    "tuples": ASSESSMENT_TUPLES,
    "assessment": {
        "evaluation_id": "semantic_eval_batch_041",
        "evaluator_id": SEM_EQ,
        "model_id": "provider/model",
        "model_version": "2026-07-01",
        "configuration_digest": _digest(f"{SEM_EQ}:config"),
        "source_commit": COMMIT_42,
        "input_digests": [_digest("cell:cell_001"), _digest("cell:cell_002"),
                          _digest("cell:cell_003")],
        "visibility_policy": "policy:internal_full",
        "authorization_policy": "policy:internal_authorized",
        "leakage_policy": "policy:internal_standard",
        "assessment_policy": "policy:internal_assessment",
        "output_schema": "object:sha256:" + "cd" * 32,
        "result_object": assessment_relation_digest(
            {"schema": ASSESSMENT_SCHEMA, "tuples": ASSESSMENT_TUPLES}),
        "created_by": "agent:semantic_matcher_001",
    },
}

Q_GOLD_009 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QGOLD-009",
    "description": "Materialized semantic assessment queried as ordinary data.",
    "sources": {"assessments": ASSESSMENT_SOURCE},
    "nodes": [
        {"id": "ra", "op": "read", "source": "assessments"},
        {"id": "f", "op": "filter", "input": "ra",
         "predicate": {"terms": [{"field": "label", "op": "eq",
                                  "value": "equivalent"}]}},
    ],
    "root": "f",
    "extensions": [MATERIALIZED],
}

EXPECTED_GOLD_009 = {
    "guarantee": "exact",
    "lower": sorted(ASSESSMENT_TUPLES, key=lambda t: json.dumps(t, sort_keys=True)),
    "upper": sorted(ASSESSMENT_TUPLES, key=lambda t: json.dumps(t, sort_keys=True)),
    "may_be_empty_groups": [],
    "bound_rule": RULE_SELECT,
    "intervals": [],
}
# Only the two "equivalent" rows survive the filter.
EXPECTED_GOLD_009["lower"] = sorted(
    [t for t in ASSESSMENT_TUPLES if t[3] == "equivalent"],
    key=lambda t: json.dumps(t, sort_keys=True))
EXPECTED_GOLD_009["upper"] = EXPECTED_GOLD_009["lower"]

# ---------------------------------------------------------------------------
# QPATH-002: the semantic equality forgery (26.8, QINV-04)

QPATH_002 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-002",
    "description": "The semantic equality forgery: vector similarity is "
                   "substituted for exact `=`.",
    "sources": {"users": {"schema": USERS_SCHEMA,
                          "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    "nodes": [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "f", "op": "filter", "input": "ru",
         "predicate": {"terms": [{"field": "name", "op": "eq", "value": "alice",
                                  "evaluator": VECTOR_SIM}]}},
    ],
    "root": "f",
    "extensions": [BARRIER],
}

# ---------------------------------------------------------------------------
# QPATH-007: the duplicated stochastic call (26.4)

QPATH_007 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-007",
    "description": "The duplicated stochastic call: the optimizer "
                   "duplicates an inline stochastic evaluator.",
    "sources": {"users": {"schema": USERS_SCHEMA,
                          "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    "nodes": [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "e1", "op": "evaluate", "input": "ru", "evaluator": VECTOR_SIM,
         "mode": "heuristic",
         "evaluation_key": full_key(VECTOR_SIM, [_digest("users:1")])},
        {"id": "e2", "op": "evaluate", "input": "ru", "evaluator": VECTOR_SIM,
         "mode": "heuristic",
         "evaluation_key": full_key(VECTOR_SIM, [_digest("users:1")])},
        {"id": "j", "op": "join", "left": "e1", "right": "e2",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
    ],
    "root": "j",
    "extensions": [BARRIER],
    "required_dimensions": ["value", "evaluation_identity"],
}

# ---------------------------------------------------------------------------
# QPATH-020: the heuristic resurrection (13.7.1, 26.6)

QPATH_020 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-020",
    "description": "The heuristic resurrection: heuristic semantic "
                   "membership passes through a join and the output is "
                   "labeled exact.",
    "sources": {"users": USERS_EXACT, "orders": ORDERS_EXACT},
    "nodes": [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "ro", "op": "read", "source": "orders"},
        {"id": "e", "op": "evaluate", "input": "ru",
         "evaluator": "sol:evaluator/positive_classifier/v1", "mode": "heuristic"},
        {"id": "j", "op": "join", "left": "e", "right": "ro",
         "join_type": "inner", "on": [{"left": "id", "right": "user_id"}]},
    ],
    "root": "j",
    "extensions": [BARRIER],
}

ORDERS_SCHEMA = [
    {"name": "user_id", "type": "i64", "nullable": False},
    {"name": "amount", "type": "i64", "nullable": False},
]

JOIN_FIELDS = USERS_SCHEMA + ORDERS_SCHEMA

# The defective claim: the join output is labeled exact with L = U.
# The heuristic evaluator (node:e) contributes to the certified side;
# no normative or registered rule licenses a heuristic contribution to
# an exact side (QV5-08).
CLAIM_020 = bound(
    "exact",
    rel(JOIN_FIELDS, [[1, "a", 1, 10], [1, "a", 1, 40], [2, "b", 2, 20]]),
    rel(JOIN_FIELDS, [[1, "a", 1, 10], [1, "a", 1, 40], [2, "b", 2, 20]]),
    provenance("tuple", [],
               derivation(RULE_JOIN, ["source:users", "source:orders"],
                          ["sol:evaluator/positive_classifier/v1"])),
    RULE_JOIN,
    assurance("contract_asserted", ["source:users", "source:orders"],
              ["source:users", "source:orders", RULE_JOIN]),
)

# ---------------------------------------------------------------------------
# QPATH-024: the transient memo (26.5, QINV-13)

QPATH_024 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-024",
    "description": "The transient memo: the evaluator is declared "
                   "deterministic-per-key, but repeated calls may "
                   "recompute different results after cache eviction.",
    "sources": {"users": {"schema": USERS_SCHEMA,
                          "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    "nodes": [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "e", "op": "evaluate", "input": "ru", "evaluator": SEM_EQ,
         "mode": "heuristic",
         "evaluation_key": full_key(SEM_EQ, [_digest("users:1")], transient=True)},
    ],
    "root": "e",
    "extensions": [BARRIER],
}

# ---------------------------------------------------------------------------
# QPATH-025: the incomplete evaluation key (26.5, Q15)

QPATH_025 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-025",
    "description": "The incomplete evaluation key: the prompt-template "
                   "digest is omitted from a semantic evaluator key.",
    "sources": {"users": {"schema": USERS_SCHEMA,
                          "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    "nodes": [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "e", "op": "evaluate", "input": "ru", "evaluator": SEM_EQ,
         "mode": "heuristic",
         "evaluation_key": {k: v for k, v in
                            full_key(SEM_EQ, [_digest("users:1")]).items()
                            if k != "prompt_template_digest"}},
    ],
    "root": "e",
    "extensions": [BARRIER],
}

# ---------------------------------------------------------------------------
# QPATH-033: the hidden heuristic view (28.5)

QPATH_033 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-033",
    "description": "The hidden heuristic view: a materialized view was "
                   "produced heuristically but substituted into an exact "
                   "query.",
    "sources": {"a": A},
    "nodes": [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "f", "op": "filter", "input": "ra",
         "predicate": {"terms": [{"field": "tag", "op": "eq", "value": "y"}]}},
    ],
    "root": "f",
}

REWRITE_033 = {
    "rule_id": SUBST_RULE,
    "location": "node:f",
    "covering_proof": heuristic_covering_proof_digest(),
    "source_commit": source_manifest({"sources": {"a": A}})["manifest_digest"],
}

# ---------------------------------------------------------------------------
# QPATH-040: the fabricated selector (13.7.1, 26.6)

QPATH_040 = {
    "schema_version": "qry.query.v0.3",
    "query_id": "QPATH-040",
    "description": "The fabricated selector: a tuple-generating LLM "
                   "operator is modeled as Select and inherits the input "
                   "relation as an upper bound.",
    "sources": {"users": {"schema": USERS_SCHEMA,
                          "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    "nodes": [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "e", "op": "evaluate", "input": "ru", "evaluator": TUPLE_GEN,
         "mode": "heuristic",
         "evaluation_key": full_key(TUPLE_GEN, [_digest("users:1")])},
    ],
    "root": "e",
    "extensions": [BARRIER],
}

# The defective claim: the planner inherits the input relation as the
# upper bound (the structural containment a tuple-generating evaluator
# cannot certify).
CLAIM_040 = bound(
    "bounded",
    rel(USERS_SCHEMA, []),
    rel(USERS_SCHEMA, [[1, "a"], [2, "b"], [3, "c"]]),
    provenance("tuple", [],
               derivation(RULE_STRUCTURAL, ["source:users"],
                          [TUPLE_GEN])),
    RULE_STRUCTURAL,
    assurance("contract_asserted", ["source:users"],
              ["source:users", RULE_STRUCTURAL]),
)

# ---------------------------------------------------------------------------
# Writing

def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    path.chmod(0o644)


def write_case(case_dir: Path, case_id: str, description: str, expected: list,
               query: dict, extra: dict | None = None) -> None:
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    write_json(case_dir / "query.json", query)
    manifest = {"case_id": case_id, "description": description,
                "expected_diagnostics": expected}
    if extra:
        manifest.update(extra["manifest"])
        for name, obj in extra["files"].items():
            write_json(case_dir / name, obj)
    write_json(case_dir / "manifest.json", manifest)
    (case_dir / "README.md").write_text(
        f"# {case_id}\n\n{description}\n\n"
        f"Expected diagnostics: {', '.join(expected) if expected else 'none (clean case)'}.\n"
    )
    (case_dir / "README.md").chmod(0o644)
    print(f"wrote {case_id}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir", nargs="?", default="corpus")
    args = ap.parse_args(argv)
    cases_dir = Path(args.corpus_dir) / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    # QGOLD-009: clean; the claim is the certified inference.
    inference = infer_certified(Q_GOLD_009)
    cb = inference[Q_GOLD_009["root"]]
    got = {
        "guarantee": cb.guarantee,
        "lower": sorted(list(t) for t in cb.lower.tuples),
        "upper": sorted(list(t) for t in cb.upper.tuples),
        "may_be_empty_groups": sorted(list(g) for g in cb.may_be_empty_groups),
        "bound_rule": cb.bound_rule,
        "intervals": sorted(json.dumps(dict(iv), sort_keys=True)
                            for iv in cb.intervals),
    }
    want = {k: v for k, v in EXPECTED_GOLD_009.items()}
    assert got == want, f"QGOLD-009: inferred core {got} != expected {want}"
    write_case(cases_dir / "QGOLD-009", "QGOLD-009", Q_GOLD_009["description"],
               [], Q_GOLD_009,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": {
                          "schema_version": "qry.bounds.v0.3",
                          "query_id": "QGOLD-009",
                          "root": Q_GOLD_009["root"],
                          "root_bound": cb.to_json(),
                      }}})

    # Plan-shape pathologies (the semantic layer fires before bound
    # validation, so no expected_bounds.json is needed).
    write_case(cases_dir / "QPATH-002", "QPATH-002", QPATH_002["description"],
               ["QINV-04", "QV6-04"], QPATH_002)
    write_case(cases_dir / "QPATH-007", "QPATH-007", QPATH_007["description"],
               ["QV6-05", "QV7-03"], QPATH_007)
    write_case(cases_dir / "QPATH-024", "QPATH-024", QPATH_024["description"],
               ["QINV-13", "QV6-03"], QPATH_024)
    write_case(cases_dir / "QPATH-025", "QPATH-025", QPATH_025["description"],
               ["QV6-03"], QPATH_025)

    # Defective-claim pathologies.
    write_case(cases_dir / "QPATH-020", "QPATH-020", QPATH_020["description"],
               ["QV5-08"], QPATH_020,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": {
                          "schema_version": "qry.bounds.v0.3",
                          "query_id": "QPATH-020",
                          "root": QPATH_020["root"],
                          "root_bound": CLAIM_020,
                      }}})
    write_case(cases_dir / "QPATH-040", "QPATH-040", QPATH_040["description"],
               ["QV5-09", "QV6-07"], QPATH_040,
               extra={"manifest": {},
                      "files": {"expected_bounds.json": {
                          "schema_version": "qry.bounds.v0.3",
                          "query_id": "QPATH-040",
                          "root": QPATH_040["root"],
                          "root_bound": CLAIM_040,
                      }}})

    # QPATH-033: rewrite case with the committed heuristic covering proof.
    write_case(cases_dir / "QPATH-033", "QPATH-033", QPATH_033["description"],
               ["QV8-02"], QPATH_033,
               extra={"manifest": {},
                      "files": {"rewrite.json": REWRITE_033,
                                "expected.json": {"applied": False}}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
