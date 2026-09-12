from __future__ import annotations
from typing import Any
from .engine import infer_all_bounds, semantic_diagnostics
from .diagnostics import Diagnostic, diag


def topological_order(query: dict[str, Any]) -> list[str]:
    nodes = {n["id"]: n for n in query.get("nodes", []) if "id" in n}
    out: list[str] = []
    seen: set[str] = set()
    def inputs(n: dict[str, Any]) -> list[str]:
        op = n.get("op")
        if op in {"filter", "project", "limit", "sort", "distinct", "aggregate", "rename"}:
            return [n.get("input")]
        if op == "join":
            return [n.get("left"), n.get("right")]
        if op in {"union_all", "union_distinct"}:
            return list(n.get("inputs", []))
        return []
    def visit(nid: str):
        if nid in seen or nid not in nodes: return
        for i in inputs(nodes[nid]):
            if i: visit(i)
        seen.add(nid); out.append(nid)
    visit(query.get("root"))
    return out


def generate_certificate(query: dict[str, Any], case_id: str | None = None) -> dict[str, Any]:
    bounds = infer_all_bounds(query)
    order = topological_order(query)
    steps = []
    for nid in order:
        node = next(n for n in query["nodes"] if n["id"] == nid)
        steps.append({
            "node_id": nid,
            "op": node["op"],
            "rule": f"qry.bound.{node['op']}.v0",
            "input_nodes": [i for i in _input_ids(node) if i],
            "bound": bounds[nid].to_json(),
        })
    return {
        "schema_version": "qry.certificate.v0.1",
        "query_id": query.get("query_id", case_id or "unknown"),
        "case_id": case_id,
        "root": query.get("root"),
        "steps": steps,
        "final_bound": bounds[query["root"]].to_json(),
    }


def _input_ids(node: dict[str, Any]) -> list[str]:
    op = node.get("op")
    if op in {"filter", "project", "limit", "sort", "distinct", "aggregate", "rename"}:
        return [node.get("input")]
    if op == "join": return [node.get("left"), node.get("right")]
    if op in {"union_all", "union_distinct"}: return list(node.get("inputs", []))
    return []


def compare_bound(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a == b


def validate_certificate(query: dict[str, Any], cert: dict[str, Any] | None) -> list[Diagnostic]:
    if cert is None:
        return [diag("QRY-CERT-000", "missing_certificate", "certificate", "Certificate missing")]
    sem = semantic_diagnostics(query)
    if sem:
        return []  # semantic validation owns these failures
    try:
        expected = infer_all_bounds(query)
    except Exception:
        return []
    diags: list[Diagnostic] = []
    order = topological_order(query)
    step_map = {s.get("node_id"): s for s in cert.get("steps", [])}
    for idx, nid in enumerate(order):
        if nid not in step_map:
            diags.append(diag("QRY-CERT-001", "certificate_missing_step", f"cert:{nid}", "Certificate missing proof step"))
            continue
        step = step_map[nid]
        if not compare_bound(step.get("bound"), expected[nid].to_json()):
            diags.append(diag("QRY-CERT-002", "certificate_step_bound_mismatch", f"cert:{nid}", "Certificate step bound does not match inferred bound"))
        # order check: inputs must have appeared in earlier certificate steps
        seen_steps = [s.get("node_id") for s in cert.get("steps", [])]
        try:
            pos = seen_steps.index(nid)
        except ValueError:
            continue
        for inp in _input_ids(next(n for n in query["nodes"] if n["id"] == nid)):
            if inp and (inp not in seen_steps[:pos]):
                diags.append(diag("QRY-CERT-004", "certificate_order_invalid", f"cert:{nid}", f"Input step {inp} does not precede node"))
    if cert.get("root") != query.get("root"):
        diags.append(diag("QRY-CERT-005", "certificate_root_mismatch", "cert.root", "Certificate root does not match query root"))
    if not compare_bound(cert.get("final_bound"), expected[query["root"]].to_json()):
        diags.append(diag("QRY-CERT-003", "certificate_final_mismatch", "cert.final_bound", "Certificate final bound mismatch"))
    return diags
