"""Phase 7 tests: machine-summary substitution answering (28.3-28.5,
37.7), lower-membership provenance (QV8-05, 12.4-12.5), the claim-context
half of QV7-03 (25.4.3), and temporal commit resolution (QV1-02, 17.5).

Covers:
* the substitution applying for a proven covering query (QGOLD-005) and
  being recorded with the covering proof and the source-commit pin;
* ineligible substitutions: commit mismatch (QV8-03), lossy summary
  (QV8-04), heuristic summary (QV8-02), missing proof (QV7-02);
* QV8-05: a requested mode above `tuple` requires per-tuple membership
  provenance for every lower tuple;
* QV7-03 (claim context): a rewrite cited in the claim's provenance must
  cover the query-required dimensions;
* QV1-02: a latest-commit selection requires an ancestry relation and a
  deterministic tie or conflict rule (17.5);
* corpus-level regression for the three Phase 7 cases.
"""
import json
from collections import Counter
from pathlib import Path

from qryref.bounds import Field
from qryref.canonical import source_manifest
from qryref.certified import (
    CertifiedBound,
    Relation,
    infer_certified,
    validate_bound_record,
)
from qryref.engine import semantic_diagnostics
from qryref.exact import execute_step
from qryref.make_rewrites_corpus import (
    A,
    PRED_Y,
    PUSH_RULE,
    SUBST_RULE,
    covering_proof_digest,
    gold_covering_proof_digest,
    heuristic_covering_proof_digest,
)
from qryref.rewrites import (
    EXPERIMENTAL_RULE,
    RewriteRequest,
    apply_rewrite,
)
from qryref.validate import validate_case_dir

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

VALS = [{"name": "v", "type": "i64", "nullable": False}]
F_ID = Field("id", "i64", False)
F_NAME = Field("name", "string", False)

A_MANIFEST = source_manifest({"sources": {"a": A}})["manifest_digest"]
GOLD_PROOF = gold_covering_proof_digest()


def _q(sources, nodes, root="r", **kw):
    q = {"schema_version": "qry.query.v0.3", "query_id": "t",
         "sources": sources, "nodes": nodes, "root": root}
    q.update(kw)
    return q


def _subst_query():
    return _q({"a": A},
              [{"id": "ra", "op": "read", "source": "a"},
               {"id": "f", "op": "filter", "input": "ra", "predicate": PRED_Y}],
              "f")


def _subst_request(**overrides):
    d = {"rule_id": SUBST_RULE, "location": "node:f",
         "covering_proof": GOLD_PROOF, "source_commit": A_MANIFEST}
    d.update(overrides)
    return RewriteRequest.from_dict(d)


# ---------------------------------------------------------------------------
# Machine-summary substitution answering (28.3, 28.5, 37.7)

def test_substitution_applies_and_records():
    out = apply_rewrite(_subst_query(), _subst_request())
    assert out.applied, [d.rule_id for d in out.diagnostics]
    assert not out.diagnostics
    # The substitution is recorded with the covering proof and the
    # source-commit pin (28.5).
    assert out.record["covering_proof"] == GOLD_PROOF
    assert out.record["source_commit"] == A_MANIFEST
    # The rewritten query answers the span's source from the summary.
    assert out.rewritten_query["sources"]["a"]["machine_summary"] == {
        "covering_proof": GOLD_PROOF, "source_commit": A_MANIFEST}


def test_substitution_preserves_exact_result():
    q = _subst_query()
    out = apply_rewrite(q, _subst_request())
    b, a = execute_step(q, 10**6), execute_step(out.rewritten_query, 10**6)
    assert not b.diagnostics and not a.diagnostics
    assert Counter(map(tuple, b.rows)) == Counter(map(tuple, a.rows))


def test_substitution_commit_mismatch():
    out = apply_rewrite(_subst_query(),
                        _subst_request(source_commit="commit:other"))
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV8-03"}


def test_substitution_lossy_summary():
    out = apply_rewrite(_subst_query(),
                        _subst_request(covering_proof=covering_proof_digest()))
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV8-04"}


def test_substitution_heuristic_summary():
    out = apply_rewrite(_subst_query(),
                        _subst_request(covering_proof=heuristic_covering_proof_digest()))
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV8-02"}


def test_substitution_without_proof():
    out = apply_rewrite(_subst_query(),
                        _subst_request(covering_proof=None, source_commit=None))
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV7-02"}


# ---------------------------------------------------------------------------
# QV8-05: requested supported membership provenance (12.4-12.5)

def rel(fields, tuples):
    return Relation(tuple(fields), frozenset(tuples))


