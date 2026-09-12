"""Substrait mapping for the QRY v0.3 AST.

Standard relational nodes map to Substrait relation concepts; Sol-specific
semantics are carried by declared extensions rather than by changing the
meaning of standard nodes (spec 29.2). The mapping profile is documented in
substrait/mapping.md and machine-readable in substrait/qry_substrait_profile.yaml;
its content digest is recorded in substrait/mapping_digest.json (gate 4).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .diagnostics import Diagnostic, diag

# QRY op -> Substrait relation concept (profile: substrait/qry_substrait_profile.yaml)
OP_TO_SUBSTRAIT = {
    "read": "ReadRel",
    "filter": "FilterRel",
    "project": "ProjectRel",
    "rename": "ProjectRel",
    "sort": "SortRel",
    "limit": "FetchRel",
    "distinct": "AggregateRel",
    "aggregate": "AggregateRel",
    "join": "JoinRel",
    "union_all": "SetRel",
    "union_distinct": "SetRel",
    "intersect": "SetRel",
    "difference": "SetRel",
    "annotate": "ProjectRel",
    "evaluate": "ExtensionRel",
    "least_fixpoint": "ExtensionRel",
    "temporal_slice": "FilterRel",
    "policy_boundary": "ExtensionRel",
}

# Ops whose Substrait representation is a declared Sol extension (29.2).
OP_EXTENSIONS = {
    "evaluate": ["urn:qry:v0.3:semantic-evaluator-barrier"],
    "least_fixpoint": ["urn:qry:v0.3:positive-recursion"],
    "temporal_slice": ["urn:qry:v0.3:valid-time"],
    "policy_boundary": ["urn:qry:v0.3:policy-boundary"],
}

# Substrait SetRel op kinds. union_all is bag union (11.2: bag semantics are
# explicit); union_distinct is set union (set semantics is the default, QINV-03).
SET_OP_KIND = {
    "union_all": "UNION",
    "union_distinct": "UNION_DISTINCT",
    "intersect": "INTERSECT",
    "difference": "MINUS",
}


def validate_substrait_profile(query: dict[str, Any]) -> list[Diagnostic]:
    """Every op in the query must be inside the mapping profile; unmapped
    ops produce a deterministic diagnostic (gate 4 acceptance)."""
    out: list[Diagnostic] = []
    for n in query.get("nodes", []):
        op = n.get("op")
        if op not in OP_TO_SUBSTRAIT:
            out.append(diag("QRY-SUBSTRAIT-001", "substrait_unsupported_op", f"node:{n.get('id')}",
                            f"Operation {op!r} is outside the QRY Substrait mapping profile"))
    return out


def to_substrait_like(query: dict[str, Any]) -> dict[str, Any]:
    """Produce the Substrait-like JSON mapping for a query.

    This is the documented interchange form (not a protobuf serializer);
    the profile in substrait/qry_substrait_profile.yaml defines the mapping.
    """
    extensions: set[str] = set(query.get("extensions", []))
    for n in query.get("nodes", []):
        extensions.update(OP_EXTENSIONS.get(n.get("op"), []))
    relations = []
    for n in query.get("nodes", []):
        op = n.get("op")
        entry: dict[str, Any] = {
            "node_id": n.get("id"),
            "substrait_rel": OP_TO_SUBSTRAIT.get(op, "Unmapped"),
            "qry_op": op,
        }
        if op in SET_OP_KIND:
            entry["set_op"] = SET_OP_KIND[op]
        if op in OP_EXTENSIONS:
            entry["extensions"] = OP_EXTENSIONS[op]
        detail = {k: v for k, v in n.items() if k not in {"id", "op", "inputs", "left", "right"}}
        if n.get("op") in {"union_all", "union_distinct", "intersect", "difference"}:
            detail["inputs"] = n.get("inputs", [])
        if n.get("op") == "join":
            detail["left"] = n.get("left")
            detail["right"] = n.get("right")
        if detail:
            entry["detail"] = detail
        relations.append(entry)
    return {
        "version": {"minorNumber": 3, "producer": "qryref.v0.3"},
        "extensions": sorted(extensions),
        "roots": [{"input": query.get("root"), "names": []}],
        "relations": relations,
    }


def profile_path() -> Path:
    return Path(__file__).resolve().parents[1] / "substrait" / "qry_substrait_profile.yaml"


def profile_digest() -> str:
    """Content digest of the mapping profile (gate 4: recorded mapping_digest)."""
    profile = yaml.safe_load(profile_path().read_text())
    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_profile_digest(recorded_path: Path | None = None) -> list[Diagnostic]:
    """Verify the recorded mapping digest matches the profile content."""
    recorded_path = recorded_path or profile_path().parent / "mapping_digest.json"
    if not recorded_path.exists():
        return [diag("QRY-SUBSTRAIT-002", "missing_mapping_digest", str(recorded_path),
                     "Recorded mapping digest missing")]
    recorded = json.loads(recorded_path.read_text())
    actual = profile_digest()
    if recorded.get("mapping_digest") != actual:
        return [diag("QRY-SUBSTRAIT-002", "mapping_digest_mismatch", str(recorded_path),
                     f"Recorded mapping digest {recorded.get('mapping_digest')} != profile digest {actual}")]
    return []
