"""Phase 8 tests: logical disclosure and leakage separation (spec 32).

Covers:
* the count-bucket partition mechanism (baseline 10-19 bucket;
  gap, overlap, bad start, and parse failures);
* QV9-03: raw cardinality under a bucketed policy, undeclared
  buckets, disclosure under suppression, and the clean bucketed path;
* QV8-08/QV9-04: provenance citing a restricted source under a
  redacted provenance policy, across the independent categories
  (32.7);
* QV9-05: the verbose denial;
* QV9-08: the non-inference claim without a conforming profile,
  with a weak physical channel, and the clean conforming path;
* canonicalization: the leakage policy and the restricted flag join
  the query identity;
* corpus-level regression for the five Phase 8 cases.
"""
import json
from pathlib import Path

from qryref.bounds import Field
from qryref.canonical import query_digest
from qryref.certified import (
    CertifiedBound,
    Relation,
    infer_certified,
    validate_bound_record,
)
from qryref.disclosure import (
    BASELINE_COUNT_BUCKETS,
    _valid_bucket_partition,
)
from qryref.validate import validate_case_dir

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

F_ID = Field("id", "i64", False)
F_NAME = Field("name", "string", False)

POLICY = {
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

S_RESTRICTED = {"schema": [{"name": "id", "type": "i64", "nullable": False},
                           {"name": "name", "type": "string", "nullable": False}],
                "tuples": [[1, "a"], [2, "b"], [3, "c"]],
                "restricted": True}


def _q(**kw):
    q = {"schema_version": "qry.query.v0.3", "query_id": "t",
         "sources": {"r": S_RESTRICTED},
         "nodes": [{"id": "r", "op": "read", "source": "r"}],
         "root": "r"}
    q.update(kw)
    return q


def rel(fields, tuples):
    return Relation(tuple(fields), frozenset(tuples))


def _claim(lower, upper, mode="tuple", members=(), sources=()):
    prov = {
        "lower_membership_mode": mode,
        "lower_memberships": [dict(m) for m in members],
        "upper_derivation": {
            "rule_id": "sol:bound/relation/v1", "input_relations": [],
            "sources": list(sources), "evaluators": [],
            "rewrites": [], "view_substitutions": [],
        },
    }
    return CertifiedBound.from_json({
        "guarantee": "bounded",
        "lower": lower.to_json() if lower is not None else None,
        "upper": upper.to_json() if upper is not None else None,
        "assurance": {"status": "contract_asserted", "evidence": ["source:r"],
                      "depends_on": ["source:r", "sol:bound/relation/v1"],
                      "stale": False},
        "provenance": prov,
        "may_be_empty_groups": [],
        "bound_rule": "sol:bound/relation/v1",
        "order": [],
        "intervals": [],
    })


L = lambda: rel([F_ID, F_NAME], [(1, "a")])
U = lambda: rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")])


def _got(q, claim, record=None):
    return {d.rule_id for d in
            validate_bound_record(q, claim, infer_certified(q), record=record)}


# ---------------------------------------------------------------------------
# Count-bucket partition mechanism (32.5)

def test_baseline_partition_is_valid():
    assert _valid_bucket_partition(BASELINE_COUNT_BUCKETS)
    # The baseline carries the mandatory 10-19 bucket.
    assert "10-19" in BASELINE_COUNT_BUCKETS


def test_spec_example_partition_is_valid():
    assert _valid_bucket_partition(["0", "1-10", "11-100", "more_than_100"])


def test_partition_gap_is_invalid():
    assert not _valid_bucket_partition(["0", "1-9", "11-19", "20-99", "100+"])


def test_partition_overlap_is_invalid():
    assert not _valid_bucket_partition(["0", "1-9", "9-19", "20-99", "100+"])


def test_partition_bad_start_is_invalid():
    assert not _valid_bucket_partition(["1", "2-9", "10-19", "20-99", "100+"])


def test_partition_unbounded_top_is_invalid():
    assert not _valid_bucket_partition(["0", "1-9", "10-19", "20-99"])


def test_partition_bad_bucket_is_invalid():
    assert not _valid_bucket_partition(["0", "1-9", "ten-nineteen", "100+"])
    assert not _valid_bucket_partition(None)
    assert not _valid_bucket_partition([])


# ---------------------------------------------------------------------------
# QV9-03: cardinality is suppressed, bucketed, or disclosed as declared

def test_qv903_raw_under_bucketed_policy():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    got = _got(q, c, {"cardinality_disclosure": {"mode": "raw", "value": 3}})
    assert "QV9-03" in got


def test_qv903_bucketed_declared_bucket_is_clean():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    got = _got(q, c, {"cardinality_disclosure": {"mode": "bucketed",
                                                 "bucket": "10-19"}})
    assert "QV9-03" not in got


def test_qv903_undeclared_bucket():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    got = _got(q, c, {"cardinality_disclosure": {"mode": "bucketed",
                                                 "bucket": "1000+"}})
    assert "QV9-03" in got


def test_qv903_no_declaration_counts_as_suppressed():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    assert "QV9-03" not in _got(q, c)


def test_qv903_disclosure_under_suppression():
    pol = {**POLICY,
           "logical_disclosure": {**POLICY["logical_disclosure"],
                                  "cardinality": "suppressed"},
           "count_buckets": None}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    got = _got(q, c, {"cardinality_disclosure": {"mode": "raw", "value": 3}})
    assert "QV9-03" in got


def test_qv903_raw_under_disclosed_policy_is_clean():
    pol = {**POLICY,
           "logical_disclosure": {**POLICY["logical_disclosure"],
                                  "cardinality": "disclosed"}}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    got = _got(q, c, {"cardinality_disclosure": {"mode": "raw", "value": 3}})
    assert "QV9-03" not in got


def test_qv903_bucketed_policy_without_buckets_is_invalid():
    pol = {**POLICY, "count_buckets": None}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    assert "QV9-03" in _got(q, c)


# ---------------------------------------------------------------------------
# QV8-08 / QV9-04: provenance visibility (32.7)

def test_qv808_qv904_lower_membership_cite():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U(), mode="why",
               members=[{"tuple": [1, "a"], "mode": "why",
                         "cites": ["source:r"]}])
    got = _got(q, c)
    assert {"QV8-08", "QV9-04"} <= got


