"""Generate the Phase 4 rewrite corpus cases (spec 36.1/36.2, 37.4).

QGOLD-010, QGOLD-021; QPATH-021, QPATH-022, QPATH-023, QPATH-026,
QPATH-034, QPATH-036, QPATH-039, QPATH-041, QPATH-043, QPATH-044,
QPATH-045, QPATH-046.

Every mandatory rewrite rule carries at least one adversarial corpus case
(37.4, gate 18): QPATH-022 (selection pushdown), QPATH-044 (projection
pruning), QPATH-045 (join associativity), QPATH-046 (union normalization),
QPATH-034 (machine-summary substitution, normative per 36.2).

Each case directory holds query.json (the pre-rewrite plan), rewrite.json
(the rewrite request), expected.json (the expected outcome), and
manifest.json (expected diagnostics). The expected rewritten queries are
hand-specified, not derived from the implementation; exact-result
equivalence is independently machine-checked by the harness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .canonical import source_manifest

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"

A = {"schema": [{"name": "id", "type": "i64", "nullable": False},
                {"name": "tag", "type": "string", "nullable": False}],
     "tuples": [[1, "x"], [2, "y"], [3, "z"]]}
B = {"schema": [{"name": "id", "type": "i64", "nullable": False},
                {"name": "val", "type": "i64", "nullable": False}],
     "tuples": [[1, 10], [2, 20], [4, 40]]}

PUSH_RULE = "sol:rewrite/push_exact_selection_through_join/v1"
PRUNE_RULE = "sol:rewrite/prune_exact_projection/v1"
ASSOC_RULE = "sol:rewrite/associate_exact_join/v1"
UNION_RULE = "sol:rewrite/normalize_union/v1"
SUBST_RULE = "sol:rewrite/substitute_exact_machine_summary/v1"
POLICY_RULE = "sol:rewrite/push_filter_across_policy_with_disclosure_proof/v1"
EXPERIMENTAL_RULE = "sol:rewrite/experimental_aggregate_fold/v1"

C = {"schema": [{"name": "id", "type": "i64", "nullable": False},
                {"name": "w", "type": "i64", "nullable": False}],
     "tuples": [[1, 100], [2, 200], [5, 500]]}
U = {"schema": [{"name": "v", "type": "i64", "nullable": False}],
     "tuples": [[1], [2]]}

PRED_Y = {"terms": [{"field": "tag", "op": "eq", "value": "y"}]}


def _q(query_id: str, nodes, root, sources=None, **kw) -> dict:
    q = {"schema_version": "qry.query.v0.3", "query_id": query_id,
         "sources": sources if sources is not None else {"a": A, "b": B},
         "nodes": nodes, "root": root}
    q.update(kw)
    return q


def _push_plan(qid: str, **kw) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "f", "op": "filter", "input": "ra", "predicate": PRED_Y},
        {"id": "j", "op": "join", "left": "f", "right": "rb",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
    ], "j", **kw)


def _pushed_plan(qid: str) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "j", "op": "join", "left": "ra", "right": "rb",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
        {"id": "j__pushed", "op": "filter", "input": "j", "predicate": PRED_Y},
    ], "j__pushed")


def _policy_plan(qid: str, policy: str) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "pb", "op": "policy_boundary", "input": "ra", "policy": policy},
        {"id": "f", "op": "filter", "input": "pb", "predicate": PRED_Y},
    ], "f", sources={"a": A}, extensions=["urn:qry:v0.3:policy-boundary"])


def _pushed_policy_plan(qid: str, policy: str) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "f", "op": "filter", "input": "ra", "predicate": PRED_Y},
        {"id": "pb", "op": "policy_boundary", "input": "f", "policy": policy},
    ], "pb", sources={"a": A}, extensions=["urn:qry:v0.3:policy-boundary"])


def _eval_plan(qid: str) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "e", "op": "evaluate", "input": "ra",
         "evaluator": "sol:evaluator/positive_classifier/v1", "mode": "heuristic"},
        {"id": "f", "op": "filter", "input": "e", "predicate": PRED_Y},
        {"id": "j", "op": "join", "left": "f", "right": "rb",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
    ], "j", extensions=["urn:qry:v0.3:semantic-evaluator-barrier"])


def _agg_plan(qid: str) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "ag", "op": "aggregate", "input": "ra", "group_by": ["tag"],
         "aggregates": [{"func": "count_set", "field": "id", "name": "c"}]},
    ], "ag", sources={"a": A})


def _prune_path_plan(qid: str) -> dict:
    """Every output column of the projection is used downstream
    (join on id, filter on tag): pruning is not licensed (QV7-02)."""
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "p", "op": "project", "input": "ra",
         "fields": [{"expr": "id", "name": "id"}, {"expr": "tag", "name": "tag"}]},
        {"id": "j", "op": "join", "left": "p", "right": "rb",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
        {"id": "f", "op": "filter", "input": "j", "predicate": PRED_Y},
    ], "f")


def _assoc_path_plan(qid: str) -> dict:
    """The outer join's on-condition names a field of the right input
    (w), so the conditions do not partition over the inner join's sides
    (QV7-02)."""
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "rc", "op": "read", "source": "c"},
        {"id": "j1", "op": "join", "left": "ra", "right": "rb",
         "join_type": "inner", "on": [{"left": "id", "right": "id"}]},
        {"id": "j2", "op": "join", "left": "j1", "right": "rc",
         "join_type": "inner", "on": [{"left": "w", "right": "id"}]},
    ], "j2", sources={"a": A, "b": B, "c": C})


def _union_path_plan(qid: str) -> dict:
    """A flat union of distinct inputs: nothing to normalize (QV7-02)."""
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "rb", "op": "read", "source": "b"},
        {"id": "rc", "op": "read", "source": "c"},
        {"id": "u", "op": "union_all", "inputs": ["ra", "rb", "rc"]},
    ], "u", sources={"a": U, "b": U, "c": U})


def _subst_plan(qid: str) -> dict:
    return _q(qid, [
        {"id": "ra", "op": "read", "source": "a"},
        {"id": "f", "op": "filter", "input": "ra", "predicate": PRED_Y},
    ], "f", sources={"a": A})


def covering_proof() -> dict:
    """The committed covering proof for QPATH-034: a lossy machine summary
    (fields [id] only) computed against the exact source manifest of the
    case query. Written by rewrite_report as covering-proof.json."""
    return {
        "format": "solqry-covering-proof/v1",
        "summary_fields": ["id"],
        "source_commit": source_manifest({"sources": {"a": A}})["manifest_digest"],
        "summary_levels": [0, 1, 2],
        "note": "QPATH-034: lossy summary - omits 'tag', which the query requires.",
    }


def covering_proof_digest() -> str:
    import json as _json
    blob = _json.dumps(covering_proof(), indent=2, sort_keys=True) + "\n"
    return "object:sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def gold_covering_proof() -> dict:
    """The committed covering proof for QGOLD-005: a field-complete
    exact machine summary (levels 0-2) computed against the exact source
    manifest of the case query. It covers the query's fields and matches
    the source commit, so the substitution applies (28.3, 28.5). Written
    by rewrite_report as covering-proof-gold.json."""
    return {
        "format": "solqry-covering-proof/v1",
        "summary_fields": ["id", "tag"],
        "source_commit": source_manifest({"sources": {"a": A}})["manifest_digest"],
        "summary_levels": [0, 1, 2],
        "note": "QGOLD-005: field-complete exact machine summary (levels 0-2) "
                "computed against the source manifest.",
    }


def gold_covering_proof_digest() -> str:
    import json as _json
    blob = _json.dumps(gold_covering_proof(), indent=2, sort_keys=True) + "\n"
    return "object:sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def heuristic_covering_proof() -> dict:
    """The committed covering proof for QPATH-033: a field-complete
    machine summary produced by a heuristic semantic evaluator. It
    covers the query's fields and matches the source commit, but it is
    not a covering exact view (QV8-02). Written by rewrite_report as
    covering-proof-heuristic.json."""
    return {
        "format": "solqry-covering-proof/v1",
        "summary_fields": ["id", "tag"],
        "source_commit": source_manifest({"sources": {"a": A}})["manifest_digest"],
        "summary_levels": [0, 1, 2],
        "guarantee": "heuristic",
        "evaluator": "sol:evaluator/semantic_equivalence/v1",
        "note": "QPATH-033: field-complete summary produced heuristically; "
                "not a covering exact view.",
    }


def heuristic_covering_proof_digest() -> str:
    import json as _json
    blob = _json.dumps(heuristic_covering_proof(), indent=2, sort_keys=True) + "\n"
    return "object:sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def disclosure_proof_digest() -> str:
    p = ROOT / "certificates" / "rewrites" / "disclosure-proof.json"
    return "object:sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def build() -> list[tuple[str, dict, dict, dict, list[str], str]]:
    """(case_id, query, rewrite, expected, expected_diagnostics, description)"""
    out = []
    # QGOLD-010: registered rewrite with complete precondition and proof metadata.
    out.append(("QGOLD-010", _push_plan("QGOLD-010"),
                {"rule_id": PUSH_RULE, "location": "node:j"},
                {"applied": True, "rewritten_query": _pushed_plan("QGOLD-010"),
                 "record": {"rule_id": PUSH_RULE, "location": "node:j",
                            "assurance": "proven"}},
                [], "Registered rewrite with complete precondition and proof metadata."))
    # QGOLD-021: policy-boundary rewrite with an explicit accepted disclosure proof.
    out.append(("QGOLD-021", _policy_plan("QGOLD-021", "policy:authorization_restricted"),
                {"rule_id": POLICY_RULE, "location": "node:pb",
                 "disclosure_proof": disclosure_proof_digest()},
                {"applied": True,
                 "rewritten_query": _pushed_policy_plan("QGOLD-021", "policy:authorization_restricted"),
                 "record": {"rule_id": POLICY_RULE, "location": "node:pb",
                            "assurance": "proven"}},
                [], "A policy-boundary rewrite with an explicit accepted disclosure proof is applied and recorded."))
    # QPATH-021: the unregistered rewrite.
    out.append(("QPATH-021", _push_plan("QPATH-021"),
                {"rule_id": "sol:rewrite/unregistered_transform/v1", "location": "node:j"},
                {"applied": False},
                ["QV7-01"], "The unregistered rewrite: optimizer applies a transformation with no rule ID."))
    # QPATH-022: the unmet precondition (evaluator barrier).
    out.append(("QPATH-022", _eval_plan("QPATH-022"),
                {"rule_id": PUSH_RULE, "location": "node:j"},
                {"applied": False},
                ["QV7-02", "QV6-05"],
                "The unmet precondition: selection pushdown crosses a stochastic evaluator barrier."))
    # QPATH-023: the stale proof.
    out.append(("QPATH-023",
                _push_plan("QPATH-023", stale_dependencies=["record:verification_044"]),
                {"rule_id": PUSH_RULE, "location": "node:j",
                 "claimed_assurance": "validated"},
                {"applied": False},
                ["QV5-10", "QV7-04"],
                "The stale proof: the rule relies on a verification whose dependencies are stale."))
    # QPATH-026: the policy-crossing rewrite (authorization, no proof).
    out.append(("QPATH-026", _policy_plan("QPATH-026", "policy:authorization_restricted"),
                {"rule_id": POLICY_RULE, "location": "node:pb"},
                {"applied": False},
                ["QV7-07", "QV9-09"],
                "The policy-crossing rewrite: the plan moves a filter across an authorization boundary "
                "and changes tuple-existence disclosure."))
    # QPATH-036: the experimental theorem.
    out.append(("QPATH-036", _agg_plan("QPATH-036"),
                {"rule_id": EXPERIMENTAL_RULE, "location": "node:ag",
                 "claimed_assurance": "validated"},
                {"applied": False},
                ["QV7-06"],
                "The experimental theorem: an unverified rewrite rule is the sole basis for an exact result."))
    # QPATH-039: the policy-boundary default bypass (leakage, fixture value match).
    out.append(("QPATH-039", _policy_plan("QPATH-039", "policy:leakage_bucketed"),
                {"rule_id": POLICY_RULE, "location": "node:pb",
                 "justification": "visible values match in the fixture"},
                {"applied": False},
                ["QINV-15", "QV7-07"],
                "The policy-boundary default bypass: a rewrite spans a LeakagePolicy node with no explicit "
                "disclosure proof, even though visible values happen to match in the fixture."))
    # QPATH-041: the prose theorem.
    out.append(("QPATH-041", _push_plan("QPATH-041"),
                {"rule_id": PUSH_RULE, "location": "node:j",
                 "claimed_assurance": "proven",
                 "evidence": [{"kind": "formal_derivation", "ref": "prose:derivation.md"}]},
                {"applied": False},
                ["QV7-08"],
                "The prose theorem: a rewrite marks assurance as proven using only an unchecked prose reference."))
    # QPATH-043: the physical-leakage shortcut.
    out.append(("QPATH-043", _push_plan("QPATH-043"),
                {"rule_id": PUSH_RULE, "location": "node:j",
                 "claimed_dimensions": ["physical_side_channel_class"]},
                {"applied": False},
                ["QV7-09", "QV9-10"],
                "The physical-leakage shortcut: a logical rewrite declares evaluator-invocation-count "
                "equivalence without a physical conformance profile."))
    # QPATH-044: the over-pruned projection (prune_exact_projection).
    out.append(("QPATH-044", _prune_path_plan("QPATH-044"),
                {"rule_id": PRUNE_RULE, "location": "node:p"},
                {"applied": False},
                ["QV7-02"],
                "The over-pruned projection: a projection is pruned although every output "
                "column is still used downstream."))
    # QPATH-045: the unpartitionable reassociation (associate_exact_join).
    out.append(("QPATH-045", _assoc_path_plan("QPATH-045"),
                {"rule_id": ASSOC_RULE, "location": "node:j2"},
                {"applied": False},
                ["QV7-02"],
                "The unpartitionable reassociation: the outer join's on-condition names a field "
                "of the right input, so the conditions do not partition over the inner join."))
    # QPATH-046: the needless union normalization (normalize_union).
    out.append(("QPATH-046", _union_path_plan("QPATH-046"),
                {"rule_id": UNION_RULE, "location": "node:u"},
                {"applied": False},
                ["QV7-02"],
                "The needless union normalization: a flat union of distinct inputs is claimed "
                "normalizable."))
    # QPATH-034: the lossy summary (substitute_exact_machine_summary, 36.2).
    out.append(("QPATH-034", _subst_plan("QPATH-034"),
                {"rule_id": SUBST_RULE, "location": "node:f",
                 "covering_proof": covering_proof_digest(),
                 "source_commit": source_manifest({"sources": {"a": A}})["manifest_digest"]},
                {"applied": False},
                ["QV8-04"],
                "The lossy summary: the machine summary omits a field required by the query "
                "but is used as a covering exact view."))
    return out


def main() -> int:
    for case_id, query, rewrite, expected, diags, desc in build():
        d = CASES / case_id
        d.mkdir(parents=True, exist_ok=True)
        for name, obj in (("query.json", query), ("rewrite.json", rewrite),
                          ("expected.json", expected),
                          ("manifest.json", {"case_id": case_id, "description": desc,
                                             "expected_diagnostics": diags})):
            p = d / name
            p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
            p.chmod(0o644)
    print(f"wrote 14 rewrite corpus cases under {CASES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
