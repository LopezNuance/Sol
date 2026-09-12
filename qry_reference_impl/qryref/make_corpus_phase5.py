"""Generate the Phase 5 normative corpus cases (spec 36.1/36.2, 37.5).

Adds the 27 normative QGOLD/QPATH cases that the v0.3 kernel can evidence
now:

* certified-bound goldens (QGOLD-002/003/004/006/007/008/017/018):
  written from the certified inference and asserted against
  hand-computed expectations (spec 13);
* execution-record cases (QGOLD-001/012, QPATH-012/035): real
  exact-evaluator runs over the committed GOLD-01 artifact (spec 30),
  including the QV5-07 truncation-labeled-exact pathology and the
  QRY-EXEC-002 continuation-drift pathology;
* the QV8-03 stale-materialized-view rewrite case (QPATH-008);
* the plan-shape and claim-based rule pathologies (QPATH-001/003/004/006/
  009/010/011/015/016/017/018/019/030/032).

The remaining 16 normative cases are blocked by later phases (6, 7, 8)
and are documented in docs/qry/2026-09-10-phase5-corpus-gap.md, not
shipped as failing case directories (ground rule: green at every phase
boundary).
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .canonical import source_manifest
from .certified import (
    RULE_AVG,
    RULE_DIFFERENCE,
    RULE_JOIN,
    RULE_LIMIT,
    RULE_LFP,
    RULE_RELATION,
    RULE_UNION,
    RULE_COUNT_SET,
    infer_certified,
)
from .exact import artifact_tree_digest, execute_step, scan_artifact_relation
from .make_corpus_v3 import (
    AVG_NODES,
    AVG_SOURCES,
    GROUP_SCHEMA,
    USERS_SCHEMA,
    VALS_SCHEMA,
    assurance,
    bound,
    derivation,
    provenance,
    q3,
    rel,
)
from .make_rewrites_corpus import A, B, SUBST_RULE, covering_proof_digest
from .record_runs import CENSUS_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CASES = ROOT / "corpus" / "cases"

ORDERS_SCHEMA = [
    {"name": "user_id", "type": "i64", "nullable": False},
    {"name": "amount", "type": "i64", "nullable": False},
]
EDGES_SCHEMA = [
    {"name": "src", "type": "i64", "nullable": False},
    {"name": "dst", "type": "i64", "nullable": False},
]

# ---------------------------------------------------------------------------
# Sources

USERS_EXACT = {"schema": USERS_SCHEMA, "tuples": [[1, "a"], [2, "b"], [3, "c"]]}
ORDERS_EXACT = {"schema": ORDERS_SCHEMA,
                "tuples": [[1, 10], [2, 20], [3, 30], [1, 40]]}
ROOTS = {"schema": VALS_SCHEMA, "tuples": [[1]]}
EDGES_EXACT = {"schema": EDGES_SCHEMA,
               "tuples": [[1, 2], [2, 3], [3, 4], [1, 5], [5, 6]]}
USERS_BOUNDED = {"schema": USERS_SCHEMA,
                 "lower": {"tuples": [[1, "a"]]},
                 "upper": {"tuples": [[1, "a"], [2, "b"]]}}
REMOVED_EXACT = {"schema": USERS_SCHEMA, "tuples": [[2, "b"]]}
UNION_A = {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [3]]},
           "upper": {"tuples": [[1], [2], [3]]}}
UNION_B = {"schema": VALS_SCHEMA, "lower": {"tuples": [[3]]},
           "upper": {"tuples": [[3], [4]]}}
DIFF_A = {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [2]]},
          "upper": {"tuples": [[1], [2], [3]]}}
DIFF_B = {"schema": VALS_SCHEMA, "lower": {"tuples": [[2]]},
          "upper": {"tuples": [[2], [3]]}}
COUNT_VALS = {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [2]]},
              "upper": {"tuples": [[1], [2], [3]]}}
EDGES_BOUNDED = {"schema": EDGES_SCHEMA,
                 "lower": {"tuples": [[1, 2], [2, 3]]},
                 "upper": {"tuples": [[1, 2], [2, 3], [3, 4], [1, 5], [5, 6]]}}
ALL_USERS = {"schema": VALS_SCHEMA,
             "tuples": [[1], [2], [3], [4], [5], [6], [7], [8]]}

# ---------------------------------------------------------------------------
# Queries

Q_GOLD_002 = q3(
    "QGOLD-002",
    "Exact join with tuple provenance.",
    {"users": USERS_EXACT, "orders": ORDERS_EXACT},
    [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "ro", "op": "read", "source": "orders"},
        {"id": "j", "op": "join", "left": "ru", "right": "ro", "join_type": "inner",
         "on": [{"left": "id", "right": "user_id"}]},
    ],
    "j",
)

Q_GOLD_003 = q3(
    "QGOLD-003",
    "Positive recursive dependency closure.",
    {"roots": ROOTS, "edges": EDGES_EXACT},
    [
        {"id": "rr", "op": "read", "source": "roots"},
        {"id": "re", "op": "read", "source": "edges"},
        {"id": "f", "op": "least_fixpoint", "seed": "rr", "edge": "re",
         "on": {"left": "src", "right": "dst"}},
    ],
    "f",
    extensions=["urn:qry:v0.3:positive-recursion"],
)

Q_GOLD_004 = q3(
    "QGOLD-004",
    "Stratified negation licensed by a local completeness assertion.",
    {"users": USERS_BOUNDED, "removed": REMOVED_EXACT},
    [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "rr", "op": "read", "source": "removed"},
        {"id": "d", "op": "difference", "inputs": ["ru", "rr"]},
    ],
    "d",
)

Q_GOLD_006 = q3(
    "QGOLD-006",
    "Bounded union with correctly propagated lower and upper relations.",
    {"a": UNION_A, "b": UNION_B},
    [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "u", "op": "union_distinct", "inputs": ["ra", "rb"]},
    ],
    "u",
)

Q_GOLD_007 = q3(
    "QGOLD-007",
    "Bounded difference using L1\\U2 and U1\\L2.",
    {"a": DIFF_A, "b": DIFF_B},
    [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "d", "op": "difference", "inputs": ["ra", "rb"]},
    ],
    "d",
)

Q_GOLD_008 = q3(
    "QGOLD-008",
    "COUNT_SET interval derived from relation bounds.",
    {"vals": COUNT_VALS},
    [
        {"id": "rv", "op": "read", "source": "vals"},
        {"id": "ag", "op": "aggregate", "input": "rv", "group_by": ["v"],
         "aggregates": [{"name": "c", "func": "count_set"}]},
    ],
    "ag",
)

Q_GOLD_017 = q3(
    "QGOLD-017",
    "Positive recursive lower and upper fixed points feed a stratified "
    "difference with correctly swapped negative sides.",
    {"roots": ROOTS, "edges": EDGES_BOUNDED, "all_users": ALL_USERS},
    [
        {"id": "rr", "op": "read", "source": "roots"},
        {"id": "re", "op": "read", "source": "edges"},
        {"id": "ru", "op": "read", "source": "all_users"},
        {"id": "f", "op": "least_fixpoint", "seed": "rr", "edge": "re",
         "on": {"left": "src", "right": "dst"}},
        {"id": "d", "op": "difference", "inputs": ["ru", "f"]},
    ],
    "d",
    extensions=["urn:qry:v0.3:positive-recursion"],
)

Q_GOLD_018 = q3(
    "QGOLD-018",
    "Bounded result carries membership provenance for lower tuples and "
    "bound-derivation provenance for the upper relation.",
    {"users": USERS_BOUNDED},
    [{"id": "ru", "op": "read", "source": "users"}],
    "ru",
)

QPATH_001 = q3(
    "QPATH-001",
    "The moving branch: query begins on branch main but records no resolved commit.",
    {"users": {"schema": USERS_SCHEMA, "branch": "main"}},
    [{"id": "ru", "op": "read", "source": "users"}],
    "ru",
)

QPATH_003 = q3(
    "QPATH-003",
    "The false exact result: approximate nearest-neighbor retrieval returns "
    "top-k rows labeled exact.",
    {"vals": {"schema": VALS_SCHEMA, "tuples": [[1], [2], [3]], "approximate": True}},
    [{"id": "rv", "op": "read", "source": "vals"}],
    "rv",
)

QPATH_004 = q3(
    "QPATH-004",
    "The open-world negation: exact NOT EXISTS is used against externally "
    "incomplete evidence.",
    {"left": {"schema": VALS_SCHEMA, "tuples": [[1], [2], [3]]},
     "right": {"schema": VALS_SCHEMA}},
    [
        {"id": "rl", "op": "read", "source": "left"},
        {"id": "rr", "op": "read", "source": "right"},
        {"id": "d", "op": "difference", "inputs": ["rl", "rr"]},
    ],
    "d",
)

QPATH_006 = q3(
    "QPATH-006",
    "The unordered top ten: LIMIT 10 is committed without deterministic ordering.",
    {"vals": {"schema": VALS_SCHEMA, "tuples": [[1], [2], [3], [4]]}},
    [
        {"id": "rv", "op": "read", "source": "vals"},
        {"id": "l", "op": "limit", "input": "rv", "limit": 10},
    ],
    "l",
)

QPATH_009 = q3(
    "QPATH-009",
    "The truth-status collapse: verification = unverified is rewritten as "
    "proposition = false.",
    {"tasks": {"schema": [
        {"name": "id", "type": "i64", "nullable": False},
        {"name": "verification", "type": "bool", "nullable": False,
         "kind": "truth_status"},
    ], "tuples": [[1, True], [2, False]]}},
    [
        {"id": "rt", "op": "read", "source": "tasks"},
        {"id": "f", "op": "filter", "input": "rt",
         "predicate": {"terms": [{"field": "verification", "op": "eq",
                                   "value": False}]}},
    ],
    "f",
)

OBJ_REF = "object:sha256:" + "ab" * 32

QPATH_010 = q3(
    "QPATH-010",
    "The unresolved object masquerade: a named output is compared directly "
    "to an immutable object reference.",
    {"users": {"schema": USERS_SCHEMA, "tuples": [[1, "a"], [2, "b"]]}},
    [
        {"id": "ru", "op": "read", "source": "users"},
        {"id": "f", "op": "filter", "input": "ru",
         "predicate": {"terms": [{"field": "name", "op": "eq", "value": OBJ_REF}]}},
    ],
    "f",
)

QPATH_011 = q3(
    "QPATH-011",
    "The unsafe universe: query asks for every value that is not a claim.",
    {"universe": {"schema": VALS_SCHEMA, "unbounded": True},
     "claims": {"schema": VALS_SCHEMA, "tuples": [[1], [2]]}},
    [
        {"id": "ru", "op": "read", "source": "universe"},
        {"id": "rc", "op": "read", "source": "claims"},
        {"id": "d", "op": "difference", "inputs": ["ru", "rc"]},
    ],
    "d",
)

QPATH_015 = q3(
    "QPATH-015",
    "The bag-set confusion: projection under bag semantics is treated as "
    "duplicate-eliminating without an explicit Distinct.",
    {"vals": {"schema": VALS_SCHEMA, "tuples": [[1], [1], [2]], "bag": True}},
    [{"id": "rv", "op": "read", "source": "vals"}],
    "rv",
)

QPATH_016 = q3(
    "QPATH-016",
    "The invalid lower difference: LA EXCEPT LB is reported as a lower bound "
    "for A EXCEPT B.",
    {"a": {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [2], [3]]},
           "upper": {"tuples": [[1], [2], [3], [4]]}},
     "b": {"schema": VALS_SCHEMA, "lower": {"tuples": [[2]]},
           "upper": {"tuples": [[2], [3]]}}},
    [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "d", "op": "difference", "inputs": ["ra", "rb"]},
    ],
    "d",
)

QPATH_017 = q3(
    "QPATH-017",
    "The unswapped negation: complement uses D\\L as a lower bound instead "
    "of D\\U.",
    {"d": {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [2], [3]]},
           "upper": {"tuples": [[1], [2], [3], [4]]}},
     "l": {"schema": VALS_SCHEMA, "lower": {"tuples": [[3]]},
           "upper": {"tuples": [[2], [3]]}}},
    [
        {"id": "rd", "op": "read", "source": "d"},
        {"id": "rl", "op": "read", "source": "l"},
        {"id": "x", "op": "difference", "inputs": ["rd", "rl"]},
    ],
    "x",
)

QPATH_018 = q3(
    "QPATH-018",
    "The friendly-label planner: planner composes lower_bound and upper_bound "
    "labels without concrete bound relations.",
    {"vals": {"schema": VALS_SCHEMA, "tuples": [[1], [2], [3]]}},
    [{"id": "rv", "op": "read", "source": "vals"}],
    "rv",
)

QPATH_019 = q3(
    "QPATH-019",
    "The average fiction: AVG over an inexact relation is labeled with a "
    "scalar lower_bound without a registered interval rule.",
    AVG_SOURCES,
    AVG_NODES,
    "g1",
)

COMMIT_A = "object:sha256:" + "aa" * 32
COMMIT_B = "object:sha256:" + "bb" * 32

QPATH_030 = q3(
    "QPATH-030",
    "The mismatched bounds: lower and upper relations come from different commits.",
    {"users": {"schema": USERS_SCHEMA,
               "lower": {"tuples": [[1, "a"]], "commit": COMMIT_A},
               "upper": {"tuples": [[1, "a"], [2, "b"]], "commit": COMMIT_B}}},
    [{"id": "ru", "op": "read", "source": "users"}],
    "ru",
)

QPATH_032 = q3(
    "QPATH-032",
    "The top-k certainty illusion: an upper-bounded input is sorted and "
    "limited without a position-certainty rule.",
    {"vals": {"schema": VALS_SCHEMA, "lower": {"tuples": [[1], [2], [3]]},
              "upper": {"tuples": [[1], [2], [3], [4]]}}},
    [
        {"id": "rv", "op": "read", "source": "vals"},
        {"id": "s", "op": "sort", "input": "rv", "by": ["v"]},
        {"id": "l", "op": "limit", "input": "s", "limit": 2},
    ],
    "l",
)

QPATH_008 = q3(
    "QPATH-008",
    "The stale materialized view: a view from commit 41 answers a query "
    "pinned to commit 42.",
    {"b": B},
    [
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "f", "op": "filter", "input": "rb",
         "predicate": {"terms": [{"field": "val", "op": "eq", "value": 20}]}},
    ],
    "f",
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
    "QGOLD-002": {
        "guarantee": "exact",
        "lower": [[1, "a", 1, 10], [1, "a", 1, 40], [2, "b", 2, 20], [3, "c", 3, 30]],
        "upper": [[1, "a", 1, 10], [1, "a", 1, 40], [2, "b", 2, 20], [3, "c", 3, 30]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_JOIN,
        "intervals": [],
    },
    "QGOLD-003": {
        "guarantee": "exact",
        "lower": [[1], [2], [3], [4], [5], [6]],
        "upper": [[1], [2], [3], [4], [5], [6]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_LFP,
        "intervals": [],
    },
    "QGOLD-004": {
        "guarantee": "exact",
        "lower": [[1, "a"]],
        "upper": [[1, "a"]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_DIFFERENCE,
        "intervals": [],
    },
    "QGOLD-006": {
        "guarantee": "bounded",
        "lower": [[1], [3]],
        "upper": [[1], [2], [3], [4]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_UNION,
        "intervals": [],
    },
    "QGOLD-007": {
        "guarantee": "bounded",
        "lower": [[1]],
        "upper": [[1], [3]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_DIFFERENCE,
        "intervals": [],
    },
    "QGOLD-008": {
        "guarantee": "bounded",
        "lower": [[1], [2]],
        "upper": [[1], [2], [3]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_COUNT_SET,
        "intervals": [
            json.dumps({"field": "c", "group": [1], "lower": 1, "upper": 1,
                        "may_be_empty": False}, sort_keys=True),
            json.dumps({"field": "c", "group": [2], "lower": 1, "upper": 1,
                        "may_be_empty": False}, sort_keys=True),
            json.dumps({"field": "c", "group": [3], "lower": 0, "upper": 1,
                        "may_be_empty": False}, sort_keys=True),
        ],
    },
    "QGOLD-017": {
        "guarantee": "bounded",
        "lower": [[7], [8]],
        "upper": [[4], [5], [6], [7], [8]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_DIFFERENCE,
        "intervals": [],
    },
    "QGOLD-018": {
        "guarantee": "bounded",
        "lower": [[1, "a"]],
        "upper": [[1, "a"], [2, "b"]],
        "may_be_empty_groups": [],
        "bound_rule": RULE_RELATION,
        "intervals": [],
    },
}

# ---------------------------------------------------------------------------
# Claims (pathological cases carry defective claims; QGOLD-018 carries an
# honest provenance claim)

def claim_003() -> dict:
    # Exact top-k over approximate retrieval, no certified derivation.
    return bound("exact", rel(VALS_SCHEMA, [[1], [2]]), rel(VALS_SCHEMA, [[1], [2]]),
                 provenance("tuple", [], None), None,
                 assurance("contract_asserted", [], []))


def claim_004() -> dict:
    # Exact negation over externally incomplete (unaudited) evidence.
    return bound("exact", rel(VALS_SCHEMA, [[1], [2], [3]]),
                 rel(VALS_SCHEMA, [[1], [2], [3]]),
                 provenance("tuple", [],
                            derivation(RULE_DIFFERENCE, ["source:left", "source:right"])),
                 RULE_DIFFERENCE,
                 assurance("contract_asserted", ["source:left", "source:right"],
                           ["source:left", "source:right", RULE_DIFFERENCE]))


def claim_006() -> dict:
    # Committed limit over an unordered input.
    return bound("bounded", rel(VALS_SCHEMA, [[1], [2], [3], [4]]),
                 rel(VALS_SCHEMA, [[1], [2], [3], [4]]),
                 provenance("tuple", [], derivation(RULE_LIMIT, ["source:vals"])),
                 RULE_LIMIT,
                 assurance("contract_asserted", ["source:vals"],
                           ["source:vals", RULE_LIMIT]))


def claim_015() -> dict:
    # Set-semantics exact claim over a bag source, no Distinct.
    return bound("exact", rel(VALS_SCHEMA, [[1], [2]]), rel(VALS_SCHEMA, [[1], [2]]),
                 provenance("tuple", [], derivation(RULE_RELATION, ["source:vals"])),
                 RULE_RELATION,
                 assurance("contract_asserted", ["source:vals"],
                           ["source:vals", RULE_RELATION]))


def claim_016() -> dict:
    # Lower side computed as L1\L2 (wrong) instead of L1\U2.
    return bound("bounded", rel(VALS_SCHEMA, [[1], [3]]),
                 rel(VALS_SCHEMA, [[1], [3], [4]]),
                 provenance("tuple", [],
                            derivation(RULE_DIFFERENCE, ["source:a", "source:b"])),
                 RULE_DIFFERENCE,
                 assurance("contract_asserted", ["source:a", "source:b"],
                           ["source:a", "source:b", RULE_DIFFERENCE]))


def claim_017() -> dict:
    # Complement lower computed as D\L (wrong) instead of D\U.
    return bound("bounded", rel(VALS_SCHEMA, [[1], [2]]),
                 rel(VALS_SCHEMA, [[1], [2], [4]]),
                 provenance("tuple", [],
                            derivation(RULE_DIFFERENCE, ["source:d", "source:l"])),
                 RULE_DIFFERENCE,
                 assurance("contract_asserted", ["source:d", "source:l"],
                           ["source:d", "source:l", RULE_DIFFERENCE]))


def claim_018() -> dict:
    # Exact labels composed without any concrete bound relation.
    return bound("exact", None, None, provenance("none", [], None), None,
                 assurance("contract_asserted", [], []))


def claim_019() -> dict:
    # Scalar lower_bound over the inexact AVG, no certified intervals.
    return bound("lower_bound", rel(GROUP_SCHEMA, [[1], [2]]), None,
                 provenance("tuple", [], derivation(RULE_AVG, ["source:amounts"])),
                 RULE_AVG,
                 assurance("contract_asserted", ["source:amounts"],
                           ["source:amounts", RULE_AVG]))


def claim_032() -> dict:
    # Exact top-k over an upper-bounded (inexact) input.
    return bound("exact", rel(VALS_SCHEMA, [[1], [2]]), rel(VALS_SCHEMA, [[1], [2]]),
                 provenance("tuple", [], derivation(RULE_LIMIT, ["source:vals"])),
                 RULE_LIMIT,
                 assurance("contract_asserted", ["source:vals"],
                           ["source:vals", RULE_LIMIT]))


def claim_gold_018() -> dict:
    # Honest bounded claim: positive why-provenance for the lower tuple
    # only, and a transfer rule for the upper relation.
    return bound("bounded", rel(USERS_SCHEMA, [[1, "a"]]),
                 rel(USERS_SCHEMA, [[1, "a"], [2, "b"]]),
                 provenance("why",
                            [{"tuple": [1, "a"], "mode": "why",
                              "cites": ["source:users"]}],
                            derivation(RULE_RELATION, ["source:users"])),
                 RULE_RELATION,
                 assurance("contract_asserted", ["source:users"],
                           ["source:users", RULE_RELATION]))


CASES = [
    # (case_id, query, expected_diagnostics, claim_builder or None)
    ("QGOLD-002", Q_GOLD_002, [], None),
    ("QGOLD-003", Q_GOLD_003, [], None),
    ("QGOLD-004", Q_GOLD_004, [], None),
    ("QGOLD-006", Q_GOLD_006, [], None),
    ("QGOLD-007", Q_GOLD_007, [], None),
    ("QGOLD-008", Q_GOLD_008, [], None),
    ("QGOLD-017", Q_GOLD_017, [], None),
    ("QGOLD-018", Q_GOLD_018, [], claim_gold_018),
    ("QPATH-003", QPATH_003, ["QINV-06", "QV5-03", "QV8-06"], claim_003),
    ("QPATH-004", QPATH_004, ["QV4-02"], claim_004),
    ("QPATH-006", QPATH_006, ["QV3-04"], claim_006),
    ("QPATH-015", QPATH_015, ["QV3-02"], claim_015),
    ("QPATH-016", QPATH_016, ["QV4-04", "QV5-02"], claim_016),
    ("QPATH-017", QPATH_017, ["QV4-04", "QV5-02"], claim_017),
    ("QPATH-018", QPATH_018, ["QV5-02", "QV5-03"], claim_018),
    ("QPATH-019", QPATH_019, ["QV5-06", "QV5-12"], claim_019),
    ("QPATH-032", QPATH_032, ["QV3-05"], claim_032),
]

# Plan-shape pathologies: the semantic layer fires before bound validation,
# so no expected_bounds.json is needed.
SEMANTIC_CASES = [
    ("QPATH-001", QPATH_001, ["QV1-02", "QV1-03"]),
    ("QPATH-009", QPATH_009, ["QINV-05"]),
    ("QPATH-010", QPATH_010, ["QV0-03"]),
    ("QPATH-011", QPATH_011, ["QV2-01", "QV2-05"]),
    ("QPATH-030", QPATH_030, ["QV1-05"]),
]

# ---------------------------------------------------------------------------
# Execution-record cases (spec 30) over the committed GOLD-01 artifact

ART_REL = "sol_validator/corpus/GOLD-01/artifact.sol.d"


def census_query(case_id: str, description: str) -> dict:
    art = REPO / ART_REL
    return {
        "schema_version": "qry.query.v0.3",
        "query_id": case_id,
        "description": description,
        "sources": {
            "records": {
                "schema": CENSUS_SCHEMA,
                "artifact": {
                    "path": ART_REL,
                    "relation": "records",
                    "digest": artifact_tree_digest(art),
                },
            }
        },
        "nodes": [
            {"id": "r", "op": "read", "source": "records"},
            {"id": "s", "op": "sort", "input": "r", "by": ["record_id"]},
        ],
        "root": "s",
    }


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

    # Standard certified/semantic cases.
    for case_id, query, expected, claim_builder in CASES:
        case_dir = cases_dir / case_id
        extra = None
        if claim_builder is not None:
            claim = claim_builder()
            if case_id in EXPECTED_CORES:
                got = {
                    "guarantee": claim["guarantee"],
                    "lower": sorted(claim["lower"]["tuples"]) if claim["lower"] else None,
                    "upper": sorted(claim["upper"]["tuples"]) if claim["upper"] else None,
                    "may_be_empty_groups": sorted(claim["may_be_empty_groups"]),
                    "bound_rule": claim["bound_rule"],
                    "intervals": sorted(json.dumps(dict(iv), sort_keys=True)
                                        for iv in claim.get("intervals", [])),
                }
                want = EXPECTED_CORES[case_id]
                assert got == want, f"{case_id}: claim core {got} != expected {want}"
            extra = {"manifest": {}, "files": {
                "expected_bounds.json": {
                    "schema_version": "qry.bounds.v0.3",
                    "query_id": case_id,
                    "root": query["root"],
                    "root_bound": claim,
                }
            }}
        else:
            inference = infer_certified(query)
            cb = inference[query["root"]]
            got = core_of(cb)
            want = EXPECTED_CORES[case_id]
            assert got == want, f"{case_id}: inferred core {got} != expected {want}"
            extra = {"manifest": {}, "files": {
                "expected_bounds.json": {
                    "schema_version": "qry.bounds.v0.3",
                    "query_id": case_id,
                    "root": query["root"],
                    "root_bound": cb.to_json(),
                }
            }}
        write_case(case_dir, case_id, query["description"], expected, query, extra)

    for case_id, query, expected in SEMANTIC_CASES:
        write_case(cases_dir / case_id, case_id, query["description"], expected, query)

    # QPATH-008: the stale materialized view (QV8-03). The covering proof
    # was computed against source A's manifest; the query is pinned to
    # source B, so the source commits do not match.
    rewrite = {
        "rule_id": SUBST_RULE,
        "location": "node:f",
        "covering_proof": covering_proof_digest(),
        "source_commit": source_manifest({"sources": {"a": A}})["manifest_digest"],
    }
    write_case(cases_dir / "QPATH-008", "QPATH-008", QPATH_008["description"],
               ["QV8-03"], QPATH_008,
               extra={"manifest": {},
                      "files": {"rewrite.json": rewrite,
                                "expected.json": {"applied": False}}})

    # Execution-record cases over the committed GOLD-01 artifact (5 records).
    art = REPO / ART_REL
    _, total = scan_artifact_relation(art, "records", CENSUS_SCHEMA)

    q = census_query("QGOLD-001", "Exact snapshot query over one artifact.")
    res = execute_step(q, total, base_dir=REPO, run_id="qrun:corpus:QGOLD-001")
    assert not res.diagnostics and res.status == "complete", \
        f"QGOLD-001: {[d.rule_id for d in res.diagnostics]} {res.status}"
    assert res.record["guarantee"]["kind"] == "exact"
    write_case(cases_dir / "QGOLD-001", "QGOLD-001", q["description"], [], q,
               extra={"manifest": {"expected_status": "complete",
                                   "expected_guarantee": "exact"},
                      "files": {"execution.json": res.record}})

    q = census_query("QGOLD-012",
                     "Incomplete execution with continuation and honest "
                     "bounded result.")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:corpus:QGOLD-012")
    assert res.status == "incomplete_with_continuation" and res.record["continuation"], \
        f"QGOLD-012: {res.status}"
    assert res.record["guarantee"]["kind"] == "bounded"
    write_case(cases_dir / "QGOLD-012", "QGOLD-012", q["description"], [], q,
               extra={"manifest": {"expected_status": "incomplete_with_continuation",
                                   "expected_guarantee": "bounded"},
                      "files": {"execution.json": res.record}})

    q = census_query("QPATH-012",
                     "The incomplete exact count: the budget stops before the "
                     "scan is exhausted but the result is labeled exact.")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:corpus:QPATH-012")
    assert res.status == "incomplete_with_continuation"
    rec = res.record
    rec["guarantee"]["kind"] = "exact"  # the defective claim
    write_case(cases_dir / "QPATH-012", "QPATH-012", q["description"],
               ["QV5-07"], q,
               extra={"manifest": {"expected_status": "incomplete_with_continuation",
                                   "expected_guarantee": "exact"},
                      "files": {"execution.json": rec}})

    q = census_query("QPATH-035",
                     "The continuation drift: the continuation resumes against "
                     "a later branch head.")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:corpus:QPATH-035")
    assert res.status == "incomplete_with_continuation" and res.record["continuation"]
    resume_src = {**q["sources"]["records"], "branch": "main"}
    write_case(cases_dir / "QPATH-035", "QPATH-035", q["description"],
               ["QRY-EXEC-002", "QV1-02", "QV1-03"], q,
               extra={"manifest": {"expected_status": "incomplete_with_continuation",
                                   "expected_guarantee": "bounded"},
                      "files": {"execution.json": res.record,
                                "resume_source.json": resume_src}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
