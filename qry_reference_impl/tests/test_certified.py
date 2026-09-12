"""Unit tests for the v0.3 certified answer-bound algebra (Phase 1).

Covers the normative transfer rules (spec 13.7-13.10), structural
one-sided containment (13.7.1), aggregate bound rules (13.11-13.14),
guarantee/assurance validation (13.2, 13.3, 13.19), bound provenance
(12.5-12.9), and validity-versus-tightness acceptance (13.18).
"""

import pytest

from qryref.certified import (
    CertifiedBound,
    Relation,
    avg_optional_prefix,
    infer_certified,
    match_core,
    validate_bound_record,
)
from qryref.bounds import Field
from qryref.engine import QRYValidationError

F_ID = Field("id", "i64", False)
F_NAME = Field("name", "string", False)
F_V = Field("v", "i64", False)
F_AMT = Field("amount", "decimal", False)
F_UID = Field("user_id", "i64", False)


def q(sources, nodes, root, stale=None):
    query = {
        "schema_version": "qry.query.v0.3",
        "query_id": "t",
        "sources": sources,
        "nodes": nodes,
        "root": root,
    }
    if stale:
        query["stale_dependencies"] = stale
    return query


def rel(fields, tuples):
    return Relation(tuple(fields), frozenset(tuples))


def claim(guarantee, lower, upper, rule=None, derivation_rule=None,
          members=None, mode="tuple", assurance_status="contract_asserted",
          depends_on=(), intervals=(), may_empty=()):
    prov = {
        "lower_membership_mode": mode,
        "lower_memberships": members or [],
        "upper_derivation": (
            {"rule_id": derivation_rule, "input_relations": [], "sources": [],
             "evaluators": [], "rewrites": [], "view_substitutions": []}
            if derivation_rule is not None else None
        ),
    }
    return CertifiedBound.from_json({
        "guarantee": guarantee,
        "lower": lower.to_json() if lower is not None else None,
        "upper": upper.to_json() if upper is not None else None,
        "assurance": {"status": assurance_status, "evidence": [],
                      "depends_on": list(depends_on), "stale": False},
        "provenance": prov,
        "may_be_empty_groups": [list(g) for g in may_empty],
        "bound_rule": rule,
        "order": [],
        "intervals": [dict(iv) for iv in intervals],
    })


# ---------------------------------------------------------------------------
# Relation operations and digests

def test_relation_digest_deterministic():
    a = rel([F_ID], [(1,), (2,)])
    b = rel([F_ID], [(2,), (1,)])
    assert a.digest() == b.digest()
    assert a.digest().startswith("object:sha256:")
    c = rel([F_ID], [(1,)])
    assert a.digest() != c.digest()


def test_relation_set_operations():
    l1 = rel([F_ID], [(1,), (2,)])
    l2 = rel([F_ID], [(2,), (3,)])
    assert Relation.union([l1, l2]).tuples == {(1,), (2,), (3,)}
    assert Relation.intersect([l1, l2]).tuples == {(2,)}
    assert l1.difference(l2).tuples == {(1,)}


def test_relation_select_project_rename_distinct():
    r = rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")])
    s = r.select([{"field": "id", "op": "gte", "value": 2}])
    assert s.tuples == {(2, "b"), (3, "c")}
    p = r.project([{"expr": "id", "name": "k"}])
    assert p.tuples == {(1,), (2,), (3,)}
    rn = r.rename({"id": "uid"})
    assert rn.fields[0].name == "uid" and rn.tuples == r.tuples
    d = rel([F_ID, F_NAME], [(1, "a"), (1, "z"), (2, "b")]).distinct(["id"])
    assert d.tuples == {(1, "a"), (2, "b")}  # deterministic: smallest tuple per key


def test_relation_join():
    left = rel([F_ID], [(1,), (2,)])
    right = rel([F_UID, F_AMT], [(1, 10), (1, 20), (2, 30)])
    j = left.join(right, [{"left": "id", "right": "user_id"}])
    assert j.tuples == {(1, 1, 10), (1, 1, 20), (2, 2, 30)}
    assert len(j.fields) == 3


# ---------------------------------------------------------------------------
# Transfer rules through inference

