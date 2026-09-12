"""Rewrite registry and application kernel (spec 25, 37.4).

Implements freeze-gate conditions 5, 16, and 18:

* the registered rewrite-rule records of 25.2 (rule ID, preconditions,
  preservation dimensions, proof evidence, pathology tests);
* the 25.4 application checks (registration, preconditions, preservation,
  evaluator barriers, context compatibility, evidence currency, effective
  assurance, physical-profile backing);
* the 25.5 conservative policy-boundary default: a rewrite that crosses,
  removes, duplicates, reorders, or fuses a policy or evaluator boundary
  is non-preserving by default (QV7-07) unless the registered rule
  explicitly proves the required logical-disclosure behavior;
* the 25.6 proof-evidence discipline: prose alone MUST NOT support
  `proven` (QV7-08); experimental rules are never the sole basis for an
  exact result (QV7-06); physical side-channel claims require a physical
  conformance profile (QV7-09).

The five mandatory rules (Q6) plus the registered policy-boundary rule are
normative; one experimental rule is registered per 25.8.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .canonical import source_manifest
from .diagnostics import Diagnostic, diag

ROOT = Path(__file__).resolve().parents[1]

# A physical conformance profile (25.3) is not published for v0.3.0;
# physical side-channel claims are therefore not claimable.
PHYSICAL_PROFILE_PUBLISHED = False

MANDATORY_RULES = (
    "sol:rewrite/push_exact_selection_through_join/v1",
    "sol:rewrite/prune_exact_projection/v1",
    "sol:rewrite/associate_exact_join/v1",
    "sol:rewrite/normalize_union/v1",
    "sol:rewrite/substitute_exact_machine_summary/v1",
)

POLICY_RULE = "sol:rewrite/push_filter_across_policy_with_disclosure_proof/v1"
EXPERIMENTAL_RULE = "sol:rewrite/experimental_aggregate_fold/v1"


@dataclass(frozen=True)
class RewriteRule:
    rule_id: str
    pattern: str
    replacement: str
    requires: dict[str, Any]
    preserves: tuple[str, ...]
    # (kind, ref_or_slug): derivation and certificate refs are resolved
    # from committed files at report time (the files must exist then);
    # adversarial_corpus refs are case IDs, contract refs are opaque.
    proof_evidence: tuple[tuple[str, str], ...]
    verification_refs: tuple[str, ...]
    pathology_tests: tuple[str, ...]
    derivation_slug: str
    assurance: str
    experimental: bool = False

    def resolved_evidence(self) -> list[dict[str, Any]]:
        out = []
        for kind, ref in self.proof_evidence:
            if kind == "formal_derivation":
                p = ROOT / "rewrites" / f"{ref}.md"
                out.append({"kind": kind,
                            "ref": "object:sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()})
            elif kind == "property_test":
                cert = json.loads((ROOT / "certificates" / "rewrites" / f"{ref}.json").read_text())
                out.append({"kind": kind, "ref": "object:sha256:" + cert["transcript_digest"][7:]})
            elif kind == "checked_certificate":
                p = ROOT / "certificates" / "rewrites" / f"{ref}.json"
                out.append({"kind": kind,
                            "ref": "object:sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()})
            else:
                out.append({"kind": kind, "ref": ref})
        return out

    def to_json(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "pattern": self.pattern,
            "replacement": self.replacement,
            "requires": self.requires,
            "preserves": list(self.preserves),
            "proof_evidence": self.resolved_evidence(),
            "verification_refs": list(self.verification_refs),
            "pathology_tests": list(self.pathology_tests),
            "derivation_ref": "object:sha256:" + hashlib.sha256(
                (ROOT / "rewrites" / f"{self.derivation_slug}.md").read_bytes()).hexdigest(),
            "assurance": self.assurance,
            "experimental": self.experimental,
        }


def _build_registry() -> dict[str, RewriteRule]:
    return {
        "sol:rewrite/push_exact_selection_through_join/v1": RewriteRule(
            rule_id="sol:rewrite/push_exact_selection_through_join/v1",
            pattern="join(filter(F_in, P), R) with P exact and left-scoped",
            replacement="filter(join(F_in, R), P)",
            requires={
                "predicate_determinism": "exact",
                "predicate_scope": ["left_input"],
                "collection_kinds": ["set", "bag"],
                "evaluator_free": True,
                "same_temporal_context": True,
                "same_visibility_policy": True,
                "same_authorization_policy": True,
                "same_leakage_policy": True,
                "spans_policy_boundary": False,
            },
            preserves=("value", "multiplicity", "provenance", "order",
                       "answer_bounds", "assurance", "logical_disclosure"),
            proof_evidence=(
                ("formal_derivation", "push_exact_selection_through_join_v1"),
                ("property_test", "selection-pushdown"),
                ("adversarial_corpus", "QPATH-022"),
                ("checked_certificate", "selection-pushdown"),
            ),
            verification_refs=("record:verification_044",),
            pathology_tests=("QPATH-022",),
            derivation_slug="push_exact_selection_through_join_v1",
            assurance="proven",
        ),
        "sol:rewrite/prune_exact_projection/v1": RewriteRule(
            rule_id="sol:rewrite/prune_exact_projection/v1",
            pattern="project(P) whose output columns are unused downstream",
            replacement="project(P') with P' pruned to the used columns",
            requires={
                "columns_unused_downstream": True,
                "evaluator_free": True,
                "same_temporal_context": True,
                "same_visibility_policy": True,
                "same_authorization_policy": True,
                "same_leakage_policy": True,
                "spans_policy_boundary": False,
            },
            preserves=("value", "multiplicity", "provenance", "order",
                       "answer_bounds", "assurance", "diagnostics",
                       "logical_disclosure"),
            proof_evidence=(
                ("formal_derivation", "prune_exact_projection_v1"),
                ("property_test", "projection-pruning"),
                ("adversarial_corpus", "QPATH-044"),
                ("checked_certificate", "projection-pruning"),
            ),
            verification_refs=("record:verification_045",),
            pathology_tests=("QPATH-044",),
            derivation_slug="prune_exact_projection_v1",
            assurance="proven",
        ),
        "sol:rewrite/associate_exact_join/v1": RewriteRule(
            rule_id="sol:rewrite/associate_exact_join/v1",
            pattern="(A join B) join C with inner joins and partitionable on-conditions",
            replacement="A join (B join C)",
            requires={
                "join_type": "inner",
                "on_partitionable": True,
                "field_names_unique": True,
                "evaluator_free": True,
                "same_temporal_context": True,
                "same_visibility_policy": True,
                "same_authorization_policy": True,
                "same_leakage_policy": True,
                "spans_policy_boundary": False,
            },
            preserves=("value", "multiplicity", "provenance", "answer_bounds",
                       "assurance", "logical_disclosure"),
            proof_evidence=(
                ("formal_derivation", "associate_exact_join_v1"),
                ("property_test", "join-associativity"),
                ("adversarial_corpus", "QPATH-045"),
                ("checked_certificate", "join-associativity"),
            ),
            verification_refs=("record:verification_046",),
            pathology_tests=("QPATH-045",),
            derivation_slug="associate_exact_join_v1",
            assurance="proven",
        ),
        "sol:rewrite/normalize_union/v1": RewriteRule(
            rule_id="sol:rewrite/normalize_union/v1",
            pattern="nested same-kind unions and duplicate union_distinct inputs",
            replacement="flattened union; duplicate distinct inputs collapsed",
            requires={
                "schema_compatible": True,
                "evaluator_free": True,
                "same_temporal_context": True,
                "same_visibility_policy": True,
                "same_authorization_policy": True,
                "same_leakage_policy": True,
                "spans_policy_boundary": False,
            },
            preserves=("value", "multiplicity", "provenance", "order",
                       "answer_bounds", "assurance", "logical_disclosure"),
            proof_evidence=(
                ("formal_derivation", "normalize_union_v1"),
                ("property_test", "union-normalization"),
                ("adversarial_corpus", "QPATH-046"),
                ("checked_certificate", "union-normalization"),
            ),
            verification_refs=("record:verification_047",),
            pathology_tests=("QPATH-046",),
            derivation_slug="normalize_union_v1",
            assurance="proven",
        ),
        "sol:rewrite/substitute_exact_machine_summary/v1": RewriteRule(
            rule_id="sol:rewrite/substitute_exact_machine_summary/v1",
            pattern="query proven coverable by machine-summary levels 0-2 with a matching source commit",
            replacement="query answered from the committed machine summary",
            requires={
                "covering_proof": True,
                "source_commit_match": True,
                "summary_levels": [0, 1, 2],
                "evaluator_free": True,
                "spans_policy_boundary": False,
            },
            preserves=("value", "multiplicity", "provenance", "answer_bounds",
                       "assurance", "logical_disclosure", "evaluation_identity"),
            proof_evidence=(
                ("formal_derivation", "substitute_exact_machine_summary_v1"),
                ("property_test", "machine-summary-substitution"),
                ("adversarial_corpus", "QPATH-034"),
                ("checked_certificate", "machine-summary-substitution"),
            ),
            verification_refs=("record:verification_048",),
            pathology_tests=("QPATH-034",),
            derivation_slug="substitute_exact_machine_summary_v1",
            assurance="proven",
        ),
        POLICY_RULE: RewriteRule(
            rule_id=POLICY_RULE,
            pattern="filter(F) above a policy boundary PB, with an accepted disclosure proof",
            replacement="filter(F) pushed below PB (applied on the protected side)",
            requires={
                "disclosure_proof": True,
                "boundary_kind": ["authorization", "visibility", "leakage"],
                "predicate_determinism": "exact",
                "spans_policy_boundary": True,
            },
            preserves=("value", "multiplicity", "provenance", "order",
                       "answer_bounds", "assurance", "logical_disclosure"),
            proof_evidence=(
                ("formal_derivation", "push_filter_across_policy_with_disclosure_proof_v1"),
                ("checked_certificate", "disclosure-proof"),
                ("adversarial_corpus", "QPATH-026"),
            ),
            verification_refs=("record:verification_049",),
            pathology_tests=("QPATH-026", "QPATH-039"),
            derivation_slug="push_filter_across_policy_with_disclosure_proof_v1",
            assurance="proven",
        ),
        EXPERIMENTAL_RULE: RewriteRule(
            rule_id=EXPERIMENTAL_RULE,
            pattern="adjacent exact aggregates over the same group keys",
            replacement="folded aggregate (unverified)",
            requires={
                "aggregate_determinism": "exact",
                "evaluator_free": True,
            },
            preserves=("value", "multiplicity"),
            proof_evidence=(
                ("contract_assertion", "contract:experimental_aggregate_fold/v1"),
            ),
            verification_refs=(),
            pathology_tests=("QPATH-036",),
            derivation_slug="experimental_aggregate_fold_v1",
            assurance="contract_asserted",
            experimental=True,
        ),
    }


RULES: dict[str, RewriteRule] = _build_registry()


# ---------------------------------------------------------------------------
# Requests and outcomes

@dataclass
class RewriteRequest:
    rule_id: str
    location: str
    disclosure_proof: str | None = None
    covering_proof: str | None = None
    source_commit: str | None = None
    justification: str | None = None
    claimed_assurance: str | None = None
    claimed_dimensions: tuple[str, ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()  # explicit evidence override

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> RewriteRequest:
        return cls(
            rule_id=obj["rule_id"],
            location=obj["location"],
            disclosure_proof=obj.get("disclosure_proof"),
            covering_proof=obj.get("covering_proof"),
            source_commit=obj.get("source_commit"),
            justification=obj.get("justification"),
            claimed_assurance=obj.get("claimed_assurance"),
            claimed_dimensions=tuple(obj.get("claimed_dimensions", [])),
            evidence=tuple(obj.get("evidence", [])),
        )


@dataclass
class RewriteOutcome:
    applied: bool
    diagnostics: list[Diagnostic] = field(default_factory=list)
    rewritten_query: dict[str, Any] | None = None
    record: dict[str, Any] | None = None

    def add(self, rule: str, code: str, target: str, message: str) -> None:
        self.diagnostics.append(diag(rule, code, target, message))


# ---------------------------------------------------------------------------
# Plan helpers

def _nodes(query: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in query.get("nodes", [])}


def _node(query: dict[str, Any], nid: str | None) -> dict[str, Any] | None:
    return _nodes(query).get(nid)


def _child_ids(n: dict[str, Any]) -> list[str]:
    op = n.get("op")
    if op in {"filter", "project", "limit", "sort", "distinct", "aggregate",
              "rename", "annotate", "evaluate", "temporal_slice", "policy_boundary"}:
        return [n.get("input")]
    if op == "join":
        return [n.get("left"), n.get("right")]
    if op in {"union_all", "union_distinct", "intersect", "difference"}:
        return list(n.get("inputs", []))
    return []


def _span_nodes(query: dict[str, Any], root_nid: str) -> set[str]:
    """All nodes reachable from root_nid (its subtree, inclusive)."""
    nodes = _nodes(query)
    seen: set[str] = set()

    def visit(nid: str | None) -> None:
        if not nid or nid in seen or nid not in nodes:
            return
        seen.add(nid)
        for c in _child_ids(nodes[nid]):
            visit(c)

    visit(root_nid)
    return seen


def _exact_predicate(n: dict[str, Any]) -> bool:
    """A predicate is exact when it has deterministic terms and no
    heuristic selectivity range."""
    pred = n.get("predicate") or {}
    if not pred.get("terms"):
        return False
    if "min_selectivity" in pred or "max_selectivity" in pred:
        return False
    return True


def _boundary_kind(policy: str | None) -> str | None:
    if not isinstance(policy, str):
        return None
    for kind in ("authorization", "visibility", "leakage"):
        if policy.startswith(f"policy:{kind}"):
            return kind
    return None


def _rewire(query: dict[str, Any], old_id: str, new_id: str) -> dict[str, Any]:
    """Point every reference to old_id at new_id (inputs and root)."""
    out = json.loads(json.dumps(query))
    for n in out.get("nodes", []):
        for key in ("input", "left", "right"):
            if n.get(key) == old_id:
                n[key] = new_id
        if isinstance(n.get("inputs"), list):
            n["inputs"] = [new_id if i == old_id else i for i in n["inputs"]]
    if out.get("root") == old_id:
        out["root"] = new_id
    return out


def _node_field_refs(n: dict[str, Any]) -> set[str]:
    """Field names a node references from its input (best effort)."""
    op = n.get("op")
    out: set[str] = set()
    if op == "filter":
        out |= {t["field"] for t in (n.get("predicate") or {}).get("terms", [])}
    elif op == "sort":
        out |= set(n.get("by", []))
    elif op == "distinct":
        out |= set(n.get("keys") or [])
    elif op == "project":
        out |= {s.get("expr") for s in n.get("fields", []) if not s.get("literal")}
    elif op == "aggregate":
        out |= set(n.get("group_by", []))
        out |= {a.get("field") for a in n.get("aggregates", []) if a.get("field")}
    elif op == "join":
        out |= {c.get("left") for c in n.get("on", [])}
        out |= {c.get("right") for c in n.get("on", [])}
    elif op == "annotate":
        out |= {c.get("expr") for c in n.get("columns", []) if c.get("expr")}
    elif op == "temporal_slice":
        out.add(n.get("field"))
    return {f for f in out if f}


def _downstream_fields(query: dict[str, Any], from_nid: str) -> set[str]:
    """Column names of from_nid's output that nodes on the path from the
    root down to (excluding) from_nid's consumer reference."""
    nodes = _nodes(query)
    used: set[str] = set()

    def visit(nid: str | None) -> bool:
        nonlocal used
        if not nid or nid not in nodes:
            return False
        if nid == from_nid:
            return True
        n = nodes[nid]
        for c in _child_ids(n):
            if visit(c):
                used |= _node_field_refs(n)
                return True
        return False

    visit(query.get("root"))
    return used


