"""Phase 4 tests: rewrite registry and application kernel (spec 25, 36.3,
37.4; gate conditions 5, 16, 18, 19).

Covers:
* registry shape (7 rules, 5 mandatory, 1 experimental, proof metadata);
* each rule applied to its golden pattern (or its honest Phase-4 gate);
* every QPATH rewrite case emits exactly its spec diagnostics;
* 36.3 adversarial sensitivity: removing the violated precondition
  changes the outcome (the rewrite applies, or the failure moves past
  the gate that was violated);
* certificate verification round-trip;
* rewrite_report determinism (byte-identical regeneration).
"""
import dataclasses
import json
from collections import Counter
from pathlib import Path

import pytest

from qryref.canonical import canonicalize_query
from qryref.check_certificate import check_file
from qryref.exact import execute_step
from qryref.make_rewrites_corpus import (
    A,
    B,
    C,
    PRED_Y,
    U,
    covering_proof,
    disclosure_proof_digest,
    gold_covering_proof_digest,
)
from qryref.property_tests import machine_summary_covering
from qryref.rewrites import (
    EXPERIMENTAL_RULE,
    MANDATORY_RULES,
    PHYSICAL_PROFILE_PUBLISHED,
    POLICY_RULE,
    RULES,
    RewriteRequest,
    _substitute_precondition_diagnostics,
    apply_rewrite,
    registry_report,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"
CERTS = ROOT / "certificates" / "rewrites"

PUSH_RULE = "sol:rewrite/push_exact_selection_through_join/v1"
PRUNE_RULE = "sol:rewrite/prune_exact_projection/v1"
ASSOC_RULE = "sol:rewrite/associate_exact_join/v1"
UNION_RULE = "sol:rewrite/normalize_union/v1"
SUBST_RULE = "sol:rewrite/substitute_exact_machine_summary/v1"

QPATH_CASES = [
    "QPATH-021", "QPATH-022", "QPATH-023", "QPATH-026", "QPATH-034",
    "QPATH-036", "QPATH-039", "QPATH-041", "QPATH-043", "QPATH-044",
    "QPATH-045", "QPATH-046",
]


def _case(case_id: str) -> tuple[dict, RewriteRequest, dict, dict]:
    d = CASES / case_id
    query = json.loads((d / "query.json").read_text())
    req = RewriteRequest.from_dict(json.loads((d / "rewrite.json").read_text()))
    expected = json.loads((d / "expected.json").read_text())
    manifest = json.loads((d / "manifest.json").read_text())
    return query, req, expected, manifest


def _equivalent(before: dict, after: dict) -> None:
    """Exact-evaluator multiset equivalence (the harness's own check)."""
    b, a = execute_step(before, 10**6), execute_step(after, 10**6)
    assert not b.diagnostics and not a.diagnostics
    assert Counter(map(tuple, b.rows)) == Counter(map(tuple, a.rows))


def _q(sources, nodes, root, **kw) -> dict:
    q = {"schema_version": "qry.query.v0.3", "query_id": "t",
         "sources": sources, "nodes": nodes, "root": root}
    q.update(kw)
    return q


# ---------------------------------------------------------------------------
# Registry shape (gate 5)

def test_registry_shape():
    assert len(RULES) == 7
    assert len(MANDATORY_RULES) == 5
    assert set(MANDATORY_RULES) <= set(RULES)
    assert POLICY_RULE in RULES and not RULES[POLICY_RULE].experimental
    assert EXPERIMENTAL_RULE in RULES and RULES[EXPERIMENTAL_RULE].experimental
    assert not PHYSICAL_PROFILE_PUBLISHED  # gate 19: physical claims not claimable
    for r in RULES.values():
        assert r.proof_evidence, r.rule_id
        assert r.preserves, r.rule_id
        assert (ROOT / "rewrites" / f"{r.derivation_slug}.md").exists(), r.rule_id
    # Every mandatory rule names an adversarial corpus case (37.4, gate 18).
    for rid in MANDATORY_RULES:
        corpus_refs = [ref for kind, ref in RULES[rid].proof_evidence
                       if kind == "adversarial_corpus"]
        assert corpus_refs, rid
        for ref in corpus_refs:
            assert (CASES / ref).is_dir(), f"{rid}: missing adversarial case {ref}"


def test_registry_report_shape():
    rep = registry_report()
    assert rep["format"] == "solqry-rewrite-registry/v1"
    assert rep["mandatory_rules"] == list(MANDATORY_RULES)
    assert len(rep["registered"]) == 6  # 5 mandatory + policy rule
    assert rep["experimental"] == [EXPERIMENTAL_RULE]
    assert len(rep["rules"]) == 7
    for rid, rec in rep["rules"].items():
        assert rec["rule_id"] == rid
        assert rec["proof_evidence"]  # evidence refs resolved to digests


# ---------------------------------------------------------------------------
# Golden patterns (each rule applies where its pattern matches)

@pytest.mark.parametrize("case_id", ["QGOLD-010", "QGOLD-021"])
def test_qgold_applied_and_recorded(case_id):
    query, req, expected, _ = _case(case_id)
    outcome = apply_rewrite(query, req)
    assert outcome.applied, [d.rule_id for d in outcome.diagnostics]
    assert canonicalize_query(outcome.rewritten_query) == \
        canonicalize_query(expected["rewritten_query"])
    for k, v in expected["record"].items():
        assert outcome.record[k] == v
    _equivalent(query, outcome.rewritten_query)


def test_prune_golden_pattern():
    q = _q({"a": A}, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "p", "op": "project", "input": "ra",
         "fields": [{"expr": "id", "name": "id"}, {"expr": "tag", "name": "tag"}]},
        {"id": "f", "op": "filter", "input": "p", "predicate": PRED_Y},
    ], "f")
    outcome = apply_rewrite(q, RewriteRequest(rule_id=PRUNE_RULE, location="node:p"))
    assert outcome.applied, [d.rule_id for d in outcome.diagnostics]
    p = next(n for n in outcome.rewritten_query["nodes"] if n["id"] == "p")
    assert [f["name"] for f in p["fields"]] == ["tag"]
    # Pruning legitimately drops the unused 'id' column: post rows are the
    # pre rows without that column.
    b, a = execute_step(q, 10**6), execute_step(outcome.rewritten_query, 10**6)
    assert not b.diagnostics and not a.diagnostics
    assert Counter(map(tuple, a.rows)) == Counter((row[1],) for row in b.rows)