def test_read_exact_source():
    inf = infer_certified(q({"s": {"schema": [{"name": "id", "type": "i64"}],
                                   "tuples": [[1], [2]]}},
                            [{"id": "r", "op": "read", "source": "s"}], "r"))
    cb = inf["r"]
    assert cb.guarantee == "exact"
    assert cb.lower.tuples == cb.upper.tuples == {(1,), (2,)}
    assert cb.to_json()["result_object"] is not None  # exact collapse (13.4)


def test_read_bounded_source_and_invariant():
    inf = infer_certified(q({"s": {"schema": [{"name": "id", "type": "i64"}],
                                   "lower": {"tuples": [[1]]},
                                   "upper": {"tuples": [[1], [2]]}}},
                            [{"id": "r", "op": "read", "source": "s"}], "r"))
    cb = inf["r"]
    assert cb.guarantee == "bounded"
    assert cb.lower.tuples <= cb.upper.tuples


def test_read_inverted_source_raises_qv501():
    with pytest.raises(QRYValidationError) as ei:
        infer_certified(q({"s": {"schema": [{"name": "id", "type": "i64"}],
                                  "lower": {"tuples": [[1], [2]]},
                                  "upper": {"tuples": [[1]]}}},
                          [{"id": "r", "op": "read", "source": "s"}], "r"))
    assert any(d.rule_id == "QV5-01" for d in ei.value.diagnostics)


def test_select_transfer_componentwise():
    inf = infer_certified(q(
        {"s": {"schema": [{"name": "id", "type": "i64"}],
               "lower": {"tuples": [[1], [2]]}, "upper": {"tuples": [[1], [2], [3]]}}},
        [{"id": "r", "op": "read", "source": "s"},
         {"id": "f", "op": "filter", "input": "r",
          "predicate": {"terms": [{"field": "id", "op": "eq", "value": 2}]}}],
        "f"))
    cb = inf["f"]
    assert cb.lower.tuples == {(2,)}
    assert cb.upper.tuples == {(2,)}
    assert cb.guarantee == "exact"


def test_filter_without_terms_structural_containment():
    inf = infer_certified(q(
        {"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2], [3]]}},
        [{"id": "r", "op": "read", "source": "s"},
         {"id": "f", "op": "filter", "input": "r",
          "predicate": {"min_selectivity": 0.0, "max_selectivity": 1.0}}],
        "f"))
    cb = inf["f"]
    # 13.7.1: U_out = U_R; typed empty lower is valid.
    assert cb.lower.tuples == frozenset()
    assert cb.upper.tuples == {(1,), (2,), (3,)}
    assert cb.guarantee == "bounded"


def test_union_transfer_and_one_sided_lower():
    inf = infer_certified(q(
        {"a": {"schema": [{"name": "id", "type": "i64"}],
               "lower": {"tuples": [[1]]}, "upper": {"tuples": [[1], [2]]}},
         "b": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[3]]}},
        [{"id": "ra", "op": "read", "source": "a"},
         {"id": "rb", "op": "read", "source": "b"},
         {"id": "u", "op": "union_all", "inputs": ["ra", "rb"]}],
        "u"))
    cb = inf["u"]
    assert cb.lower.tuples == {(1,), (3,)}
    assert cb.upper.tuples == {(1,), (2,), (3,)}


def test_union_upper_requires_both_uppers():
    inf = infer_certified(q(
        {"a": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1]]},
         "b": {"schema": [{"name": "id", "type": "i64"}]}},  # no certified side
        [{"id": "ra", "op": "read", "source": "a"},
         {"id": "rb", "op": "read", "source": "b"},
         {"id": "u", "op": "union_all", "inputs": ["ra", "rb"]}],
        "u"))
    cb = inf["u"]
    assert cb.upper is None
    assert cb.lower.tuples == {(1,)}  # any available lower side is valid (13.17)
    assert cb.guarantee == "lower_bound"


def test_intersect_one_sided_upper():
    inf = infer_certified(q(
        {"a": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2]]},
         "b": {"schema": [{"name": "id", "type": "i64"}]}},
        [{"id": "ra", "op": "read", "source": "a"},
         {"id": "rb", "op": "read", "source": "b"},
         {"id": "i", "op": "intersect", "inputs": ["ra", "rb"]}],
        "i"))
    cb = inf["i"]
    assert cb.lower is None
    assert cb.upper.tuples == {(1,), (2,)}
    assert cb.guarantee == "upper_bound"