def _query_fields(query: dict[str, Any]) -> set[str]:
    """All field names referenced by any node reachable from the root:
    the fields a covering machine summary must provide (QV8-04)."""
    nodes = _nodes(query)
    seen: set[str] = set()
    used: set[str] = set()

    def visit(nid: str | None) -> None:
        nonlocal used
        if not nid or nid in seen or nid not in nodes:
            return
        seen.add(nid)
        used |= _node_field_refs(nodes[nid])
        for c in _child_ids(nodes[nid]):
            visit(c)

    visit(query.get("root"))
    return used


def _output_fields(query: dict[str, Any], nid: str | None) -> set[str]:
    """Output column names of a node (best effort for pattern checks)."""
    n = _node(query, nid)
    if n is None:
        return set()
    op = n.get("op")
    if op == "read":
        src = query.get("sources", {}).get(n.get("source"), {})
        return {f["name"] for f in src.get("schema", [])}
    if op == "project":
        return {s.get("name") or s.get("expr") for s in n.get("fields", [])}
    if op == "join":
        return _output_fields(query, n.get("left")) | _output_fields(query, n.get("right"))
    if op in {"filter", "sort", "distinct", "limit", "rename",
              "temporal_slice", "policy_boundary"}:
        return _output_fields(query, n.get("input"))
    if op in {"union_all", "union_distinct"}:
        inputs = n.get("inputs") or []
        return _output_fields(query, inputs[0]) if inputs else set()
    return set()


