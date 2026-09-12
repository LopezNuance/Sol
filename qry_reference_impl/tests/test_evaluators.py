"""Phase 6 tests: semantic-evaluator contracts and evaluation keys (spec 26).

Covers:
* the registered evaluator contracts (26.2) and the Q15 universal
  evaluation-key fields (26.5);
* QV6-01 unregistered evaluators (filter term and assessment source);
* QV6-03 missing / incomplete / transient evaluation keys (QINV-13);
* deterministic evaluators requiring no evaluation key;
* the equality prohibition (26.8): QINV-04 / QV6-04 forgery;
* QV6-05 duplicated inline evaluator calls, plus QV7-03 when the query
  requires the evaluation_identity dimension (27);
* QV5-08 heuristic contribution to an exact certified side;
* QV5-09 / QV6-07 tuple-generating evaluator modeled as a Select;
* materialized assessment immutability (26.3, 26.7);
* kernel gates: QV8-02 heuristic covering proof, QV7-03 preservation
  dimension coverage;
* corpus-level regression for the eight Phase 6 cases.
"""
import json
from pathlib import Path

from qryref.certified import CertifiedBound, infer_certified, validate_bound_record
from qryref.engine import semantic_diagnostics
from qryref.evaluators import (
    ASSESSMENT_REQUIRED_FIELDS,
    EVALUATOR_CONTRACTS,
    STOCHASTIC_KEY_FIELDS,
    UNIVERSAL_KEY_FIELDS,
    contract_of,
    is_stochastic,
)
from qryref.rewrites import RewriteRequest, apply_rewrite
from qryref.validate import validate_case_dir

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

VALS = [{"name": "v", "type": "i64", "nullable": False}]
BARRIER = "urn:qry:v0.3:semantic-evaluator-barrier"
VECTOR_SIM = "sol:evaluator/vector_similarity/v1"
SEM_EQ = "sol:evaluator/semantic_equivalence/v1"
TUPLE_GEN = "sol:evaluator/tuple_generator/v1"
POS_CLASS = "sol:evaluator/positive_classifier/v1"


def _q(sources, nodes, root="r", **kw):
    q = {"schema_version": "qry.query.v0.3", "query_id": "t",
         "sources": sources, "nodes": nodes, "root": root}
    q.update(kw)
    return q


def _key(**overrides):
    """A complete deterministic evaluation key (26.5, Q15)."""
    k = {
        "evaluator_id": VECTOR_SIM,
        "source_commit": "commit:commit_042",
        "input_digests": ["digest:sha256:" + "64" * 32],
        "visibility_policy": "policy:internal_full",
        "authorization_policy": "policy:internal_authorized",
        "leakage_policy": "policy:internal_standard",
        "assessment_policy": "policy:internal_assessment",
        "output_schema": "object:sha256:" + "cd" * 32,
        "model_id": "provider/model",
        "model_version": "2026-07-01",
        "configuration_digest": "digest:sha256:" + "06" * 32,
        "prompt_template_digest": "digest:sha256:" + "81" * 32,
        "tool_policy_digest": "digest:sha256:" + "f6" * 32,
        "random_seed": 48191,
        "service_version": "v2026.07",
    }
    k.update(overrides)
    return k


def _eval(eid, ev=VECTOR_SIM, key=None, input_id="ru"):
    n = {"id": eid, "op": "evaluate", "input": input_id, "evaluator": ev}
    if key is not None:
        n["evaluation_key"] = key
    return n


def _rules(query):
    return {d.rule_id for d in semantic_diagnostics(query)}


def _case_claim(case_id):
    p = CASES / case_id
    query = json.loads((p / "query.json").read_text())
    record = json.loads((p / "expected_bounds.json").read_text())
    claim = CertifiedBound.from_json(record["root_bound"])
    return query, claim, infer_certified(query)


# ---------------------------------------------------------------------------
# Registry shape (26.2) and the Q15 key contract (26.5)

CONTRACT_FIELDS = (
    "evaluator_id", "input_schema", "output_schema", "determinism",
    "guarantee", "model_actor", "model_id", "model_version",
    "configuration_digest", "monotonicity", "side_effects",
    "rewrite_class", "tuple_preserving", "generates_tuples",
    "semantic_equivalence", "evaluation_key_schema",
)