def test_qv808_qv904_upper_derivation_source_cite():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U(), sources=["source:r"])
    got = _got(q, c)
    assert {"QV8-08", "QV9-04"} <= got


def test_qv808_qv904_record_cite_form():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U(), mode="why",
               members=[{"tuple": [1, "a"], "mode": "why",
                         "cites": ["record:r:1"]}])
    assert {"QV8-08", "QV9-04"} <= _got(q, c)


def test_qv808_qv904_visible_provenance_policy_is_clean():
    pol = {**POLICY,
           "logical_disclosure": {**POLICY["logical_disclosure"],
                                  "provenance": "visible"}}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U(), mode="why",
               members=[{"tuple": [1, "a"], "mode": "why",
                         "cites": ["source:r"]}],
               sources=["source:r"])
    got = _got(q, c)
    assert "QV8-08" not in got and "QV9-04" not in got


def test_qv808_qv904_no_restricted_sources_is_clean():
    q = _q(leakage_policy=POLICY,
           sources={"r": {**S_RESTRICTED, "restricted": False}})
    c = _claim(L(), U(), mode="why",
               members=[{"tuple": [1, "a"], "mode": "why",
                         "cites": ["source:r"]}],
               sources=["source:r"])
    got = _got(q, c)
    assert "QV8-08" not in got and "QV9-04" not in got