# ---------------------------------------------------------------------------
# Transformations

def _push_selection(query: dict[str, Any], j: dict[str, Any]) -> dict[str, Any]:
    """join(filter(F_in, P), R)  ->  filter(join(F_in, R), P).

    The consumed filter node is dropped from the plan, and the new filter
    is appended after the rewire so its input reference to the join is
    not rewritten onto itself.
    """
    left = _node(query, j["left"])
    assert left is not None and left.get("op") == "filter"
    out = json.loads(json.dumps(query))
    for n in out["nodes"]:
        if n["id"] == j["id"]:
            n["left"] = left["input"]
    out["nodes"] = [n for n in out["nodes"] if n["id"] != left["id"]]
    new_id = j["id"] + "__pushed"
    out = _rewire(out, j["id"], new_id)
    out["nodes"].append({"id": new_id, "op": "filter", "input": j["id"],
                         "predicate": left["predicate"]})
    return out


def _prune_projection(query: dict[str, Any], p: dict[str, Any]) -> dict[str, Any] | None:
    used = _downstream_fields(query, p["id"])
    fields = [s for s in p.get("fields", [])
              if (s.get("name") or s.get("expr")) in used]
    if len(fields) == len(p.get("fields", [])):
        return None  # nothing to prune
    out = json.loads(json.dumps(query))
    for n in out["nodes"]:
        if n["id"] == p["id"]:
            n["fields"] = fields
    return out