def test_difference_transfer():
    inf = infer_certified(q(
        {"a": {"schema": [{"name": "id", "type": "i64"}],
               "lower": {"tuples": [[1], [2]]}, "upper": {"tuples": [[1], [2], [3]]}},
         "b": {"schema": [{"name": "id", "type": "i64"}],
               "lower": {"tuples": [[2]]}, "upper": {"tuples": [[2], [4]]}}},
        [{"id": "ra", "op": "read", "source": "a"},
         {"id": "rb", "op": "read", "source": "b"},
         {"id": "d", "op": "difference", "inputs": ["ra", "rb"]}],
        "d"))
    cb = inf["d"]
    # 13.8: L_R = L1 \ U2, U_R = U1 \ L2.
    assert cb.lower.tuples == {(1,)}
    assert cb.upper.tuples == {(1,), (3,)}


def test_difference_heuristic_right_keeps_upper():
    inf = infer_certified(q(
        {"a": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2]]},
         "b": {"schema": [{"name": "id", "type": "i64"}]}},
        [{"id": "ra", "op": "read", "source": "a"},
         {"id": "rb", "op": "read", "source": "b"},
         {"id": "d", "op": "difference", "inputs": ["ra", "rb"]}],
        "d"))
    cb = inf["d"]
    assert cb.lower.tuples == frozenset()  # typed empty lower (13.8)
    assert cb.upper.tuples == {(1,), (2,)}


def test_complement_as_difference_over_exact_domain():
    # 13.9: complement vs explicit finite exact domain D: L = D \ U_R, U = D \ L_R.
    inf = infer_certified(q(
        {"d": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2], [3], [4]]},
         "r": {"schema": [{"name": "id", "type": "i64"}],
               "lower": {"tuples": [[2]]}, "upper": {"tuples": [[2], [3]]}}},
        [{"id": "rd", "op": "read", "source": "d"},
         {"id": "rr", "op": "read", "source": "r"},
         {"id": "c", "op": "difference", "inputs": ["rd", "rr"]}],
        "c"))
    cb = inf["c"]
    assert cb.lower.tuples == {(1,), (4,)}
    assert cb.upper.tuples == {(1,), (3,), (4,)}


def test_limit_exact_ordered_and_inexact_heuristic():
    sources = {"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2], [3], [4]]}}
    nodes = [
        {"id": "r", "op": "read", "source": "s"},
        {"id": "o", "op": "sort", "input": "r", "by": ["id"]},
        {"id": "l", "op": "limit", "input": "o", "limit": 2},
    ]
    inf = infer_certified(q(sources, nodes, "l"))
    assert inf["l"].guarantee == "exact"
    assert inf["l"].lower.tuples == {(1,), (2,)}
    # Inexact input: no position certainty -> heuristic (13.15).
    sources2 = {"s": {"schema": [{"name": "id", "type": "i64"}],
                      "lower": {"tuples": [[1]]}, "upper": {"tuples": [[1], [2], [3]]}}}
    inf2 = infer_certified(q(sources2, nodes, "l"))
    assert inf2["l"].guarantee == "heuristic"
    assert inf2["l"].lower is None and inf2["l"].upper is None


def test_evaluate_heuristic_and_sound_positive():
    sources = {"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2], [3]]}}
    nodes_h = [{"id": "r", "op": "read", "source": "s"},
               {"id": "e", "op": "evaluate", "input": "r",
                "evaluator": "sol:evaluator/x/v1", "mode": "heuristic"}]
    inf = infer_certified(q(sources, nodes_h, "e"))
    assert inf["e"].lower.tuples == frozenset()
    assert inf["e"].upper.tuples == {(1,), (2,), (3,)}
    nodes_p = [{"id": "r", "op": "read", "source": "s"},
               {"id": "e", "op": "evaluate", "input": "r",
                "evaluator": "sol:evaluator/x/v1", "mode": "sound_positive",
                "positives": [[1], [3]]}]
    inf2 = infer_certified(q(sources, nodes_p, "e"))
    assert inf2["e"].lower.tuples == {(1,), (3,)}
    assert inf2["e"].upper.tuples == {(1,), (2,), (3,)}


def test_evaluate_positive_outside_upper_raises_qv504():
    sources = {"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2]]}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "e", "op": "evaluate", "input": "r",
              "evaluator": "sol:evaluator/x/v1", "mode": "sound_positive",
              "positives": [[9]]}]
    with pytest.raises(QRYValidationError) as ei:
        infer_certified(q(sources, nodes, "e"))
    assert any(d.rule_id == "QV5-04" for d in ei.value.diagnostics)


def test_least_fixpoint_separate_sides():
    sources = {
        "seed": {"schema": [{"name": "x", "type": "i64"}],
                 "lower": {"tuples": [[1]]}, "upper": {"tuples": [[1], [4]]}},
        "edge": {"schema": [{"name": "a", "type": "i64"}, {"name": "b", "type": "i64"}],
                 "lower": {"tuples": [[1, 2]]}, "upper": {"tuples": [[1, 2], [2, 3]]}},
    }
    nodes = [{"id": "rs", "op": "read", "source": "seed"},
             {"id": "re", "op": "read", "source": "edge"},
             {"id": "lf", "op": "least_fixpoint", "seed": "rs", "edge": "re",
              "on": {"left": "a", "right": "b"}}]
    inf = infer_certified(q(sources, nodes, "lf"))
    assert inf["lf"].lower.tuples == {(1,), (2,)}
    assert inf["lf"].upper.tuples == {(1,), (2,), (3,), (4,)}


def test_temporal_slice_and_annotate():
    sources = {"s": {"schema": [{"name": "id", "type": "i64"}, {"name": "ts", "type": "string"}],
                     "tuples": [[1, "2026-01-01"], [2, "2026-06-01"], [3, "2026-12-01"]]}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "t", "op": "temporal_slice", "input": "r", "field": "ts",
              "from": "2026-01-01", "to": "2026-06-30"},
             {"id": "a", "op": "annotate", "input": "t",
              "columns": [{"name": "tag", "literal": "in-range"}]}]
    inf = infer_certified(q(sources, nodes, "a"))
    assert inf["a"].lower.tuples == {(1, "2026-01-01", "in-range"), (2, "2026-06-01", "in-range")}