def _claim(lower, upper, mode="tuple", members=(), rewrites=()):
    prov = {
        "lower_membership_mode": mode,
        "lower_memberships": [dict(m) for m in members],
        "upper_derivation": {
            "rule_id": "sol:bound/relation/v1", "input_relations": [],
            "sources": ["source:s"], "evaluators": [],
            "rewrites": list(rewrites), "view_substitutions": [],
        },
    }
    return CertifiedBound.from_json({
        "guarantee": "bounded",
        "lower": lower.to_json() if lower is not None else None,
        "upper": upper.to_json() if upper is not None else None,
        "assurance": {"status": "contract_asserted", "evidence": ["source:s"],
                      "depends_on": ["source:s", "sol:bound/relation/v1"],
                      "stale": False},
        "provenance": prov,
        "may_be_empty_groups": [],
        "bound_rule": "sol:bound/relation/v1",
        "order": [],
        "intervals": [],
    })


def _s_query(**kw):
    return _q({"s": {"schema": [{"name": "id", "type": "i64", "nullable": False},
                                {"name": "name", "type": "string", "nullable": False}],
                     "tuples": [[1, "a"], [2, "b"], [3, "c"]]}},
              [{"id": "r", "op": "read", "source": "s"}], "r", **kw)


def test_qv805_missing_membership_provenance():
    q = _s_query()
    c = _claim(rel([F_ID, F_NAME], [(1, "a")]),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               mode="why")
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV8-05" in got


def test_qv805_complete_membership_provenance():
    q = _s_query()
    c = _claim(rel([F_ID, F_NAME], [(1, "a")]),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               mode="why",
               members=[{"tuple": [1, "a"], "mode": "why",
                         "cites": ["source:s"]}])
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV8-05" not in got


def test_qv805_minimal_mode_needs_no_entries():
    q = _s_query()
    c = _claim(rel([F_ID, F_NAME], [(1, "a")]),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               mode="tuple")
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV8-05" not in got


def test_qv805_empty_lower_is_vacuously_satisfied():
    q = _s_query()
    c = _claim(rel([F_ID, F_NAME], []),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               mode="why")
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV8-05" not in got


# ---------------------------------------------------------------------------
# QV7-03 (claim context): cited rewrites must cover required dimensions

def test_qv703_claim_cited_rewrite_drops_required_dimension():
    q = _s_query(required_dimensions=["value", "provenance"])
    c = _claim(rel([F_ID, F_NAME], [(1, "a")]),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               rewrites=[EXPERIMENTAL_RULE])
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV7-03" in got


def test_qv703_claim_cited_rewrite_covers_required_dimension():
    q = _s_query(required_dimensions=["value", "provenance"])
    c = _claim(rel([F_ID, F_NAME], [(1, "a")]),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               rewrites=[PUSH_RULE])
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV7-03" not in got


def test_qv703_claim_no_required_dimensions():
    q = _s_query()
    c = _claim(rel([F_ID, F_NAME], [(1, "a")]),
               rel([F_ID, F_NAME], [(1, "a"), (2, "b"), (3, "c")]),
               rewrites=[EXPERIMENTAL_RULE])
    got = {d.rule_id for d in validate_bound_record(q, c, infer_certified(q))}
    assert "QV7-03" not in got


# ---------------------------------------------------------------------------
# QV1-02: temporal commit resolution (17.5)

def _temporal_query(latest):
    src = {"schema": VALS, "tuples": [[1], [2]],
           "branch": "main", "commit": "object:sha256:" + "00" * 32}
    if latest is not None:
        src["latest"] = latest
    return _q({"s": src}, [{"id": "r", "op": "read", "source": "s"}], "r")


def test_qv102_timestamp_latest_selection_fails():
    q = _temporal_query({"branch": "main"})
    diags = semantic_diagnostics(q)
    assert {d.rule_id for d in diags} == {"QV1-02"}
    assert diags[0].category == "temporal_validation_failure"


def test_qv102_latest_with_ancestry_and_tie_rule_is_clean():
    q = _temporal_query({"branch": "main",
                         "ancestry": "object:sha256:" + "aa" * 32,
                         "tie_rule": "object:sha256:" + "bb" * 32})
    assert {d.rule_id for d in semantic_diagnostics(q)} == set()


def test_qv102_no_latest_declaration_is_clean():
    assert {d.rule_id for d in semantic_diagnostics(_temporal_query(None))} == set()


# ---------------------------------------------------------------------------
# Corpus-level regression: the three Phase 7 cases

PHASE7_CASES = ["QGOLD-005", "QPATH-013", "QPATH-014"]


def test_phase7_corpus_cases():
    for name in PHASE7_CASES:
        p = CASES / name
        manifest = json.loads((p / "manifest.json").read_text())
        expected = set(manifest.get("expected_diagnostics", []))
        got = {d.rule_id for d in validate_case_dir(p, check_match=not expected,
                                                    manifest=manifest)}
        if expected:
            assert expected.issubset(got), (name, expected, got)
        else:
            assert not got, (name, got)