def test_associate_golden_pattern():
    q = _q({"a": A, "b": B, "c": C}, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "rc", "op": "read", "source": "c"},
        {"id": "j1", "op": "join", "left": "ra", "right": "rb",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
        {"id": "j2", "op": "join", "left": "j1", "right": "rc",
         "join_type": "inner", "on": [{"left": "val", "right": "w"}]},
    ], "j2")
    outcome = apply_rewrite(q, RewriteRequest(rule_id=ASSOC_RULE, location="node:j2"))
    assert outcome.applied, [d.rule_id for d in outcome.diagnostics]
    _equivalent(q, outcome.rewritten_query)


def test_union_golden_pattern():
    q = _q({"a": U, "b": U, "c": U}, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "rc", "op": "read", "source": "c"},
        {"id": "u1", "op": "union_all", "inputs": ["ra", "rb"]},
        {"id": "u", "op": "union_all", "inputs": ["u1", "rc"]},
    ], "u")
    outcome = apply_rewrite(q, RewriteRequest(rule_id=UNION_RULE, location="node:u"))
    assert outcome.applied, [d.rule_id for d in outcome.diagnostics]
    u = next(n for n in outcome.rewritten_query["nodes"] if n["id"] == "u")
    assert u["inputs"] == ["ra", "rb", "rc"]
    _equivalent(q, outcome.rewritten_query)