def _associate_join(query: dict[str, Any], j: dict[str, Any]) -> dict[str, Any] | None:
    """(A join B) join C  ->  A join (B join C)."""
    left = _node(query, j["left"])
    assert left is not None and left.get("op") == "join"
    a, b = left["left"], left["right"]
    c = j["right"]
    a_fields = _output_fields(query, a)
    b_fields = _output_fields(query, b)
    # The inner join's conditions move to the outer join (they link A and
    # B); the outer join's conditions partition over B (inner) and A
    # (outer). on_a must be non-empty; on_b may be empty (cross with C).
    on_a = [dict(c) for c in left.get("on", [])]
    on_b = []
    for cond in j.get("on", []):
        if cond["left"] in a_fields:
            on_a.append(dict(cond))
        elif cond["left"] in b_fields:
            on_b.append(dict(cond))
        else:
            return None  # not partitionable
    if not on_a:
        return None
    inner_id = j["id"] + "__assoc"
    out = json.loads(json.dumps(query))
    out_nodes = {n["id"]: n for n in out["nodes"]}
    inner = {"id": inner_id, "op": "join", "left": b, "right": c,
             "join_type": "inner", "on": on_b}
    out["nodes"].append(inner)
    out_nodes[j["id"]]["left"] = a
    out_nodes[j["id"]]["right"] = inner_id
    out_nodes[j["id"]]["on"] = on_a
    return out


