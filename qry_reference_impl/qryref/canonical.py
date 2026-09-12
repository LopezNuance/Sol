"""Typed-AST canonicalization, query digests, and source manifests.

Implements spec section 29: the AST (not the surface syntax) is the unit
of canonicalization, hashing, signing, validation, plan caching, rewrite
provenance, and execution identity (29.1). Canonicalization is
deterministic and idempotent; the query digest covers the canonical
expression, source manifest, semantic modes, policies, and extension
declarations (29.4). Unknown required extensions fail validation
(29.5) -- the op-level requirement is enforced in engine.py.

Normalization rules (representation, not semantics):
  * dict keys sorted (canonical JSON);
  * nodes in deterministic topological order from the root;
  * sources sorted by name;
  * set-valued data (tuples, lower/upper tuples, unique_keys) sorted;
  * commutative operand lists (union/intersect/difference inputs,
    AND predicate terms) sorted;
  * cosmetic metadata ("description") excluded from the identity.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .engine import input_ids  # shared input extraction (v0.1 + v0.3 ops)


def _tuple_key(t: Any) -> str:
    return json.dumps(t, sort_keys=True)


def _canon_value(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _canon_value(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [_canon_value(x) for x in v]
    return v


def canonical_source(src: dict[str, Any]) -> dict[str, Any]:
    """Canonical form of one source declaration.

    The schema field order is preserved (it is the relation's column
    order, part of its identity); set-valued data is sorted.
    """
    out: dict[str, Any] = {}
    if "schema" in src:
        out["schema"] = [dict(f) for f in src["schema"]]
    if "rows" in src:
        out["rows"] = dict(src["rows"])
    if "unique_keys" in src:
        out["unique_keys"] = sorted(tuple(k) for k in src["unique_keys"])
    if "artifact" in src:
        out["artifact"] = dict(src["artifact"])
    if "assessment" in src:
        # The materialized assessment record (26.3, 26.7) is part of
        # the source identity: the query digest and source manifest
        # must reflect the recorded evaluation.
        out["assessment"] = dict(src["assessment"])
    if "latest" in src:
        # The latest-commit selection (17.5) is part of the source
        # identity: the commit resolution is part of what the query
        # asks for.
        out["latest"] = dict(src["latest"])
    if "machine_summary" in src:
        # The machine-summary annotation (28.3, 28.5) is part of the
        # source identity: the evaluation path and its pins are part
        # of the query.
        out["machine_summary"] = dict(src["machine_summary"])
    for key in ("tuples", "lower", "upper"):
        if key in src:
            if key == "tuples":
                out["tuples"] = sorted(src["tuples"], key=_tuple_key)
            else:
                inner = src[key]
                side = {"tuples": sorted(inner.get("tuples", []), key=_tuple_key)}
                if "commit" in inner:
                    # Per-side commit pin is part of the side's identity
                    # (QV1-05: lower/upper must use compatible manifests).
                    side["commit"] = inner["commit"]
                out[key] = side
    # Source-level facts are part of the source identity (QV1-01/02/05,
    # QV2-05, QV3-01/02, QINV-06, QV8-08/QV9-04): the query digest and
    # source manifest must reflect them.
    for key in ("approximate", "bag", "branch", "commit", "restricted",
                "unbounded"):
        if key in src:
            out[key] = src[key]
    return {k: _canon_value(v) for k, v in sorted(out.items())}


def _canonical_node(n: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in n.items() if k not in {"id", "op"}}
    # Commutative operand lists: sort for determinism (set semantics, QINV-03).
    if n.get("op") in {"union_all", "union_distinct", "intersect", "difference"}:
        out["inputs"] = sorted(n.get("inputs", []))
    pred = n.get("predicate")
    if isinstance(pred, dict) and "terms" in pred:
        pred = dict(pred)
        pred["terms"] = sorted(pred["terms"], key=lambda t: json.dumps(t, sort_keys=True))
        out["predicate"] = pred
    out = _canon_value(out)
    return {"id": n["id"], "op": n["op"], **out}


def _topo_nodes(query: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {n["id"]: n for n in query.get("nodes", [])}
    order: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(nid: str | None) -> None:
        if not nid or nid in seen or nid not in nodes:
            return
        seen.add(nid)
        for inp in sorted(input_ids(nodes[nid])):
            visit(inp)
        order.append(_canonical_node(nodes[nid]))

    visit(query.get("root"))
    for nid in sorted(nodes):
        if nid not in seen:
            order.append(_canonical_node(nodes[nid]))
    return order


def canonicalize_query(query: dict[str, Any]) -> dict[str, Any]:
    """Deterministic canonical form of a v0.1/v0.3 query (29.1, 29.4)."""
    sources = {
        name: canonical_source(query["sources"][name])
        for name in sorted(query.get("sources") or {})
    }
    out = {
        "schema_version": query.get("schema_version", "qry.query.v0.1"),
        "query_id": query.get("query_id"),
        "sources": sources,
        "nodes": _topo_nodes(query),
        "root": query.get("root"),
        "extensions": sorted(query.get("extensions", [])),
        "stale_dependencies": sorted(query.get("stale_dependencies", [])),
    }
    # Required equivalence dimensions (27, 29.4) are part of the query
    # identity only when declared; an absent field and an empty list
    # are equivalent, so existing digests are unchanged.
    rd = sorted(query.get("required_dimensions") or [])
    if rd:
        out["required_dimensions"] = rd
    # The leakage policy (32) is part of the query identity (29.4): the
    # disclosure commitments the query makes are part of what it asks
    # for.
    lp = query.get("leakage_policy")
    if lp:
        out["leakage_policy"] = _canon_value(lp)
    return out


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def query_digest(query: dict[str, Any]) -> str:
    """Content digest of the canonical query (29.4)."""
    return "digest:sha256:" + hashlib.sha256(canonical_json(canonicalize_query(query)).encode("utf-8")).hexdigest()


def source_manifest(query: dict[str, Any]) -> dict[str, Any]:
    """Content-addressed source manifest (29.4: the digest includes the
    source manifest; 30.3: continuations bind to the same manifest)."""
    digests = {
        name: "object:sha256:" + hashlib.sha256(canonical_json(canonical_source(src)).encode("utf-8")).hexdigest()
        for name, src in sorted((query.get("sources") or {}).items())
    }
    manifest_digest = "object:sha256:" + hashlib.sha256(canonical_json(digests).encode("utf-8")).hexdigest()
    return {"sources": digests, "manifest_digest": manifest_digest}