def test_substitute_eligible_is_executable():
    """Phase 7 (37.7): a field-complete summary with a matching commit is
    a covering exact view; the eligible substitution applies and is
    recorded with the covering proof and the source-commit pin."""
    q = _q({"a": A}, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "f", "op": "filter", "input": "ra", "predicate": PRED_Y},
    ], "f")
    from qryref.canonical import source_manifest
    pin = source_manifest(q)["manifest_digest"]
    proof = {"format": "solqry-covering-proof/v1",
             "summary_fields": ["id", "tag"], "source_commit": pin}
    assert _substitute_precondition_diagnostics(q,
                                                RewriteRequest(rule_id=SUBST_RULE,
                                                               location="node:f",
                                                               covering_proof="object:sha256:" + "1" * 64,
                                                               source_commit=pin),
                                                proof) == []
    out = apply_rewrite(q, RewriteRequest(rule_id=SUBST_RULE, location="node:f",
                                          covering_proof=gold_covering_proof_digest(),
                                          source_commit=pin))
    assert out.applied, [d.rule_id for d in out.diagnostics]
    assert out.record["covering_proof"] == gold_covering_proof_digest()
    assert out.record["source_commit"] == pin


# ---------------------------------------------------------------------------
# QPATH cases emit exactly their spec diagnostics

@pytest.mark.parametrize("case_id", QPATH_CASES)
def test_qpath_exact_diagnostics(case_id):
    query, req, expected, manifest = _case(case_id)
    assert not expected["applied"]
    outcome = apply_rewrite(query, req)
    assert not outcome.applied
    assert {d.rule_id for d in outcome.diagnostics} == \
        set(manifest["expected_diagnostics"]), case_id


# ---------------------------------------------------------------------------
# 36.3 adversarial sensitivity: removing the violated precondition

def test_qpath021_registration_gate():
    """The violated precondition is registration (25.4.1). Registering the
    rule id moves the failure past the registration gate: QV7-01 becomes
    QV7-02 (registered but no supported transformation for that id)."""
    query, req, _, manifest = _case("QPATH-021")
    assert {d.rule_id for d in apply_rewrite(query, req).diagnostics} == {"QV7-01"}
    reg = dict(RULES)
    reg[req.rule_id] = dataclasses.replace(RULES[PUSH_RULE], rule_id=req.rule_id)
    out = apply_rewrite(query, req, registry=reg)
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV7-02"}


def test_qpath022_remove_evaluator_barrier():
    query, req, _, _ = _case("QPATH-022")
    q2 = json.loads(json.dumps(query))
    q2["nodes"] = [n for n in q2["nodes"] if n["id"] != "e"]
    for n in q2["nodes"]:
        if n.get("input") == "e":
            n["input"] = "ra"
    q2.pop("extensions", None)
    out = apply_rewrite(q2, req)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(q2, out.rewritten_query)


def test_qpath023_drop_stale_dependency():
    query, req, _, _ = _case("QPATH-023")
    q2 = json.loads(json.dumps(query))
    q2.pop("stale_dependencies")
    out = apply_rewrite(q2, req)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(query, out.rewritten_query)


def test_qpath026_supply_disclosure_proof():
    query, req, _, _ = _case("QPATH-026")
    req2 = RewriteRequest.from_dict({**req.__dict__,
                                     "disclosure_proof": disclosure_proof_digest()})
    out = apply_rewrite(query, req2)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(query, out.rewritten_query)


def test_qpath034_field_complete_summary_is_eligible():
    """Remove the violated precondition (the missing field): a
    field-complete summary with a matching commit is eligible (no
    precondition diagnostics), and a commit mismatch is QV8-03."""
    query, req, _, _ = _case("QPATH-034")
    from qryref.canonical import source_manifest
    pin = source_manifest(query)["manifest_digest"]
    proof = {"format": "solqry-covering-proof/v1",
             "summary_fields": ["id", "tag"], "source_commit": pin}
    assert _substitute_precondition_diagnostics(query, req, proof) == []
    proof_bad = {**proof, "source_commit": "object:sha256:" + "0" * 64}
    (rid, _c, _m), = _substitute_precondition_diagnostics(query, req, proof_bad)
    assert rid == "QV8-03"
    # The committed (lossy) proof is what the corpus case references.
    (rid, _c, _m), = _substitute_precondition_diagnostics(query, req, covering_proof())
    assert rid == "QV8-04"