def _normalize_union(query: dict[str, Any], u: dict[str, Any]) -> dict[str, Any] | None:
    nodes = _nodes(query)
    inputs = list(u.get("inputs", []))
    changed = False
    flat: list[str] = []
    for i in inputs:
        n = nodes.get(i)
        if n is not None and n.get("op") == u["op"] and n.get("inputs"):
            flat.extend(n["inputs"])
            changed = True
        else:
            flat.append(i)
    if u["op"] == "union_distinct":
        seen: set[str] = set()
        dedup = []
        for i in flat:
            if i not in seen:
                seen.add(i)
                dedup.append(i)
        if len(dedup) != len(flat):
            changed = True
        flat = dedup
    if not changed:
        return None
    out = json.loads(json.dumps(query))
    for n in out["nodes"]:
        if n["id"] == u["id"]:
            n["inputs"] = flat
    return out


def _push_filter_across_policy(query: dict[str, Any], pb: dict[str, Any]) -> dict[str, Any] | None:
    """filter(F) above PB  ->  filter(F) below PB.

    Before: A -> PB -> F. After: A -> F -> PB. The filter id is
    preserved; PB's input moves below the filter.
    """
    consumer = None
    for n in query.get("nodes", []):
        if n.get("op") == "filter" and n.get("input") == pb["id"]:
            consumer = n
            break
    if consumer is None:
        return None
    out = json.loads(json.dumps(query))
    out_nodes = {n["id"]: n for n in out["nodes"]}
    a = pb["input"]
    out_nodes[consumer["id"]]["input"] = a
    # Output must flow through the boundary: every reference to the
    # filter (including the root) now points at the boundary node.
    out = _rewire(out, consumer["id"], pb["id"])
    for n in out["nodes"]:
        if n["id"] == pb["id"]:
            n["input"] = consumer["id"]
    return out


# ---------------------------------------------------------------------------
# Application kernel (25.4)