# ---------------------------------------------------------------------------
# Aggregate bound rules (13.11-13.14)

def test_count_set_interval():
    sources = {"s": {"schema": [{"name": "id", "type": "i64"}],
                     "lower": {"tuples": [[1], [2]]}, "upper": {"tuples": [[1], [2], [3]]}}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "a", "op": "aggregate", "input": "r", "group_by": [],
              "aggregates": [{"name": "n", "func": "count_set", "type": "i64"}]}]
    inf = infer_certified(q(sources, nodes, "a"))
    cb = inf["a"]
    assert cb.lower.tuples == {()} and cb.upper.tuples == {()}
    assert cb.intervals[0] == {"field": "n", "group": [], "lower": 2, "upper": 3, "may_be_empty": False}


def test_sum_interval():
    sources = {"s": {"schema": [{"name": "v", "type": "i64"}],
                     "lower": {"tuples": [[5]]}, "upper": {"tuples": [[5], [-3], [10]]}}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "a", "op": "aggregate", "input": "r", "group_by": [],
              "aggregates": [{"name": "s", "func": "sum", "field": "v", "type": "i64"}]}]
    inf = infer_certified(q(sources, nodes, "a"))
    iv = inf["a"].intervals[0]
    # 13.12: SUM_min = 5 + (-3) = 2, SUM_max = 5 + 10 = 15.
    assert iv["lower"] == 2 and iv["upper"] == 15


def test_min_max_intervals():
    sources = {"s": {"schema": [{"name": "v", "type": "i64"}],
                     "lower": {"tuples": [[5]]}, "upper": {"tuples": [[5], [1], [9]]}}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "a", "op": "aggregate", "input": "r", "group_by": [],
              "aggregates": [{"name": "mn", "func": "min", "field": "v", "type": "i64"},
                             {"name": "mx", "func": "max", "field": "v", "type": "i64"}]}]
    inf = infer_certified(q(sources, nodes, "a"))
    ivs = {iv["field"]: iv for iv in inf["a"].intervals}
    assert ivs["mn"]["lower"] == 1 and ivs["mn"]["upper"] == 5   # MIN(U) <= MIN(R) <= MIN(L)
    assert ivs["mx"]["lower"] == 5 and ivs["mx"]["upper"] == 9   # MAX(L) <= MAX(R) <= MAX(U)


