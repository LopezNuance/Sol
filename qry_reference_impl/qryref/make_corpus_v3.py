"""Generate the v0.3 certified-bounds corpus cases (Phase 1 of the
implementation plan): QGOLD-013..016, QGOLD-019, QGOLD-020 and
QPATH-031, QPATH-037, QPATH-038, QPATH-042.

Golden cases are written from the certified inference and asserted
against hand-computed expectations (spec sections 13.7.1, 13.8, 13.14).
Pathological cases carry hand-crafted defective bound claims that the
validator must flag (13.19).
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .certified import (
    RULE_AVG,
    RULE_DIFFERENCE,
    RULE_INTERSECT,
    RULE_RELATION,
    RULE_STRUCTURAL,
    infer_certified,
)

USERS_SCHEMA = [
    {"name": "id", "type": "i64", "nullable": False},
    {"name": "name", "type": "string", "nullable": False},
]
VALS_SCHEMA = [{"name": "v", "type": "i64", "nullable": False}]
AMOUNTS_SCHEMA = [
    {"name": "user_id", "type": "i64", "nullable": False},
    {"name": "amount", "type": "decimal", "nullable": False},
]

SELECT_CERTIFIED = "sol:bound/select_certified/v1"


def q3(case_id: str, description: str, sources: dict, nodes: list, root: str,
       stale: list | None = None, extensions: list | None = None) -> dict:
    query = {
        "schema_version": "qry.query.v0.3",
        "query_id": case_id,
        "description": description,
        "sources": sources,
        "nodes": nodes,
        "root": root,
    }
    if stale:
        query["stale_dependencies"] = stale
    if extensions:
        query["extensions"] = extensions
    return query


def rel(fields: list, tuples: list) -> dict:
    return {"fields": fields, "tuples": tuples}


def provenance(mode="tuple", members=None, derivation=None) -> dict:
    return {
        "lower_membership_mode": mode,
        "lower_memberships": members or [],
        "upper_derivation": derivation,
    }


def derivation(rule_id: str, sources: list, evaluators: list | None = None) -> dict:
    return {
        "rule_id": rule_id,
        "input_relations": [],
        "sources": sources,
        "evaluators": evaluators or [],
        "rewrites": [],
        "view_substitutions": [],
    }


def assurance(status="contract_asserted", evidence=None, depends_on=None, stale=False) -> dict:
    return {
        "status": status,
        "evidence": evidence or [],
        "depends_on": depends_on or [],
        "stale": stale,
    }


def bound(guarantee, lower, upper, prov, rule, assurance_rec=None, may_empty=None) -> dict:
    return {
        "guarantee": guarantee,
        "lower": lower,
        "upper": upper,
        "lower_object": None,
        "upper_object": None,
        "result_object": None,
        "assurance": assurance_rec or assurance(),
        "provenance": prov,
        "may_be_empty_groups": may_empty or [],
        "bound_rule": rule,
        "order": [],
    }


# ---------------------------------------------------------------------------
# Queries

Q_GOLD_013 = q3(
    "QGOLD-013",
    "Heuristic tuple-preserving semantic filter over exact input: lower = typed empty, upper = input (13.7.1).",
    {"users": {"schema": USERS_SCHEMA, "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    [
        {"id": "u", "op": "read", "source": "users"},
        {"id": "e1", "op": "evaluate", "input": "u", "evaluator": "sol:evaluator/positive_classifier/v1", "mode": "heuristic"},
    ],
    "e1",
    extensions=["urn:qry:v0.3:semantic-evaluator-barrier"],
)

Q_GOLD_014 = q3(
    "QGOLD-014",
    "Semantic filter with certified positive classifications: lower = positives, upper = input (13.7.1).",
    {"users": {"schema": USERS_SCHEMA, "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
    [
        {"id": "u", "op": "read", "source": "users"},
        {"id": "e1", "op": "evaluate", "input": "u", "evaluator": "sol:evaluator/positive_classifier/v1",
         "mode": "sound_positive", "positives": [[1, "a"], [3, "c"]]},
    ],
    "e1",
    extensions=["urn:qry:v0.3:semantic-evaluator-barrier"],
)

GHOST_SOURCES = {
    "users": {"schema": USERS_SCHEMA, "tuples": [[1, "a"], [2, "b"]]},
    "ghosts": {"schema": USERS_SCHEMA},
}

Q_GOLD_015 = q3(
    "QGOLD-015",
    "Intersection with one heuristic operand retains the certified upper of the other operand (13.7.1, 13.17).",
    GHOST_SOURCES,
    [
        {"id": "a", "op": "read", "source": "users"},
        {"id": "b", "op": "read", "source": "ghosts"},
        {"id": "i1", "op": "intersect", "inputs": ["a", "b"]},
    ],
    "i1",
)

Q_GOLD_016 = q3(
    "QGOLD-016",
    "Difference with a heuristic right operand retains the certified upper of the left operand; typed empty lower (13.8).",
    GHOST_SOURCES,
    [
        {"id": "a", "op": "read", "source": "users"},
        {"id": "b", "op": "read", "source": "ghosts"},
        {"id": "d1", "op": "difference", "inputs": ["a", "b"]},
    ],
    "d1",
)

Q_GOLD_019 = q3(
    "QGOLD-019",
    "A tighter registered bound than the normative baseline is accepted (13.18).",
    {"vals": {"schema": VALS_SCHEMA, "tuples": [[1], [2], [3], [4]]}},
    [
        {"id": "v", "op": "read", "source": "vals"},
        {"id": "f1", "op": "filter", "input": "v", "predicate": {"min_selectivity": 0.0, "max_selectivity": 1.0}},
    ],
    "f1",
)

AVG_SOURCES = {
    "amounts": {
        "schema": AMOUNTS_SCHEMA,
        "lower": {"tuples": [[1, 5]]},
        "upper": {"tuples": [[1, 5], [1, 16], [1, 6], [2, 7]]},
    }
}

AVG_NODES = [
    {"id": "a", "op": "read", "source": "amounts"},
    {"id": "g1", "op": "aggregate", "input": "a", "group_by": ["user_id"],
     "aggregates": [{"name": "avg_amount", "func": "avg", "field": "amount", "type": "decimal"}]},
]

Q_GOLD_020 = q3(
    "QGOLD-020",
    "sol:bound/avg_optional_prefix/v1 returns a certified interval and records possible emptiness when lower is empty (13.14).",
    AVG_SOURCES,
    AVG_NODES,
    "g1",
)

QPATH_031 = q3(
    "QPATH-031",
    "The inverted bounds: lower relation contains a tuple absent from the upper relation.",
    {"vals": {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [2]]}, "upper": {"tuples": [[1]]}}},
    [{"id": "v", "op": "read", "source": "vals"}],
    "v",
)

BOUNDED_USERS = {
    "users": {
        "schema": USERS_SCHEMA,
        "lower": {"tuples": [[1, "a"]]},
        "upper": {"tuples": [[1, "a"], [2, "b"]]},
    }
}

QPATH_037 = q3(
    "QPATH-037",
    "The possible-as-proven tuple: a tuple occurring only in U is given ordinary why-provenance asserting exact-answer membership.",
    BOUNDED_USERS,
    [{"id": "u", "op": "read", "source": "users"}],
    "u",
)

QPATH_038 = q3(
    "QPATH-038",
    "The missing upper derivation: a bounded result has an upper object but no transfer rule or source-bound provenance.",
    BOUNDED_USERS,
    [{"id": "u", "op": "read", "source": "users"}],
    "u",
)

QPATH_042 = q3(
    "QPATH-042",
    "The invalid AVG prefix: the AVG interval omits an extremal optional prefix and excludes a feasible mean.",
    AVG_SOURCES,
    AVG_NODES,
    "g1",
)


# ---------------------------------------------------------------------------
# Hand-computed expectations (spec-derived, not implementation-derived)

def core_of(cb) -> dict:
    return {
        "guarantee": cb.guarantee,
        "lower": sorted(list(t) for t in cb.lower.tuples) if cb.lower is not None else None,
        "upper": sorted(list(t) for t in cb.upper.tuples) if cb.upper is not None else None,
        "may_be_empty_groups": sorted(list(g) for g in cb.may_be_empty_groups),
        "bound_rule": cb.bound_rule,
        "intervals": sorted(json.dumps(dict(iv), sort_keys=True) for iv in cb.intervals),
    }


EXPECTED_CORES = {
    "QGOLD-013": {
        "guarantee": "bounded",
        "lower": [],
        "upper": [[1, "a"], [2, "b"], [3, "c"]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_STRUCTURAL,
        "intervals": [],
    },
    "QGOLD-014": {
        "guarantee": "bounded",
        "lower": [[1, "a"], [3, "c"]],
        "upper": [[1, "a"], [2, "b"], [3, "c"]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_STRUCTURAL,
        "intervals": [],
    },
    "QGOLD-015": {
        "guarantee": "upper_bound",
        "lower": None,
        "upper": [[1, "a"], [2, "b"]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_INTERSECT,
        "intervals": [],
    },
    "QGOLD-016": {
        "guarantee": "bounded",
        "lower": [],
        "upper": [[1, "a"], [2, "b"]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_DIFFERENCE,
        "intervals": [],
    },
    # QGOLD-019: the claim is a registered tighter bound, not the baseline.
    "QGOLD-019": {
        "guarantee": "bounded",
        "lower": [[2], [4]],
        "upper": [[2], [3], [4]],
        "may_be_empty_groups": [],
        "bound_rule": SELECT_CERTIFIED,
        "intervals": [],
    },
    "QGOLD-020": {
        "guarantee": "bounded",
        "lower": [[1]],
        "upper": [[1], [2]],
        "may_be_empty_groups": [[2]],
        "bound_rule": RULE_AVG,
        "intervals": [
            json.dumps({"field": "avg_amount", "group": [1], "lower": "5/1", "upper": "21/2", "may_be_empty": False}, sort_keys=True),
            json.dumps({"field": "avg_amount", "group": [2], "lower": "7/1", "upper": "7/1", "may_be_empty": True}, sort_keys=True),
        ],
    },
}

# ---------------------------------------------------------------------------
# Claims (pathological cases carry defective claims)

def claim_019() -> dict:
    return bound(
        "bounded",
        rel(VALS_SCHEMA, [[2], [4]]),
        rel(VALS_SCHEMA, [[2], [3], [4]]),
        provenance(
            "tuple",
            [
                {"tuple": [2], "mode": "tuple", "cites": ["record:verification_001"]},
                {"tuple": [4], "mode": "tuple", "cites": ["record:verification_001"]},
            ],
            derivation(SELECT_CERTIFIED, ["source:vals"]),
        ),
        SELECT_CERTIFIED,
        assurance("contract_asserted", ["record:verification_001"], ["source:vals", SELECT_CERTIFIED]),
    )


def claim_031() -> dict:
    return bound(
        "bounded",
        rel(VALS_SCHEMA, [[1], [2]]),
        rel(VALS_SCHEMA, [[1]]),
        provenance("tuple", [], derivation(RULE_RELATION, ["source:vals"])),
        RULE_RELATION,
        assurance("contract_asserted", ["source:vals"], ["source:vals", RULE_RELATION]),
    )


def claim_037() -> dict:
    return bound(
        "bounded",
        rel(USERS_SCHEMA, [[1, "a"]]),
        rel(USERS_SCHEMA, [[1, "a"], [2, "b"]]),
        provenance(
            "why",
            [
                {"tuple": [1, "a"], "mode": "why", "cites": ["record:verification_001"]},
                {"tuple": [2, "b"], "mode": "why", "cites": ["record:verification_001"]},
            ],
            derivation(RULE_RELATION, ["source:users"]),
        ),
        RULE_RELATION,
        assurance("contract_asserted", ["record:verification_001"], ["source:users", RULE_RELATION]),
    )


def claim_038() -> dict:
    return bound(
        "bounded",
        rel(USERS_SCHEMA, [[1, "a"]]),
        rel(USERS_SCHEMA, [[1, "a"], [2, "b"]]),
        provenance("tuple", [], None),
        RULE_RELATION,
        assurance("contract_asserted", ["source:users"], ["source:users", RULE_RELATION]),
    )


GROUP_SCHEMA = [{"name": "user_id", "type": "i64", "nullable": False}]


def claim_042() -> dict:
    # Group 1 interval computed over k in [1..2], omitting the k=0 extremal
    # prefix: min 11/2 instead of the certified 5/1.
    b = bound(
        "bounded",
        rel(GROUP_SCHEMA, [[1], [2]]),
        rel(GROUP_SCHEMA, [[1], [2]]),
        provenance("tuple", [], derivation(RULE_AVG, ["source:amounts"])),
        RULE_AVG,
        assurance("contract_asserted", ["source:amounts"], ["source:amounts", RULE_AVG]),
        may_empty=[[2]],
    )
    b["intervals"] = [
        {"field": "avg_amount", "group": [1], "lower": "11/2", "upper": "21/2", "may_be_empty": False},
        {"field": "avg_amount", "group": [2], "lower": "7/1", "upper": "7/1", "may_be_empty": True},
    ]
    return b


CASES = [
    # (case_id, query, expected_diagnostics, claim_builder or None)
    ("QGOLD-013", Q_GOLD_013, [], None),
    ("QGOLD-014", Q_GOLD_014, [], None),
    ("QGOLD-015", Q_GOLD_015, [], None),
    ("QGOLD-016", Q_GOLD_016, [], None),
    ("QGOLD-019", Q_GOLD_019, [], claim_019),
    ("QGOLD-020", Q_GOLD_020, [], None),
    ("QPATH-031", QPATH_031, ["QV5-01"], claim_031),
    ("QPATH-037", QPATH_037, ["QINV-14", "QV8-07"], claim_037),
    ("QPATH-038", QPATH_038, ["QV8-06"], claim_038),
    ("QPATH-042", QPATH_042, ["QV5-12"], claim_042),
]


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir", nargs="?", default="corpus")
    args = ap.parse_args(argv)
    cases_dir = Path(args.corpus_dir) / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    for case_id, query, expected, claim_builder in CASES:
        case_dir = cases_dir / case_id
        if case_dir.exists():
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True)
        write_json(case_dir / "query.json", query)
        write_json(case_dir / "manifest.json", {
            "case_id": case_id,
            "description": query["description"],
            "expected_diagnostics": expected,
        })

        if claim_builder is not None:
            claim = claim_builder()
            # For QGOLD-019 the claim must still equal the hand-computed core.
            if case_id in EXPECTED_CORES:
                got = {
                    "guarantee": claim["guarantee"],
                    "lower": sorted(claim["lower"]["tuples"]) if claim["lower"] else None,
                    "upper": sorted(claim["upper"]["tuples"]) if claim["upper"] else None,
                    "may_be_empty_groups": sorted(claim["may_be_empty_groups"]),
                    "bound_rule": claim["bound_rule"],
                    "intervals": sorted(json.dumps(dict(iv), sort_keys=True) for iv in claim.get("intervals", [])),
                }
                want = EXPECTED_CORES[case_id]
                assert got == want, f"{case_id}: claim core {got} != expected {want}"
            write_json(case_dir / "expected_bounds.json", {
                "schema_version": "qry.bounds.v0.3",
                "query_id": case_id,
                "root": query["root"],
                "root_bound": claim,
            })
        else:
            inference = infer_certified(query)
            cb = inference[query["root"]]
            got = core_of(cb)
            want = EXPECTED_CORES[case_id]
            assert got == want, f"{case_id}: inferred core {got} != expected {want}"
            write_json(case_dir / "expected_bounds.json", {
                "schema_version": "qry.bounds.v0.3",
                "query_id": case_id,
                "root": query["root"],
                "root_bound": cb.to_json(),
            })

        (case_dir / "README.md").write_text(
            f"# {case_id}\n\n{query['description']}\n\n"
            f"Expected diagnostics: {', '.join(expected) if expected else 'none (clean case)'}.\n"
        )
        print(f"wrote {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