def apply_rewrite(query: dict[str, Any], request: RewriteRequest,
                  registry: dict[str, RewriteRule] | None = None) -> RewriteOutcome:
    """Check and apply one registered rewrite at one location (25.4)."""
    reg = registry or RULES
    outcome = RewriteOutcome(applied=False)
    nodes = _nodes(query)
    nid = request.location.removeprefix("node:")
    node = nodes.get(nid)

    # 25.4.1 registered and supported
    rule = reg.get(request.rule_id)
    if rule is None:
        outcome.add("QV7-01", "unregistered_rewrite", request.location,
                    f"Rewrite {request.rule_id!r} is not registered (25.4.1)")
        return outcome
    if node is None:
        outcome.add("QV7-02", "unmet_precondition", request.location,
                    f"Location {request.location!r} does not name a plan node")
        return outcome

    span = _span_nodes(query, nid)
    span_ops = {nodes[i].get("op") for i in span if i in nodes}
    has_evaluator = "evaluate" in span_ops
    boundaries = [nodes[i] for i in span if i in nodes and nodes[i].get("op") == "policy_boundary"]
    crosses_boundary = bool(boundaries)

    # 25.4.6-7 / QPATH-023: stale proof -> effective assurance unknown
    stale = set(query.get("stale_dependencies", [])) & set(rule.verification_refs)
    if stale:
        outcome.add("QV7-04", "stale_proof", request.location,
                    f"Rule evidence {sorted(stale)} is stale; effective assurance is unknown (25.4.6-7)")
        outcome.add("QV5-10", "stale_assurance", request.location,
                    "Effective assurance degraded to unknown through stale dependencies")

    # 25.4.4 / 25.5: evaluator barrier
    if has_evaluator and rule.rule_id != POLICY_RULE:
        outcome.add("QV7-02", "unmet_precondition", request.location,
                    "Precondition evaluator_free not met: the span contains a semantic-evaluator node")
        outcome.add("QV6-05", "evaluator_barrier", request.location,
                    "Rewrite crosses a semantic-evaluator barrier (25.5)")

    # 25.5: policy boundary default non-preserving. A crossing is only
    # licensed by the policy rule with a committed, verified disclosure
    # proof; every other crossing (any rule, missing or unverified proof)
    # is non-preserving by default.
    valid_policy_proof = (
        rule.rule_id == POLICY_RULE
        and bool(request.disclosure_proof)
        and _verify_disclosure_proof(request.disclosure_proof)
    )
    if crosses_boundary and not valid_policy_proof:
        outcome.add("QV7-07", "non_preserving_policy_boundary", request.location,
                    "Rewrite spans a policy boundary without an explicit disclosure proof; "
                    "non-preserving by default (25.5)")
        for pb in boundaries:
            if _boundary_kind(pb.get("policy")) == "authorization":
                outcome.add("QV9-09", "disclosure_change", request.location,
                            "Moving the filter across the authorization boundary changes "
                            "tuple-existence disclosure")
        if request.justification and "value" in request.justification.lower() \
                and "match" in request.justification.lower():
            outcome.add("QINV-15", "fixture_value_match", request.location,
                        "Justification by fixture value matching is not a disclosure proof (QPATH-039)")

    # 25.6: prose-only proof must not support proven
    if request.claimed_assurance == "proven":
        evidence = request.evidence or [(k, r) for k, r in rule.proof_evidence]
        strong = [e for e in evidence
                  if (e.get("kind") if isinstance(e, dict) else e[0]) in {"mechanized_proof", "checked_certificate"}
                  and str(e.get("ref") if isinstance(e, dict) else e[1]).startswith("object:sha256:")]
        if not strong:
            outcome.add("QV7-08", "prose_only_proof", request.location,
                        "Assurance `proven` is claimed from an unchecked prose reference; "
                        "prose alone MUST NOT support proven (25.6)")

    # 25.3: physical side-channel claims require a physical profile
    if "physical_side_channel_class" in (request.claimed_dimensions or ()) \
            or "physical_side_channel_class" in rule.preserves:
        if not PHYSICAL_PROFILE_PUBLISHED:
            outcome.add("QV7-09", "physical_claim_without_profile", request.location,
                        "Physical side-channel preservation claimed without a physical "
                        "conformance profile (25.3)")
            outcome.add("QV9-10", "logical_physical_conflation", request.location,
                        "A logical rewrite is used for a physical non-inference claim")

    # Rule-specific preconditions and transformations
    op = node.get("op")
    rewritten: dict[str, Any] | None = None
    if rule.rule_id == "sol:rewrite/push_exact_selection_through_join/v1":
        if op != "join":
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Pattern requires a join node")
        else:
            left = nodes.get(node.get("left"))
            if left is None or left.get("op") != "filter":
                outcome.add("QV7-02", "unmet_precondition", request.location,
                            "Precondition predicate_scope=[left_input] not met: the left input is not a filter")
            elif not _exact_predicate(left):
                outcome.add("QV7-02", "unmet_precondition", request.location,
                            "Precondition predicate_determinism=exact not met: the predicate is not exact")
            else:
                rewritten = _push_selection(query, node)
    elif rule.rule_id == "sol:rewrite/prune_exact_projection/v1":
        if op != "project":
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Pattern requires a project node")
        else:
            rewritten = _prune_projection(query, node)
            if rewritten is None:
                outcome.add("QV7-02", "unmet_precondition", request.location,
                            "Precondition columns_unused_downstream not met: every output column is used")
    elif rule.rule_id == "sol:rewrite/associate_exact_join/v1":
        if op != "join" or nodes.get(node.get("left"), {}).get("op") != "join":
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Pattern requires (join) join with the left input a join")
        elif node.get("join_type", "inner") != "inner" \
                or nodes[node["left"]].get("join_type", "inner") != "inner":
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Precondition join_type=inner not met")
        else:
            rewritten = _associate_join(query, node)
            if rewritten is None:
                outcome.add("QV7-02", "unmet_precondition", request.location,
                            "Precondition on_partitionable not met: on-conditions do not "
                            "partition over the inner join's sides")
    elif rule.rule_id == "sol:rewrite/normalize_union/v1":
        if op not in {"union_all", "union_distinct"}:
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Pattern requires a union node")
        else:
            rewritten = _normalize_union(query, node)
            if rewritten is None:
                outcome.add("QV7-02", "unmet_precondition", request.location,
                            "Nothing to normalize: no nested same-kind unions or duplicate "
                            "distinct inputs")
    elif rule.rule_id == "sol:rewrite/substitute_exact_machine_summary/v1":
        proof = _load_covering_proof(request.covering_proof or "")
        subst_diags = _substitute_precondition_diagnostics(query, request, proof)
        if subst_diags:
            for rid, cat, msg in subst_diags:
                outcome.add(rid, cat, request.location, msg)
        else:
            rewritten = _substitute_machine_summary(query, request)
    elif rule.rule_id == POLICY_RULE:
        if op != "policy_boundary":
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Pattern requires a policy_boundary node")
        elif _boundary_kind(node.get("policy")) is None:
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Precondition boundary_kind not met: the policy reference is not an "
                        "authorization/visibility/leakage boundary")
        elif not valid_policy_proof:
            # QV7-07 (and QV9-09/QINV-15 where applicable) already emitted
            # by the generic boundary check above.
            pass
        else:
            rewritten = _push_filter_across_policy(query, node)
            if rewritten is None:
                outcome.add("QV7-02", "unmet_precondition", request.location,
                            "Pattern requires a filter directly above the boundary")
    elif rule.rule_id == EXPERIMENTAL_RULE:
        if op != "aggregate":
            outcome.add("QV7-02", "unmet_precondition", request.location,
                        "Pattern requires an aggregate node")
        else:
            outcome.add("QV7-06", "experimental_rule_sole_basis", request.location,
                        "Experimental rule applied; the result may not be labeled exact or "
                        "certified solely on this rule (25.8)")

    if outcome.diagnostics:
        return outcome
    if rewritten is None:
        outcome.add("QV7-02", "unmet_precondition", request.location,
                    "Rewrite could not be applied at this location")
        return outcome

    # QV7-03: the rule's preservation contract must cover the
    # logical-equivalence dimensions the query requires (27, 29.4).
    required = tuple(query.get("required_dimensions") or ())
    missing = [d for d in required if d not in rule.preserves]
    if missing:
        outcome.add("QV7-03", "preservation_dimensions_uncovered", request.location,
                    f"Rule preservation contract does not cover the query-required "
                    f"logical-equivalence dimensions {missing} (27)")
        return outcome

    outcome.applied = True
    outcome.rewritten_query = rewritten
    outcome.record = {
        "rule_id": rule.rule_id,
        "location": request.location,
        "assurance": rule.assurance,
        "preserved_dimensions": list(rule.preserves),
        "proof_evidence_kinds": [k for k, _ in rule.proof_evidence],
        "disclosure_proof": request.disclosure_proof,
        "source_commit": request.source_commit,
    }
    if request.covering_proof:
        # The machine-summary substitution is recorded with the covering
        # proof and the source-commit pin (28.5; Phase 7 acceptance).
        outcome.record["covering_proof"] = request.covering_proof
    return outcome