def test_avg_optional_prefix_rule():
    # 13.14: L = {5}, O = {16, 6}. AVG_min = min(5/1, 11/2, 27/3) = 5/1;
    # AVG_max = max(5/1, 21/2, 27/3) = 21/2.
    Lg = [(1, 5)]
    Ug = [(1, 5), (1, 16), (1, 6)]
    amin, amax, may_empty = avg_optional_prefix(Lg, Ug, 1)
    assert (amin, amax, may_empty) == (5 / 1, 21 / 2, False)
    # n_L = 0: extrema over k >= 1, may_be_empty true.
    amin, amax, may_empty = avg_optional_prefix([], [(2, 7)], 1)
    assert (amin, amax, may_empty) == (7, 7, True)
    # Empty exact relation: AVG undefined.
    assert avg_optional_prefix([], [], 1) is None


def test_aggregate_may_be_empty_group():
    sources = {"s": {"schema": [{"name": "g", "type": "i64"}, {"name": "v", "type": "i64"}],
                     "lower": {"tuples": [[1, 5]]},
                     "upper": {"tuples": [[1, 5], [1, 16], [1, 6], [2, 7]]}}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "a", "op": "aggregate", "input": "r", "group_by": ["g"],
              "aggregates": [{"name": "avg_v", "func": "avg", "field": "v", "type": "decimal"}]}]
    inf = infer_certified(q(sources, nodes, "a"))
    cb = inf["a"]
    assert cb.lower.tuples == {(1,)}
    assert cb.upper.tuples == {(1,), (2,)}
    assert list(cb.may_be_empty_groups) == [(2,)]
    ivs = {tuple(iv["group"]): iv for iv in cb.intervals}
    assert ivs[(1,)]["lower"] == "5/1" and ivs[(1,)]["upper"] == "21/2"
    assert ivs[(2,)]["lower"] == "7/1" and ivs[(2,)]["may_be_empty"] is True


# ---------------------------------------------------------------------------
# Claim validation (13.19)