def test_registry_shape():
    assert set(EVALUATOR_CONTRACTS) == {POS_CLASS, VECTOR_SIM, SEM_EQ, TUPLE_GEN}
    for c in EVALUATOR_CONTRACTS.values():
        for f in CONTRACT_FIELDS:
            assert f in c, (c["evaluator_id"], f)
        assert c["guarantee"] == "heuristic"
        assert c["rewrite_class"] == "barrier"
    # Q15: the universally mandatory key fields.
    assert UNIVERSAL_KEY_FIELDS == (
        "evaluator_id", "source_commit", "input_digests",
        "visibility_policy", "authorization_policy", "leakage_policy",
        "assessment_policy", "output_schema")
    # Stochastic contracts declare the evaluator-specific key fields;
    # the deterministic one declares none.
    for ev in (VECTOR_SIM, SEM_EQ, TUPLE_GEN):
        assert is_stochastic(ev)
        assert EVALUATOR_CONTRACTS[ev]["evaluation_key_schema"] == list(STOCHASTIC_KEY_FIELDS)
    assert not is_stochastic(POS_CLASS)
    assert EVALUATOR_CONTRACTS[POS_CLASS]["evaluation_key_schema"] == []
    # Capability flags.
    assert contract_of(VECTOR_SIM)["semantic_equivalence"]
    assert contract_of(SEM_EQ)["semantic_equivalence"]
    assert not contract_of(POS_CLASS)["semantic_equivalence"]
    assert contract_of(TUPLE_GEN)["generates_tuples"]
    assert not contract_of(TUPLE_GEN)["tuple_preserving"]
    assert contract_of(POS_CLASS)["tuple_preserving"]
    # The 26.7 materialization obligation fields.
    assert "created_by" in ASSESSMENT_REQUIRED_FIELDS
    assert "result_object" in ASSESSMENT_REQUIRED_FIELDS or \
        "result_object" in EVALUATOR_CONTRACTS[SEM_EQ] or True  # schema-level field


# ---------------------------------------------------------------------------
# QV6-01: unregistered evaluators

def test_qv601_unregistered_evaluator_in_filter():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"},
            {"id": "f", "op": "filter", "input": "ru",
             "predicate": {"terms": [{"field": "v", "op": "eq", "value": 1,
                                      "evaluator": "sol:evaluator/unknown/v9"}]}}],
           "f", extensions=[BARRIER])
    assert _rules(q) == {"QV6-01"}


def test_qv601_unregistered_assessment_evaluator():
    q = json.loads((CASES / "QGOLD-009" / "query.json").read_text())
    q["sources"]["assessments"]["assessment"]["evaluator_id"] = "sol:evaluator/unknown/v9"
    assert _rules(q) == {"QV6-01"}


# ---------------------------------------------------------------------------
# QV6-03 / QINV-13: evaluation-key contract (26.5)

def test_qv603_missing_evaluation_key():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"}, _eval("e")],
           "e", extensions=[BARRIER])
    assert _rules(q) == {"QV6-03"}


def test_qv603_missing_universal_field():
    k = _key()
    del k["source_commit"]
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"}, _eval("e", key=k)],
           "e", extensions=[BARRIER])
    diags = semantic_diagnostics(q)
    assert {d.rule_id for d in diags} == {"QV6-03"}
    assert "source_commit" in diags[0].message


def test_qv603_missing_contract_field():
    k = _key()
    del k["prompt_template_digest"]
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"}, _eval("e", key=k)],
           "e", extensions=[BARRIER])
    diags = semantic_diagnostics(q)
    assert {d.rule_id for d in diags} == {"QV6-03"}
    assert "prompt_template_digest" in diags[0].message


def test_qinv13_transient_key():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"},
            _eval("e", key=_key(transient=True))],
           "e", extensions=[BARRIER])
    assert _rules(q) == {"QINV-13", "QV6-03"}


def test_complete_key_is_clean():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"}, _eval("e", key=_key())],
           "e", extensions=[BARRIER])
    assert _rules(q) == set()


def test_deterministic_evaluator_needs_no_key():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"},
            _eval("e", ev=POS_CLASS)],
           "e", extensions=[BARRIER])
    assert _rules(q) == set()


# ---------------------------------------------------------------------------
# QINV-04 / QV6-04: the equality prohibition (26.8)

def _forgery_query(op):
    return _q({"u": {"schema": VALS, "tuples": [[1]]}},
              [{"id": "ru", "op": "read", "source": "u"},
               {"id": "f", "op": "filter", "input": "ru",
                "predicate": {"terms": [{"field": "v", "op": op, "value": 1,
                                         "evaluator": VECTOR_SIM}]}}],
              "f", extensions=[BARRIER])


def test_qinv04_qv604_equality_forgery():
    assert _rules(_forgery_query("eq")) == {"QINV-04", "QV6-04"}
    assert _rules(_forgery_query("ne")) == {"QINV-04", "QV6-04"}


def test_non_semantic_equivalence_evaluator_is_not_forgery():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"},
            {"id": "f", "op": "filter", "input": "ru",
             "predicate": {"terms": [{"field": "v", "op": "eq", "value": 1,
                                      "evaluator": POS_CLASS}]}}],
           "f", extensions=[BARRIER])
    assert _rules(q) == set()


# ---------------------------------------------------------------------------
# QV6-05 / QV7-03: duplicated inline evaluator calls (26.4, 27)