def _verify_disclosure_proof(ref: str) -> bool:
    """The disclosure proof must be a committed object whose content
    digest matches the reference (transcript verification is performed
    by check_certificate)."""
    if not ref.startswith("object:sha256:"):
        return False
    p = ROOT / "certificates" / "rewrites" / "disclosure-proof.json"
    if not p.exists():
        return False
    return "object:sha256:" + hashlib.sha256(p.read_bytes()).hexdigest() == ref


# Committed covering-proof objects (25.4.2). Each is referenced by its
# content digest; the kernel resolves the reference against the files.
COVERING_PROOF_FILES = (
    "covering-proof.json",
    "covering-proof-gold.json",
    "covering-proof-heuristic.json",
)


def _load_covering_proof(ref: str) -> dict[str, Any] | None:
    """The covering proof must be a committed object whose content digest
    matches the reference (25.4.2; QV8-03/QV8-04)."""
    if not ref.startswith("object:sha256:"):
        return None
    for name in COVERING_PROOF_FILES:
        p = ROOT / "certificates" / "rewrites" / name
        if not p.exists():
            continue
        if "object:sha256:" + hashlib.sha256(p.read_bytes()).hexdigest() != ref:
            continue
        try:
            obj = json.loads(p.read_text())
        except Exception:
            return None
        return obj if obj.get("format") == "solqry-covering-proof/v1" else None
    return None