def test_qpath036_experimental_rule_never_sole_basis():
    """25.8: the experimental rule is never the sole basis for an exact
    result. Its rejection is exactly QV7-06 and does not depend on the
    requested assurance; no transformation is applied in v0.3.0."""
    query, req, _, _ = _case("QPATH-036")
    out = apply_rewrite(query, req)
    assert not out.applied
    assert {d.rule_id for d in out.diagnostics} == {"QV7-06"}
    req2 = RewriteRequest.from_dict({**req.__dict__, "claimed_assurance": None})
    out2 = apply_rewrite(query, req2)
    assert not out2.applied
    assert {d.rule_id for d in out2.diagnostics} == {"QV7-06"}


def test_qpath039_supply_disclosure_proof():
    query, req, _, _ = _case("QPATH-039")
    req2 = RewriteRequest.from_dict({**req.__dict__,
                                     "disclosure_proof": disclosure_proof_digest()})
    out = apply_rewrite(query, req2)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(query, out.rewritten_query)


def test_qpath041_supply_checked_certificate_evidence():
    query, req, _, _ = _case("QPATH-041")
    req2 = RewriteRequest.from_dict({**req.__dict__,
                                     "evidence": [{"kind": "checked_certificate",
                                                   "ref": "object:sha256:" + "ab" * 32}]})
    out = apply_rewrite(query, req2)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(query, out.rewritten_query)


def test_qpath043_drop_claimed_dimension():
    query, req, _, _ = _case("QPATH-043")
    req2 = RewriteRequest.from_dict({**req.__dict__, "claimed_dimensions": []})
    out = apply_rewrite(query, req2)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(query, out.rewritten_query)


def test_qpath044_remove_downstream_consumer():
    query, req, _, _ = _case("QPATH-044")
    q2 = json.loads(json.dumps(query))
    q2["nodes"] = [n for n in q2["nodes"] if n["id"] != "f"]
    q2["root"] = "j"
    out = apply_rewrite(q2, req)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    # The prune drops the now-unused 'tag' column (second output column).
    b, a = execute_step(q2, 10**6), execute_step(out.rewritten_query, 10**6)
    assert not b.diagnostics and not a.diagnostics
    assert Counter(map(tuple, a.rows)) == Counter(
        (row[0], row[2], row[3]) for row in b.rows)


def test_qpath045_partitionable_condition():
    query, req, _, _ = _case("QPATH-045")
    q2 = json.loads(json.dumps(query))
    for n in q2["nodes"]:
        if n["id"] == "j2":
            n["on"] = [{"left": "val", "right": "w"}]
    out = apply_rewrite(q2, req)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(q2, out.rewritten_query)


def test_qpath046_nested_union():
    query, req, _, _ = _case("QPATH-046")
    q2 = json.loads(json.dumps(query))
    q2["nodes"] = [n for n in q2["nodes"] if n["id"] != "u"] + [
        {"id": "u1", "op": "union_all", "inputs": ["ra", "rb"]},
        {"id": "u", "op": "union_all", "inputs": ["u1", "rc"]},
    ]
    out = apply_rewrite(q2, req)
    assert out.applied, [d.rule_id for d in out.diagnostics]
    _equivalent(query, out.rewritten_query)


# ---------------------------------------------------------------------------
# Certificates and report determinism (gate 18)

def test_certificates_verify_roundtrip():
    files = sorted(CERTS.glob("*.json"))
    assert len(files) == 10  # 6 property certs + 3 covering proofs + registry
    for p in files:
        ok, detail = check_file(p)
        assert ok, (p.name, detail)


def test_rewrite_report_deterministic():
    import qryref.rewrite_report as rr
    snap1 = {p.name: p.read_bytes() for p in sorted(rr.OUT.glob("*.json"))}
    rr.main()
    snap2 = {p.name: p.read_bytes() for p in sorted(rr.OUT.glob("*.json"))}
    assert snap1 == snap2


def test_covering_decision_procedure():
    assert machine_summary_covering(["a", "b"], ["a", "b", "c"], "k", "k")
    assert not machine_summary_covering(["a", "b"], ["a"], "k", "k")
    assert not machine_summary_covering(["a"], ["a"], "k1", "k2")