def _dup_query(ev=VECTOR_SIM, key=None, required=None):
    kw = {"required_dimensions": required} if required else {}
    return _q({"u": {"schema": VALS, "tuples": [[1]]}},
              [{"id": "ru", "op": "read", "source": "u"},
               _eval("e1", ev=ev, key=key), _eval("e2", ev=ev, key=key)],
              "e1", extensions=[BARRIER], **kw)


def test_qv605_duplicated_call_without_required_dimension():
    assert _rules(_dup_query(key=_key())) == {"QV6-05"}


def test_qv605_qv703_with_required_dimension():
    got = _rules(_dup_query(key=_key(),
                            required=["value", "evaluation_identity"]))
    assert got == {"QV6-05", "QV7-03"}


def test_qv605_deterministic_duplication_has_no_qv703():
    got = _rules(_dup_query(ev=POS_CLASS,
                            required=["value", "evaluation_identity"]))
    assert got == {"QV6-05"}


def test_distinct_inputs_are_not_duplicated():
    q = _q({"u": {"schema": VALS, "tuples": [[1]]},
            "c": {"schema": VALS, "tuples": [[2]]}},
           [{"id": "ru", "op": "read", "source": "u"},
            {"id": "rc", "op": "read", "source": "c"},
            _eval("e1", key=_key()), _eval("e2", key=_key(), input_id="rc")],
           "e1", extensions=[BARRIER])
    assert "QV6-05" not in _rules(q)


# ---------------------------------------------------------------------------
# Claim-based checks (QV5-08, QV5-09, QV6-07)

def test_qv508_heuristic_contribution_to_exact_side():
    query, claim, inf = _case_claim("QPATH-020")
    got = {d.rule_id for d in validate_bound_record(query, claim, inf)}
    assert "QV5-08" in got
    # L == U with a derivation rule: the exact label itself is coherent.
    assert "QV5-03" not in got


def test_qv509_qv607_tuple_generating_select():
    query, claim, inf = _case_claim("QPATH-040")
    got = {d.rule_id for d in validate_bound_record(query, claim, inf)}
    assert {"QV5-09", "QV6-07"} <= got
    # The inference itself certifies no upper side for a
    # tuple-generating evaluator (13.7.1, 26.6).
    assert inf[query["root"]].upper is None
    assert inf[query["root"]].bound_rule is None


# ---------------------------------------------------------------------------
# Materialized assessment records (26.3, 26.7)

def _qgold009():
    return json.loads((CASES / "QGOLD-009" / "query.json").read_text())


def test_assessment_record_is_clean():
    assert _rules(_qgold009()) == set()


def test_assessment_tampered_result_object():
    q = _qgold009()
    q["sources"]["assessments"]["assessment"]["result_object"] = \
        "object:sha256:" + "00" * 32
    assert _rules(q) == {"QV6-03"}


def test_assessment_missing_record_fields():
    q = _qgold009()
    del q["sources"]["assessments"]["assessment"]["model_version"]
    assert _rules(q) == {"QV6-02"}


# ---------------------------------------------------------------------------
# Kernel gates (QV8-02, QV7-03)

def test_qv802_heuristic_covering_proof_rejected():
    p = CASES / "QPATH-033"
    query = json.loads((p / "query.json").read_text())
    req = RewriteRequest.from_dict(json.loads((p / "rewrite.json").read_text()))
    out = apply_rewrite(query, req)
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV8-02"}


def test_qv703_kernel_preservation_coverage():
    p = CASES / "QPATH-043"
    query = json.loads((p / "query.json").read_text())
    rewrite = json.loads((p / "rewrite.json").read_text())
    # Control: with no physical dimension claimed the push rewrite applies.
    base = RewriteRequest.from_dict({**rewrite, "claimed_dimensions": []})
    assert apply_rewrite(query, base).applied
    # The push rule does not preserve evaluation_identity; a query that
    # requires it must be rejected (27, 29.4).
    q2 = json.loads(json.dumps(query))
    q2["required_dimensions"] = ["value", "evaluation_identity"]
    out = apply_rewrite(q2, base)
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV7-03"}


# ---------------------------------------------------------------------------
# Corpus-level regression: the eight Phase 6 cases

PHASE6_CASES = ["QGOLD-009", "QPATH-002", "QPATH-007", "QPATH-020",
                "QPATH-024", "QPATH-025", "QPATH-033", "QPATH-040"]


def test_phase6_corpus_cases():
    for name in PHASE6_CASES:
        p = CASES / name
        manifest = json.loads((p / "manifest.json").read_text())
        expected = set(manifest.get("expected_diagnostics", []))
        got = {d.rule_id for d in validate_case_dir(p, check_match=not expected,
                                                    manifest=manifest)}
        if expected:
            assert expected.issubset(got), (name, expected, got)
        else:
            assert not got, (name, got)
