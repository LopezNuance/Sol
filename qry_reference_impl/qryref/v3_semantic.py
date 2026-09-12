"""v0.3 semantic validator rules (spec 34: QV0/QV1/QV2/QV3/QV4, QV5-06/07,
QINV-05/06).

Two layers:

* plan-shape and source-fact checks (``source_semantic_diagnostics``,
  ``plan_semantic_diagnostics``) wired into ``semantic_diagnostics``; they
  fire on declared source facts (branch/commit pins, unbounded/bag/
  approximate flags, truth-status fields) and plan shapes, so they are
  inert for queries that declare none of them;
* claim-based checks (``claim_semantic_diagnostics``) wired into
  ``validate_bound_record``; they fire only when a claimed bound record
  makes a commitment the plan cannot support.

QV5-07 (budget truncation labeled exact) is checked by the
execution-record case validation, where the truncation is an execution
fact, not a plan fact.
"""
from __future__ import annotations

from typing import Any

from .diagnostics import Diagnostic, diag
from .evaluators import claim_evaluator_diagnostics, evaluator_semantic_diagnostics

# ---------------------------------------------------------------------------
# Plan helpers


def _nodes(query: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in query.get("nodes", [])}


def _child_ids(n: dict[str, Any]) -> list[str]:
    op = n.get("op")
    if op in {"filter", "project", "limit", "sort", "distinct", "aggregate",
              "rename", "annotate", "evaluate", "temporal_slice", "policy_boundary"}:
        return [n.get("input")]
    if op == "join":
        return [n.get("left"), n.get("right")]
    if op in {"union_all", "union_distinct", "intersect", "difference"}:
        return list(n.get("inputs", []))
    if op == "least_fixpoint":
        return [n.get("seed"), n.get("edge")]
    return []


def _subtree_sources(query: dict[str, Any], nid: str | None) -> set[str]:
    """Source names read anywhere in the subtree rooted at nid."""
    nodes = _nodes(query)
    seen: set[str] = set()
    out: set[str] = set()

    def visit(nid: str | None) -> None:
        if not nid or nid in seen or nid not in nodes:
            return
        seen.add(nid)
        n = nodes[nid]
        if n.get("op") == "read":
            out.add(n.get("source"))
        for c in _child_ids(n):
            visit(c)

    visit(nid)
    return out


def _has_sort_ancestor(query: dict[str, Any], nid: str | None) -> bool:
    """A deterministic order is declared when a sort node is on the path
    from the root to (and excluding) nid's consumer."""
    nodes = _nodes(query)
    seen: set[str] = set()

    def visit(nid: str | None) -> bool:
        if not nid or nid in seen or nid not in nodes:
            return False
        seen.add(nid)
        n = nodes[nid]
        if n.get("op") == "sort" and n.get("by"):
            return True
        return any(visit(c) for c in _child_ids(n))

    return visit(query.get("root"))


def _field_types(query: dict[str, Any]) -> dict[str, str]:
    """Best-effort field-name -> type map over all declared sources."""
    out: dict[str, str] = {}
    for src in query.get("sources", {}).values():
        for f in src.get("schema", []):
            out.setdefault(f.get("name"), f.get("type"))
    return out