def _substitute_precondition_diagnostics(query: dict[str, Any], request: RewriteRequest,
                                         proof: dict[str, Any] | None) -> list[tuple[str, str, str]]:
    """Rule-specific precondition checks for machine-summary substitution
    (25.4.2; QV8-03 source-commit match, QV8-04 field completeness).

    ``proof`` is the loaded covering-proof object, or None when the request
    carries no covering proof or the reference does not resolve to a
    committed object. Returns (rule_id, category, message) tuples; a
    non-empty list means the rewrite is rejected.
    """
    if not request.covering_proof or not request.source_commit:
        return [("QV7-02", "unmet_precondition",
                 "Preconditions covering_proof and source_commit_match not met: "
                 "a committed covering proof and a source-commit pin are required")]
    if proof is None:
        return [("QV7-02", "unmet_precondition",
                 "Precondition covering_proof not met: the covering proof is not a "
                 "committed object with a matching content digest")]
    manifest = source_manifest(query)["manifest_digest"]
    if request.source_commit != proof.get("source_commit") \
            or proof.get("source_commit") != manifest:
        return [("QV8-03", "stale_materialized_view",
                 "Source commits do not match: the summary was computed against a "
                 "different source manifest than the query (QV8-03)")]
    missing = sorted(_query_fields(query) - set(proof.get("summary_fields", [])))
    if missing:
        return [("QV8-04", "lossy_summary",
                 f"Machine summary is not field-complete for the query; missing fields: "
                 f"{missing} (QV8-04)")]
    # QV8-02: view substitution preserves value, bounds, provenance,
    # policy, and freshness. A summary produced heuristically (26) is
    # not a covering exact view, however field-complete it is.
    if proof.get("guarantee", "exact") != "exact":
        return [("QV8-02", "heuristic_view_substitution",
                 "View substitution does not preserve value, bounds, provenance, policy, "
                 "and freshness: the summary was produced heuristically and is not a "
                 "covering exact view (28.5)")]
    # All preconditions hold: the substitution is eligible and executable
    # (28.3, 28.5, 37.7).
    return []


def _substitute_machine_summary(query: dict[str, Any],
                                request: RewriteRequest) -> dict[str, Any]:
    """The rewritten query: every source read in the span is answered from
    the committed machine summary (28.3). The summary remains derived; the
    annotation records the covering proof and the source-commit pin."""
    q = json.loads(json.dumps(query))
    nodes = {n["id"]: n for n in q.get("nodes", [])}
    span = _span_nodes(q, request.location.removeprefix("node:"))
    sources: set[str] = set()
    for nid in span:
        n = nodes.get(nid)
        if n is not None and n.get("op") == "read" and n.get("source"):
            sources.add(n["source"])
    for name in sorted(sources):
        q["sources"][name]["machine_summary"] = {
            "covering_proof": request.covering_proof,
            "source_commit": request.source_commit,
        }
    return q


def registry_report() -> dict[str, Any]:
    """Condition-5 evidence: the registered rule kernel with proof metadata."""
    return {
        "format": "solqry-rewrite-registry/v1",
        "mandatory_rules": list(MANDATORY_RULES),
        "registered": sorted(r.rule_id for r in RULES.values() if not r.experimental),
        "experimental": sorted(r.rule_id for r in RULES.values() if r.experimental),
        "rules": {rid: rule.to_json() for rid, rule in sorted(RULES.items())},
    }
