"""Machine-checkable property tests over generated finite instances (25.6).

Each mandatory rule gets a seeded generator of small finite instances.
For every instance the pre- and post-rewrite plans are evaluated with the
exact evaluator (full budget) and the rule's preservation property is
checked. The transcript (per-instance plan and result digests) is
committed as a certificate with a transcript digest;
``check_certificate`` re-runs the test and verifies the digest, which is
what makes the certificate *checked* (25.6: a checked certificate MAY
support ``proven`` assurance).
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from typing import Any

from .exact import execute_step

SEED = 20260909


def _q(sources: dict[str, Any], nodes: list[dict[str, Any]], root: str,
       extensions: list[str] | None = None) -> dict[str, Any]:
    q = {"schema_version": "qry.query.v0.3", "query_id": "pt",
         "sources": sources, "nodes": nodes, "root": root}
    if extensions:
        q["extensions"] = extensions
    return q


def _rows(query: dict[str, Any]) -> list[list[Any]]:
    r = execute_step(query, 10**6)
    assert not r.diagnostics, r.diagnostics
    assert r.status == "complete", r.status
    return [list(t) for t in r.rows]


def _digest(rows: list[list[Any]]) -> str:
    return "object:sha256:" + hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _gen_relation(rng: random.Random, max_rows: int = 4, value_range: int = 5) -> list[list[int]]:
    n = rng.randint(0, max_rows)
    return [[rng.randint(0, value_range)] for _ in range(n)]


def _entry(instance: int, before: list[list[Any]], after: list[list[Any]],
           order_sensitive: bool) -> dict[str, Any]:
    preserved = (before == after) if order_sensitive else (Counter(map(tuple, before)) == Counter(map(tuple, after)))
    return {"instance": instance,
            "before_digest": _digest(before), "after_digest": _digest(after),
            "preserved": preserved}


# ---------------------------------------------------------------------------
# push_exact_selection_through_join: value + multiplicity + order

def property_test_selection_pushdown(n: int = 256, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    transcript = []
    for i in range(n):
        a = _gen_relation(rng)
        b = _gen_relation(rng)
        k = rng.randint(0, 5)
        srcs = {"a": {"schema": [{"name": "v", "type": "i64"}], "tuples": a},
                "b": {"schema": [{"name": "v", "type": "i64"}], "tuples": b}}
        pred = {"terms": [{"field": "v", "op": "gte", "value": k}]}
        before = _q(srcs, [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "rb", "op": "read", "source": "b"},
            {"id": "f", "op": "filter", "input": "ra", "predicate": pred},
            {"id": "j", "op": "join", "left": "f", "right": "rb",
             "join_type": "inner", "on": [{"left": "v", "right": "v"}]},
        ], "j")
        after = _q(srcs, [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "rb", "op": "read", "source": "b"},
            {"id": "j", "op": "join", "left": "ra", "right": "rb",
             "join_type": "inner", "on": [{"left": "v", "right": "v"}]},
            {"id": "f2", "op": "filter", "input": "j", "predicate": pred},
        ], "f2")
        transcript.append(_entry(i, _rows(before), _rows(after), order_sensitive=True))
    return transcript


# ---------------------------------------------------------------------------
# prune_exact_projection: value + multiplicity + order

def property_test_projection_pruning(n: int = 256, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    transcript = []
    for i in range(n):
        rows = [[rng.randint(0, 5), rng.randint(0, 5)] for _ in range(rng.randint(0, 4))]
        srcs = {"s": {"schema": [{"name": "g", "type": "i64"}, {"name": "v", "type": "i64"}],
                      "tuples": rows}}
        before = _q(srcs, [
            {"id": "r", "op": "read", "source": "s"},
            {"id": "p1", "op": "project", "input": "r",
             "fields": [{"expr": "g", "name": "g"}, {"expr": "v", "name": "v"}]},
            {"id": "p2", "op": "project", "input": "p1", "fields": [{"expr": "g", "name": "g"}]},
        ], "p2")
        after = _q(srcs, [
            {"id": "r", "op": "read", "source": "s"},
            {"id": "p1", "op": "project", "input": "r", "fields": [{"expr": "g", "name": "g"}]},
            {"id": "p2", "op": "project", "input": "p1", "fields": [{"expr": "g", "name": "g"}]},
        ], "p2")
        transcript.append(_entry(i, _rows(before), _rows(after), order_sensitive=True))
    return transcript


# ---------------------------------------------------------------------------
# associate_exact_join: value + multiplicity (order not claimed)

def property_test_join_associativity(n: int = 4096, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    transcript = []
    for i in range(n):
        a = _gen_relation(rng, max_rows=3, value_range=3)
        b = _gen_relation(rng, max_rows=3, value_range=3)
        c = _gen_relation(rng, max_rows=3, value_range=3)
        srcs = {"a": {"schema": [{"name": "a", "type": "i64"}], "tuples": a},
                "b": {"schema": [{"name": "b", "type": "i64"}], "tuples": b},
                "c": {"schema": [{"name": "c", "type": "i64"}], "tuples": c}}
        before = _q(srcs, [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "rb", "op": "read", "source": "b"},
            {"id": "rc", "op": "read", "source": "c"},
            {"id": "j1", "op": "join", "left": "ra", "right": "rb",
             "join_type": "inner", "on": [{"left": "a", "right": "b"}]},
            {"id": "j2", "op": "join", "left": "j1", "right": "rc",
             "join_type": "inner", "on": [{"left": "b", "right": "c"}]},
        ], "j2")
        after = _q(srcs, [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "rb", "op": "read", "source": "b"},
            {"id": "rc", "op": "read", "source": "c"},
            {"id": "j1", "op": "join", "left": "rb", "right": "rc",
             "join_type": "inner", "on": [{"left": "b", "right": "c"}]},
            {"id": "j2", "op": "join", "left": "ra", "right": "j1",
             "join_type": "inner", "on": [{"left": "a", "right": "b"}]},
        ], "j2")
        transcript.append(_entry(i, _rows(before), _rows(after), order_sensitive=False))
    return transcript


# ---------------------------------------------------------------------------
# normalize_union: value + multiplicity + order

def property_test_union_normalization(n: int = 512, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    transcript = []
    for i in range(n):
        a = _gen_relation(rng)
        b = _gen_relation(rng)
        c = _gen_relation(rng)
        srcs = {"a": {"schema": [{"name": "v", "type": "i64"}], "tuples": a},
                "b": {"schema": [{"name": "v", "type": "i64"}], "tuples": b},
                "c": {"schema": [{"name": "v", "type": "i64"}], "tuples": c}}
        if i % 2 == 0:
            # union_all(a, union_all(b, c)) -> union_all(a, b, c)
            before = _q(srcs, [
                {"id": "ra", "op": "read", "source": "a"},
                {"id": "rb", "op": "read", "source": "b"},
                {"id": "rc", "op": "read", "source": "c"},
                {"id": "u1", "op": "union_all", "inputs": ["rb", "rc"]},
                {"id": "u2", "op": "union_all", "inputs": ["ra", "u1"]},
            ], "u2")
            after = _q(srcs, [
                {"id": "ra", "op": "read", "source": "a"},
                {"id": "rb", "op": "read", "source": "b"},
                {"id": "rc", "op": "read", "source": "c"},
                {"id": "u2", "op": "union_all", "inputs": ["ra", "rb", "rc"]},
            ], "u2")
        else:
            # union_distinct(a, a, b) -> union_distinct(a, b)
            before = _q(srcs, [
                {"id": "ra", "op": "read", "source": "a"},
                {"id": "rb", "op": "read", "source": "b"},
                {"id": "u", "op": "union_distinct", "inputs": ["ra", "ra", "rb"]},
            ], "u")
            after = _q(srcs, [
                {"id": "ra", "op": "read", "source": "a"},
                {"id": "rb", "op": "read", "source": "b"},
                {"id": "u", "op": "union_distinct", "inputs": ["ra", "rb"]},
            ], "u")
        transcript.append(_entry(i, _rows(before), _rows(after), order_sensitive=True))
    return transcript


# ---------------------------------------------------------------------------
# substitute_exact_machine_summary: eligibility decision procedure

def machine_summary_covering(query_fields: list[str], summary_fields: list[str],
                             query_commit: str, summary_commit: str) -> bool:
    """A machine summary is a covering exact view for a query only when
    every output field is present in levels 0-2 and the source commits
    match (Q18; QGOLD-005 / QPATH-034)."""
    return (set(query_fields) <= set(summary_fields)
            and query_commit == summary_commit)


def property_test_machine_summary_substitution(n: int = 256, seed: int = SEED) -> list[dict[str, Any]]:
    """Cross-check: the kernel's substitute-branch decision (QV8-03 commit
    match, QV8-04 field completeness, eligible) agrees with the covering
    decision procedure on generated finite instances."""
    from .canonical import source_manifest
    from .rewrites import (
        RewriteRequest,
        _substitute_precondition_diagnostics,
    )

    def decision(query: dict[str, Any], request: RewriteRequest,
                 proof: dict[str, Any]) -> str:
        diags = _substitute_precondition_diagnostics(query, request, proof)
        if not diags:
            return "eligible"
        (rid, _cat, _msg), = diags
        return rid

    rng = random.Random(seed)
    universe = ["f0", "f1", "f2", "f3", "f4"]
    commits = ["commit_41", "commit_42", "commit_43"]
    transcript = []
    for i in range(n):
        qf = [f for f, keep in zip(universe, [rng.random() < 0.6 for _ in universe]) if keep] or ["f0"]
        sf = [f for f, keep in zip(universe, [rng.random() < 0.6 for _ in universe]) if keep]
        qc, sc = rng.choice(commits), rng.choice(commits)
        commit_match = qc == sc
        # A query over one source that references exactly qf.
        srcs = {"s": {"schema": [{"name": f, "type": "i64"} for f in universe],
                      "tuples": [[rng.randint(0, 5)] * len(universe)
                                 for _ in range(rng.randint(0, 4))]}}
        query = _q(srcs, [
            {"id": "r", "op": "read", "source": "s"},
            {"id": "f", "op": "filter", "input": "r",
             "predicate": {"terms": [{"field": f, "op": "eq", "value": 0} for f in qf]}},
        ], "f")
        pin = source_manifest(query)["manifest_digest"]
        proof = {"format": "solqry-covering-proof/v1", "summary_fields": sf,
                 "source_commit": pin if commit_match else "object:sha256:" + "0" * 64}
        request = RewriteRequest(rule_id="sol:rewrite/substitute_exact_machine_summary/v1",
                                 location="node:f",
                                 covering_proof="object:sha256:" + "1" * 64,
                                 source_commit=pin)
        actual = decision(query, request, proof)
        covering = machine_summary_covering(qf, sf, qc, sc)
        expected = "eligible" if covering else ("QV8-03" if not commit_match else "QV8-04")
        transcript.append({"instance": i, "query_fields": qf, "summary_fields": sf,
                           "commit_match": commit_match,
                           "expected": expected, "actual": actual,
                           "preserved": expected == actual})
    return transcript


# ---------------------------------------------------------------------------
# push_filter_across_policy_with_disclosure_proof: visible-set equality

def property_test_disclosure_proof(n: int = 256, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    transcript = []
    for i in range(n):
        a = _gen_relation(rng)
        k = rng.randint(0, 5)
        pred = {"terms": [{"field": "v", "op": "gte", "value": k}]}
        srcs = {"a": {"schema": [{"name": "v", "type": "i64"}], "tuples": a}}
        # Before: A -> PB -> F. After: A -> F -> PB. PB is identity on the
        # relation; the visible output set must be unchanged.
        ext = ["urn:qry:v0.3:policy-boundary"]
        before = _q(srcs, [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "pb", "op": "policy_boundary", "input": "ra",
             "policy": "policy:authorization_restricted"},
            {"id": "f", "op": "filter", "input": "pb", "predicate": pred},
        ], "f", extensions=ext)
        after = _q(srcs, [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "f", "op": "filter", "input": "ra", "predicate": pred},
            {"id": "pb", "op": "policy_boundary", "input": "f",
             "policy": "policy:authorization_restricted"},
        ], "pb", extensions=ext)
        transcript.append(_entry(i, _rows(before), _rows(after), order_sensitive=True))
    return transcript


# ---------------------------------------------------------------------------
# Certificate assembly

TESTS = {
    "selection-pushdown": (property_test_selection_pushdown,
                           "value+multiplicity+order preservation under exact selection "
                           "pushdown through an inner join"),
    "projection-pruning": (property_test_projection_pruning,
                           "value+multiplicity+order preservation under exact projection pruning"),
    "join-associativity": (property_test_join_associativity,
                           "value+multiplicity preservation under exact join reassociation "
                           "(order not claimed)"),
    "union-normalization": (property_test_union_normalization,
                           "value+multiplicity+order preservation under union normalization"),
    "machine-summary-substitution": (property_test_machine_summary_substitution,
                                     "kernel cross-check: the substitute-branch decision "
                                     "(QV8-03 commit match, QV8-04 field completeness, "
                                     "eligible) agrees with the covering decision procedure"),
    "disclosure-proof": (property_test_disclosure_proof,
                         "visible-set equality when an exact filter is pushed across an "
                         "authorization boundary (the boundary is identity on the relation)"),
}

RULE_IDS = {
    "selection-pushdown": "sol:rewrite/push_exact_selection_through_join/v1",
    "projection-pruning": "sol:rewrite/prune_exact_projection/v1",
    "join-associativity": "sol:rewrite/associate_exact_join/v1",
    "union-normalization": "sol:rewrite/normalize_union/v1",
    "machine-summary-substitution": "sol:rewrite/substitute_exact_machine_summary/v1",
    "disclosure-proof": "sol:rewrite/push_filter_across_policy_with_disclosure_proof/v1",
}


def transcript_digest(transcript: list[dict[str, Any]]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(transcript, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_certificate(slug: str) -> dict[str, Any]:
    fn, property_ = TESTS[slug]
    transcript = fn()
    assert all(e["preserved"] for e in transcript), \
        f"property test failed for {slug}: " + str([e for e in transcript if not e["preserved"]][:3])
    return {
        "schema_version": "solqry.rewrite-certificate/v1",
        "rule_id": RULE_IDS[slug],
        "rule_slug": slug,
        "seed": SEED,
        "cases": len(transcript),
        "property": property_,
        "transcript": transcript,
        "transcript_digest": transcript_digest(transcript),
    }


def verify_certificate(cert: dict[str, Any]) -> tuple[bool, str]:
    """Re-run the property test and verify the committed transcript."""
    slug = cert.get("rule_slug")
    if slug not in TESTS:
        return False, f"unknown rule_slug {slug!r}"
    if cert.get("seed") != SEED:
        return False, "seed mismatch"
    try:
        transcript = TESTS[slug][0]()
    except Exception as e:
        return False, f"property test failed to run: {e}"
    if not all(e["preserved"] for e in transcript):
        return False, "property test failed on re-run"
    if transcript_digest(transcript) != cert.get("transcript_digest"):
        return False, "transcript digest mismatch"
    if len(transcript) != cert.get("cases"):
        return False, "case count mismatch"
    return True, "verified"