def _field_kinds(query: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for src in query.get("sources", {}).values():
        for f in src.get("schema", []):
            if f.get("kind"):
                out.setdefault(f.get("name"), f.get("kind"))
    return out


def _value_type(v: Any) -> str | None:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "i64"
    if isinstance(v, float):
        return "decimal"
    if isinstance(v, str):
        return "string"
    return None


def _source_flags(query: dict[str, Any], flag: str) -> set[str]:
    return {name for name, src in query.get("sources", {}).items() if src.get(flag)}


def _reads_of(query: dict[str, Any], flag: str) -> set[str]:
    """Node ids of reads over sources carrying ``flag``."""
    flagged = _source_flags(query, flag)
    return {n["id"] for n in query.get("nodes", [])
            if n.get("op") == "read" and n.get("source") in flagged}


def _unaudited_sources(query: dict[str, Any]) -> set[str]:
    """Sources with no exact instance and no certified sides: externally
    incomplete evidence (QV4-02)."""
    out = set()
    for name, src in query.get("sources", {}).items():
        if "tuples" not in src and "lower" not in src and "upper" not in src:
            out.add(name)
    return out


# ---------------------------------------------------------------------------
# Source-fact checks (QV1)

def source_semantic_diagnostics(query: dict[str, Any]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for name, src in query.get("sources", {}).items():
        if src.get("branch") and not src.get("commit"):
            diags.append(diag("QV1-02", "unresolved_branch", f"source:{name}",
                              f"Branch {src['branch']!r} is not resolved to a commit before evaluation"))
            diags.append(diag("QV1-03", "mutable_source_manifest", f"source:{name}",
                              "Source manifest is not immutable for one execution (unresolved branch)"))
        lc = (src.get("lower") or {}).get("commit")
        uc = (src.get("upper") or {}).get("commit")
        if lc and uc and lc != uc:
            diags.append(diag("QV1-05", "incompatible_source_manifests", f"source:{name}",
                              "Lower and upper relations use incompatible source manifests"))
        # 17.5: a latest-commit selection MUST declare a branch or lineage,
        # an ancestry relation, and a deterministic tie or conflict rule;
        # wall-clock timestamp alone across divergent branches is not a
        # valid commit resolution (QV1-02).
        latest = src.get("latest")
        if isinstance(latest, dict):
            missing = [f for f in ("ancestry", "tie_rule") if not latest.get(f)]
            if missing:
                diags.append(diag("QV1-02", "temporal_validation_failure", f"source:{name}",
                                  "Latest-commit selection is not a valid commit resolution: "
                                  + ", ".join(missing) + " missing; LATEST MUST NOT be "
                                  "interpreted solely by wall-clock timestamp in a branching "
                                  "history (17.5)"))
    return diags


# ---------------------------------------------------------------------------
# Plan-shape checks (QV0, QV2, QINV-05)

def plan_semantic_diagnostics(query: dict[str, Any]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    nodes = _nodes(query)
    types = _field_types(query)
    kinds = _field_kinds(query)

    for nid, n in nodes.items():
        # QV0-03: type-correct expressions.
        for t in (n.get("predicate") or {}).get("terms", []):
            field, op, value = t.get("field"), t.get("op"), t.get("value")
            if isinstance(value, str) and (value.startswith("object:") or value.startswith("digest:")):
                diags.append(diag("QV0-03", "type_error", f"node:{nid}",
                                  f"Expression compares field {field!r} with an immutable object "
                                  f"reference; named outputs are not object references"))
                continue
            ft = types.get(field)
            vt = _value_type(value)
            if ft and vt and ft != vt and not (ft == "decimal" and vt == "i64"):
                diags.append(diag("QV0-03", "type_error", f"node:{nid}",
                                  f"Expression is not type-correct: field {field!r} is {ft}, "
                                  f"literal is {vt}"))
            if kinds.get(field) == "truth_status" and op in {"eq", "ne"} and isinstance(value, bool):
                diags.append(diag("QINV-05", "truth_status_collapse", f"node:{nid}",
                                  f"Truth-status field {field!r} is compared as proposition truth; "
                                  f"unverified is not false"))

        # QV2-01/05: the difference's output domain (left side) must be
        # finitely bounded; generating output values from an unbounded
        # domain is unsafe (QPATH-011: every value that is not a claim).
        # An unbounded right side only tests membership and cannot make
        # the output unbounded, so it is not flagged here.
        if n.get("op") == "difference":
            left = (n.get("inputs") or [None])[0]
            if _subtree_sources(query, left) & _source_flags(query, "unbounded"):
                diags.append(diag("QV2-01", "unbound_output_variable", f"node:{nid}",
                                  "Output variables range over an unbounded domain and are not finitely bound"))
                diags.append(diag("QV2-05", "unsafe_unbounded_generation", f"node:{nid}",
                                  "Values are generated from an unbounded domain"))

    # Semantic-evaluator plan-shape rules (26.3-26.8, Q15): materialized
    # assessment records, evaluation-key completeness, duplicated
    # inline evaluator calls, and the equality prohibition.
    diags.extend(evaluator_semantic_diagnostics(query))
    return diags


# ---------------------------------------------------------------------------
# Claim-based checks (QV3, QV4, QV5-06, QINV-06)

def claim_semantic_diagnostics(query: dict[str, Any], claim, inference) -> list[Diagnostic]:
    """Checks that fire only when a claimed bound record commits to more
    than the plan supports. ``claim`` is a CertifiedBound; ``inference``
    is the node -> CertifiedBound map from infer_certified (may be None)."""
    diags: list[Diagnostic] = []
    nodes = _nodes(query)
    g = claim.guarantee
    committed = g in {"exact", "lower_bound", "upper_bound", "bounded"}

    # QV3-02: bag conversion must be explicit.
    if committed and _reads_of(query, "bag") and not any(
            n.get("op") == "distinct" for n in nodes.values()):
        diags.append(diag("QV3-02", "implicit_bag_conversion", "root_bound",
                          "Set-semantics claim over a bag source without an explicit Distinct"))

    # QV3-04 / QV3-05: limit over an unordered or inexact input.
    for nid, n in nodes.items():
        if n.get("op") != "limit":
            continue
        if committed and not _has_sort_ancestor(query, nid):
            diags.append(diag("QV3-04", "limit_without_deterministic_order", f"node:{nid}",
                              "Limit is committed without deterministic ordering"))
        if g == "exact" and inference is not None:
            inp = inference.get(n.get("input"))
            if inp is not None and inp.guarantee != "exact":
                diags.append(diag("QV3-05", "top_k_without_position_certainty", f"node:{nid}",
                                  "Inexact top-k/limit labeled exact without a registered "
                                  "position-certainty rule"))

    # QV4-02: exact negation crossing an open or incomplete boundary.
    if g == "exact":
        for nid, n in nodes.items():
            if n.get("op") != "difference":
                continue
            right = (n.get("inputs") or [None])[1]
            if _subtree_sources(query, right) & _unaudited_sources(query):
                diags.append(diag("QV4-02", "negation_across_incomplete_boundary", f"node:{nid}",
                                  "Classical exact negation crosses an open or incomplete boundary"))

    # QV4-04: bounded difference must use L1\U2 / U1\L2.
    if inference is not None and claim.lower is not None:
        root = query.get("root")
        root_node = nodes.get(root)
        if root_node is not None and root_node.get("op") == "difference":
            inputs = root_node.get("inputs") or []
            left = inference.get(inputs[0]) if len(inputs) > 0 else None
            right = inference.get(inputs[1]) if len(inputs) > 1 else None
            if (left is not None and right is not None
                    and left.lower is not None and left.upper is not None
                    and right.lower is not None and right.upper is not None):
                correct = left.lower.difference(right.upper)
                wrong = left.lower.difference(right.lower)
                if (claim.lower.tuples == wrong.tuples
                        and claim.lower.tuples != correct.tuples):
                    diags.append(diag("QV4-04", "wrong_side_difference", "root_bound",
                                       "Bounded difference lower uses lower-left (L1\\L2) instead of "
                                       "upper-right (L1\\U2)"))
                    diags.append(diag("QV5-02", "missing_transfer_rule", "root_bound",
                                      "Certified lower side has no normative or registered transfer rule"))

    # QV5-06: inexact aggregate labeled with a scalar bound.
    if committed and inference is not None:
        root = query.get("root")
        root_node = nodes.get(root)
        if root_node is not None and root_node.get("op") == "aggregate":
            inp = inference.get(root_node.get("input"))
            if inp is not None and inp.guarantee != "exact" and not claim.intervals:
                diags.append(diag("QV5-06", "scalar_bound_over_inexact_aggregate", "root_bound",
                                  "Inexact aggregate labeled with a scalar bound without a "
                                  "registered interval rule"))

    # QINV-06: approximate retrieval labeled exact.
    if g == "exact" and _reads_of(query, "approximate"):
        diags.append(diag("QINV-06", "false_exact_result", "root_bound",
                           "Approximate retrieval result is labeled exact"))

    # QV7-03 (claim context): every rewrite cited in the claim's
    # provenance must cover the query-required logical-equivalence
    # dimensions (25.4.3). A value-equivalent rewrite that drops the
    # required lower-membership lineage is a provenance violation.
    required = set(query.get("required_dimensions") or ())
    if required:
        from .rewrites import RULES
        ud = claim.provenance.upper_derivation
        for rid in sorted(set(ud.rewrites)) if ud is not None else ():
            rule = RULES.get(rid)
            if rule is None:
                continue
            missing = [d for d in sorted(required) if d not in rule.preserves]
            if missing:
                diags.append(diag("QV7-03", "preservation_dimensions_uncovered",
                                  "root_bound.provenance",
                                  f"Cited rewrite {rid} does not cover the query-required "
                                  f"logical-equivalence dimensions {missing} (25.4.3, 27)"))

    # Semantic-evaluator claim rules (QV5-08, QV5-09, QV6-07): the
    # claim commits to more than the plan's evaluators support.
    diags.extend(claim_evaluator_diagnostics(query, claim))
    return diags