def test_qv501_inverted_claim():
    query = q({"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2]]}},
              [{"id": "r", "op": "read", "source": "s"}], "r")
    inf = infer_certified(query)
    c = claim("bounded", rel([F_ID], [(1,), (2,)]), rel([F_ID], [(1,)]),
              rule="sol:bound/relation/v1", derivation_rule="sol:bound/relation/v1")
    diags = validate_bound_record(query, c, inf)
    assert any(d.rule_id == "QV5-01" for d in diags)


def test_qv502_missing_side():
    # A "bounded" label claims both certified sides; a missing upper is QV5-02.
    c = claim("bounded", rel([F_ID], [(1,)]), None, rule="sol:bound/relation/v1")
    diags = validate_bound_record(q({}, [], "r"), c)
    assert any(d.rule_id == "QV5-02" for d in diags)
    # A "lower_bound" label with an unavailable upper is valid (13.2, 13.5).
    c2 = claim("lower_bound", rel([F_ID], [(1,)]), None, rule="sol:bound/relation/v1")
    assert not any(d.rule_id == "QV5-02" for d in validate_bound_record(q({}, [], "r"), c2))


def test_qv503_false_exact():
    c = claim("exact", rel([F_ID], [(1,)]), rel([F_ID], [(1,), (2,)]),
              rule="sol:bound/relation/v1", derivation_rule="sol:bound/relation/v1")
    diags = validate_bound_record(q({}, [], "r"), c)
    assert any(d.rule_id == "QV5-03" for d in diags)


def test_qv806_missing_upper_derivation():
    c = claim("bounded", rel([F_ID], [(1,)]), rel([F_ID], [(1,), (2,)]),
              rule="sol:bound/relation/v1", derivation_rule=None)
    diags = validate_bound_record(q({}, [], "r"), c)
    assert any(d.rule_id == "QV8-06" for d in diags)


def test_qv807_upper_only_why_provenance():
    c = claim("bounded", rel([F_ID], [(1,)]), rel([F_ID], [(1,), (2,)]),
              rule="sol:bound/relation/v1", derivation_rule="sol:bound/relation/v1",
              mode="why",
              members=[{"tuple": [2], "mode": "why", "cites": ["record:v1"]}])
    diags = validate_bound_record(q({}, [], "r"), c)
    assert any(d.rule_id == "QV8-07" for d in diags)
    assert any(d.rule_id == "QINV-14" for d in diags)


def test_qv510_stale_assurance():
    query = q({"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1]]}},
              [{"id": "r", "op": "read", "source": "s"}], "r",
              stale=["source:s"])
    inf = infer_certified(query)
    c = claim("exact", rel([F_ID], [(1,)]), rel([F_ID], [(1,)]),
              rule="sol:bound/relation/v1", derivation_rule="sol:bound/relation/v1",
              assurance_status="contract_asserted", depends_on=["source:s"])
    diags = validate_bound_record(query, c, inf)
    assert any(d.rule_id == "QV5-10" for d in diags)


def test_qv512_avg_nonconformance():
    sources = {"s": {"schema": [{"name": "g", "type": "i64"}, {"name": "v", "type": "i64"}],
                     "lower": {"tuples": [[1, 5]]},
                     "upper": {"tuples": [[1, 5], [1, 16], [1, 6]]}}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "a", "op": "aggregate", "input": "r", "group_by": ["g"],
              "aggregates": [{"name": "avg_v", "func": "avg", "field": "v", "type": "decimal"}]}]
    query = q(sources, nodes, "a")
    inf = infer_certified(query)
    bad = claim("bounded", rel([Field("g", "i64", False)], [(1,)]),
                rel([Field("g", "i64", False)], [(1,)]),
                rule="sol:bound/avg_optional_prefix/v1",
                derivation_rule="sol:bound/avg_optional_prefix/v1",
                intervals=[{"field": "avg_v", "group": [1], "lower": "11/2",
                            "upper": "21/2", "may_be_empty": False}])
    diags = validate_bound_record(query, bad, inf)
    assert any(d.rule_id == "QV5-12" for d in diags)


# ---------------------------------------------------------------------------
# Validity versus tightness (13.18)

def test_tighter_registered_bound_accepted():
    sources = {"s": {"schema": [{"name": "v", "type": "i64"}],
                     "lower": {"tuples": [[2], [4]]},
                     "upper": {"tuples": [[2], [3], [4]]}}}
    nodes = [{"id": "r", "op": "read", "source": "s"},
             {"id": "f", "op": "filter", "input": "r",
              "predicate": {"terms": [{"field": "v", "op": "gte", "value": 2}]}}]
    query = q(sources, nodes, "f")
    inf = infer_certified(query)
    inferred = inf["f"]
    # Baseline (13.7): L = {2,4}, U = {2,3,4}.
    assert inferred.lower.tuples == {(2,), (4,)}
    assert inferred.upper.tuples == {(2,), (3,), (4,)}
    # Tighter registered claim: U collapses to {2,4} (exact).
    tighter = claim("exact", rel([F_V], [(2,), (4,)]), rel([F_V], [(2,), (4,)]),
                    rule="sol:bound/select_certified/v1",
                    derivation_rule="sol:bound/select_certified/v1")
    assert match_core(inferred, tighter)
    # A looser claim (smaller lower than the baseline) is not a tighter bound.
    looser = claim("bounded", rel([F_V], [(2,)]), rel([F_V], [(2,), (3,), (4,)]),
                   rule="sol:bound/select_certified/v1",
                   derivation_rule="sol:bound/select_certified/v1")
    assert not match_core(inferred, looser)


def test_mixed_guarantee_composition_invalidates_only_dependent_sides():
    # A heuristic operand invalidates only the sides that depend on it:
    # intersect keeps the other operand's certified upper (13.16, 13.7.1).
    sources = {"a": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2]]},
               "b": {"schema": [{"name": "id", "type": "i64"}]}}
    nodes = [{"id": "ra", "op": "read", "source": "a"},
             {"id": "rb", "op": "read", "source": "b"},
             {"id": "i", "op": "intersect", "inputs": ["ra", "rb"]}]
    inf = infer_certified(q(sources, nodes, "i"))
    cb = inf["i"]
    assert cb.upper is not None and cb.upper.tuples == {(1,), (2,)}
    assert cb.lower is None  # not synthesized from an arbitrary universe (13.5)
    assert cb.guarantee == "upper_bound"


def test_unavailable_side_not_synthesized():
    sources = {"a": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1]]},
               "b": {"schema": [{"name": "id", "type": "i64"}]}}
    nodes = [{"id": "ra", "op": "read", "source": "a"},
             {"id": "rb", "op": "read", "source": "b"},
             {"id": "u", "op": "union_all", "inputs": ["ra", "rb"]}]
    inf = infer_certified(q(sources, nodes, "u"))
    assert inf["u"].upper is None  # explicit unavailable, never synthesized