def test_qv808_qv904_no_policy_is_clean():
    q = _q()
    c = _claim(L(), U(), mode="why",
               members=[{"tuple": [1, "a"], "mode": "why",
                         "cites": ["source:r"]}],
               sources=["source:r"])
    got = _got(q, c)
    assert "QV8-08" not in got and "QV9-04" not in got


# ---------------------------------------------------------------------------
# QV9-05: error and unauthorized-reference behavior obey policy

def test_qv905_verbose_denial():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    got = _got(q, c, {"error_behavior": "distinguished_from_missing"})
    assert "QV9-05" in got


def test_qv905_indistinguishable_behavior_is_clean():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    got = _got(q, c, {"error_behavior": "indistinguishable_from_missing"})
    assert "QV9-05" not in got


def test_qv905_distinguishable_policy_permits_distinction():
    pol = {**POLICY,
           "logical_disclosure": {**POLICY["logical_disclosure"],
                                  "unauthorized_reference_behavior":
                                      "distinguishable"}}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    got = _got(q, c, {"error_behavior": "distinguished_from_missing"})
    assert "QV9-05" not in got


# ---------------------------------------------------------------------------
# QV9-08: no general non-inference claim without a conforming profile

PROFILE = {
    "adversary_model": "online adversary with query history",
    "query_history": "bounded to the declared session",
    "leakage_channels": ["logical_result", "diagnostics"],
    "verification_method": "exhaustive finite check over the declared channels",
}


def test_qv908_claim_without_profile():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    got = _got(q, c, {"non_inference_claim": True})
    assert "QV9-08" in got


def test_qv908_claim_with_weak_physical_channel():
    pol = {**POLICY, "physical_side_channels": {"timing": "best_effort"},
           "non_inference_profile": PROFILE}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    got = _got(q, c, {"non_inference_claim": True})
    assert "QV9-08" in got


def test_qv908_conforming_profile_and_suppressed_channels_is_clean():
    pol = {**POLICY, "physical_side_channels": {"timing": "suppressed"},
           "non_inference_profile": PROFILE}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    got = _got(q, c, {"non_inference_claim": True})
    assert "QV9-08" not in got


def test_qv908_incomplete_profile_is_not_conforming():
    bad = {k: v for k, v in PROFILE.items() if k != "verification_method"}
    pol = {**POLICY, "non_inference_profile": bad}
    q = _q(leakage_policy=pol)
    c = _claim(L(), U())
    assert "QV9-08" in _got(q, c, {"non_inference_claim": True})


def test_qv908_no_claim_is_clean():
    q = _q(leakage_policy=POLICY)
    c = _claim(L(), U())
    assert "QV9-08" not in _got(q, c)


# ---------------------------------------------------------------------------
# Canonicalization: policy and restricted flag join the query identity

def test_leakage_policy_joins_query_identity():
    base = _q()
    with_policy = _q(leakage_policy=POLICY)
    assert query_digest(base) != query_digest(with_policy)
    other = _q(leakage_policy={**POLICY, "policy_id": "policy:other"})
    assert query_digest(with_policy) != query_digest(other)


def test_restricted_flag_joins_source_identity():
    base = _q(sources={"r": {**S_RESTRICTED, "restricted": False}})
    restricted = _q()
    assert query_digest(base) != query_digest(restricted)


# ---------------------------------------------------------------------------
# Corpus-level regression: the five Phase 8 cases

PHASE8_CASES = ["QGOLD-011", "QPATH-005", "QPATH-027", "QPATH-028",
                "QPATH-029"]


def test_phase8_corpus_cases():
    for name in PHASE8_CASES:
        p = CASES / name
        manifest = json.loads((p / "manifest.json").read_text())
        expected = set(manifest.get("expected_diagnostics", []))
        got = {d.rule_id for d in validate_case_dir(p, check_match=not expected,
                                                    manifest=manifest)}
        if expected:
            assert expected.issubset(got), (name, expected, got)
        else:
            assert not got, (name, got)
