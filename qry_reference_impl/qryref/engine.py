from __future__ import annotations
from typing import Any
from .bounds import Bound, RowBound, Field, field_map, schema_compatible, apply_selectivity, max_add, max_mul, max_min
from .diagnostics import Diagnostic, diag
from .v3_semantic import plan_semantic_diagnostics, source_semantic_diagnostics
from .rules import OP_REQUIRED_EXTENSIONS

class QRYValidationError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        super().__init__("; ".join(d.message for d in diagnostics))


def node_map(query: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[Diagnostic]]:
    seen: dict[str, dict[str, Any]] = {}
    diags: list[Diagnostic] = []
    for n in query.get("nodes", []):
        nid = n.get("id")
        if nid in seen:
            diags.append(diag("QRY-SEM-001", "duplicate_node", f"node:{nid}", "Duplicate node id"))
        else:
            seen[nid] = n
    return seen, diags


def input_ids(node: dict[str, Any]) -> list[str]:
    op = node.get("op")
    if op in {"filter", "project", "limit", "sort", "distinct", "aggregate", "rename",
              "annotate", "evaluate", "temporal_slice", "policy_boundary"}:
        return [node.get("input")]
    if op == "join":
        return [node.get("left"), node.get("right")]
    if op in {"union_all", "union_distinct", "intersect", "difference"}:
        return list(node.get("inputs", []))
    if op == "least_fixpoint":
        return [node.get("seed"), node.get("edge")]
    return []


def semantic_diagnostics(query: dict[str, Any]) -> list[Diagnostic]:
    nodes, diags = node_map(query)
    root = query.get("root")
    if root not in nodes:
        diags.append(diag("QRY-SEM-002", "missing_root", "query.root", f"Root node {root!r} not found"))
    for nid, n in nodes.items():
        op = n.get("op")
        if op not in {"read", "filter", "project", "limit", "sort", "distinct", "aggregate", "join",
                      "union_all", "union_distinct", "rename", "intersect", "difference", "annotate",
                      "evaluate", "least_fixpoint", "temporal_slice", "policy_boundary"}:
            diags.append(diag("QRY-SEM-010", "unknown_operation", f"node:{nid}", f"Unknown op {op!r}"))
        for inp in input_ids(n):
            if inp not in nodes:
                diags.append(diag("QRY-SEM-003", "missing_input", f"node:{nid}", f"Input {inp!r} not found"))
        if op == "read":
            source = n.get("source")
            if source not in query.get("sources", {}):
                diags.append(diag("QRY-SEM-005", "unknown_source", f"node:{nid}", f"Source {source!r} not declared"))
        if op == "filter":
            pred = n.get("predicate", {})
            mn = pred.get("min_selectivity", 0.0)
            mx = pred.get("max_selectivity", 1.0)
            if not (0 <= mn <= mx <= 1):
                diags.append(diag("QRY-SEM-008", "invalid_selectivity", f"node:{nid}", "Selectivity must satisfy 0 <= min <= max <= 1"))
        if op == "limit":
            lim = n.get("limit")
            if not isinstance(lim, int) or lim < 0:
                diags.append(diag("QRY-SEM-009", "invalid_limit", f"node:{nid}", "Limit must be a non-negative integer"))
        if op in {"intersect", "difference"}:
            if len(n.get("inputs", [])) != 2:
                diags.append(diag("QRY-SEM-003", "missing_input", f"node:{nid}", f"{op} requires exactly two inputs"))
        if op == "evaluate":
            if n.get("mode", "heuristic") not in {"heuristic", "sound_positive"}:
                diags.append(diag("QRY-SEM-014", "invalid_evaluate_mode", f"node:{nid}", "Evaluate mode must be heuristic or sound_positive"))
            elif n.get("mode") == "sound_positive" and not n.get("positives"):
                diags.append(diag("QRY-SEM-015", "missing_positives", f"node:{nid}", "Sound-positive evaluate requires a certified positive set"))
        if op == "least_fixpoint":
            if not n.get("seed") or not n.get("edge") or not n.get("on"):
                diags.append(diag("QRY-SEM-016", "incomplete_fixpoint", f"node:{nid}", "Least fixpoint requires seed, edge, and on"))
        if op == "temporal_slice":
            if not n.get("field"):
                diags.append(diag("QRY-SEM-017", "missing_temporal_field", f"node:{nid}", "Temporal slice requires a time field"))
        if op == "policy_boundary":
            policy = n.get("policy", "")
            if not (isinstance(policy, str) and policy.startswith("policy:")):
                diags.append(diag("QRY-SEM-019", "invalid_policy_reference", f"node:{nid}",
                                  "Policy boundary requires a policy reference of the form policy:<name>"))
    # v0.3 source-fact and plan-shape semantic rules (QV0/QV1/QV2/QINV-05).
    diags.extend(source_semantic_diagnostics(query))
    diags.extend(plan_semantic_diagnostics(query))

    # Extension declarations (29.2, 29.5): ops with Sol-specific semantics
    # require their extension URN declared on the query.
    declared = set(query.get("extensions", []))
    for nid, n in nodes.items():
        required = OP_REQUIRED_EXTENSIONS.get(n.get("op"))
        if required and required not in declared:
            diags.append(diag("QRY-SEM-018", "undeclared_extension", f"node:{nid}",
                              f"Operation {n.get('op')!r} requires declared extension {required}"))
        if n.get("op") == "aggregate" and query.get("schema_version") == "qry.query.v0.3":
            # v0.3 aggregate functions are checked here; v0.1 queries use the
            # legacy "fn" spelling and are checked by the row-bound path.
            for agg in n.get("aggregates", []):
                func = agg.get("func")
                if func not in {"count_set", "sum", "min", "max", "avg"}:
                    diags.append(diag("QRY-SEM-013", "unknown_aggregate", f"node:{nid}", f"Unknown aggregate func {func!r}"))
                elif func in {"sum", "min", "max", "avg"} and not agg.get("field"):
                    diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Aggregate {func!r} requires a field"))
    # Evaluator-bearing predicate terms (26.8) and materialized
    # assessment sources (26.3) carry Sol-specific semantics and
    # require their extension URNs (29.2, 29.5).
    for nid, n in nodes.items():
        if n.get("op") != "filter":
            continue
        terms = (n.get("predicate") or {}).get("terms", [])
        if any(t.get("evaluator") for t in terms) \
                and "urn:qry:v0.3:semantic-evaluator-barrier" not in declared:
            diags.append(diag("QRY-SEM-018", "undeclared_extension", f"node:{nid}",
                              "A filter predicate using a semantic evaluator requires "
                              "declared extension urn:qry:v0.3:semantic-evaluator-barrier"))
    for name, src in query.get("sources", {}).items():
        if "assessment" in src and "urn:qry:v0.3:materialized-assessment" not in declared:
            diags.append(diag("QRY-SEM-018", "undeclared_extension", f"source:{name}",
                              "A source with a materialized assessment requires declared "
                              "extension urn:qry:v0.3:materialized-assessment"))
    # cycle detection
    temp: set[str] = set()
    perm: set[str] = set()
    def visit(nid: str) -> None:
        if nid in perm or nid not in nodes:
            return
        if nid in temp:
            diags.append(diag("QRY-SEM-004", "cycle", f"node:{nid}", "Cycle detected"))
            return
        temp.add(nid)
        for c in input_ids(nodes[nid]):
            if c:
                visit(c)
        temp.remove(nid)
        perm.add(nid)
    if root in nodes:
        visit(root)
    # schema-dependent field checks if possible (v0.1 row-bound path only;
    # v0.3 queries are checked by the certified inference)
    if not diags and query.get("schema_version", "qry.query.v0.1") != "qry.query.v0.3":
        try:
            infer_all_bounds(query)
        except QRYValidationError as e:
            diags.extend(e.diagnostics)
    return diags


def source_bound(source: dict[str, Any]) -> Bound:
    fields = tuple(Field(f["name"], f.get("type", "unknown"), f.get("nullable", True)) for f in source.get("schema", []))
    rows = source.get("rows", {})
    keys = tuple(tuple(k) for k in source.get("unique_keys", []))
    return Bound(RowBound(rows.get("min", 0), rows.get("max")), fields, (), keys)


def infer_all_bounds(query: dict[str, Any]) -> dict[str, Bound]:
    nodes, nd = node_map(query)
    if nd:
        raise QRYValidationError(nd)
    memo: dict[str, Bound] = {}
    visiting: set[str] = set()

    def infer(nid: str) -> Bound:
        if nid in memo:
            return memo[nid]
        if nid not in nodes:
            raise QRYValidationError([diag("QRY-SEM-003", "missing_input", f"node:{nid}", "Node not found")])
        if nid in visiting:
            raise QRYValidationError([diag("QRY-SEM-004", "cycle", f"node:{nid}", "Cycle detected")])
        visiting.add(nid)
        n = nodes[nid]
        op = n.get("op")
        b: Bound
        if op == "read":
            src = n.get("source")
            if src not in query.get("sources", {}):
                raise QRYValidationError([diag("QRY-SEM-005", "unknown_source", f"node:{nid}", f"Source {src!r} not declared")])
            b = source_bound(query["sources"][src])
        elif op == "filter":
            inp = infer(n["input"])
            pred = n.get("predicate", {})
            mn = pred.get("min_selectivity", 0.0)
            mx = pred.get("max_selectivity", 1.0)
            if not (0 <= mn <= mx <= 1):
                raise QRYValidationError([diag("QRY-SEM-008", "invalid_selectivity", f"node:{nid}", "Selectivity must satisfy 0 <= min <= max <= 1")])
            b = apply_selectivity(inp, mn, mx)
        elif op == "project":
            inp = infer(n["input"])
            fm = field_map(inp)
            out_fields: list[Field] = []
            for spec in n.get("fields", []):
                expr = spec.get("expr")
                name = spec.get("name") or expr
                if expr not in fm and not spec.get("literal"):
                    raise QRYValidationError([diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Field {expr!r} not found")])
                if spec.get("literal"):
                    out_fields.append(Field(name, spec.get("type", "unknown"), spec.get("nullable", False)))
                else:
                    base = fm[expr]
                    out_fields.append(Field(name, spec.get("type", base.type), spec.get("nullable", base.nullable)))
            if len({f.name for f in out_fields}) != len(out_fields):
                raise QRYValidationError([diag("QRY-SEM-011", "duplicate_field", f"node:{nid}", "Duplicate projected field name")])
            b = Bound(inp.rows, tuple(out_fields))
        elif op == "rename":
            inp = infer(n["input"])
            mapping = n.get("mapping", {})
            fields = tuple(Field(mapping.get(f.name, f.name), f.type, f.nullable) for f in inp.fields)
            b = Bound(inp.rows, fields, inp.order, inp.unique_keys)
        elif op == "limit":
            inp = infer(n["input"])
            lim = n.get("limit")
            if not isinstance(lim, int) or lim < 0:
                raise QRYValidationError([diag("QRY-SEM-009", "invalid_limit", f"node:{nid}", "Limit must be a non-negative integer")])
            maxv = lim if inp.rows.max is None else min(inp.rows.max, lim)
            b = Bound(RowBound(min(inp.rows.min, lim), maxv), inp.fields, inp.order, inp.unique_keys)
        elif op == "sort":
            inp = infer(n["input"])
            fm = field_map(inp)
            for field in n.get("by", []):
                if field not in fm:
                    raise QRYValidationError([diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Sort field {field!r} not found")])
            b = Bound(inp.rows, inp.fields, tuple(n.get("by", [])), inp.unique_keys)
        elif op == "distinct":
            inp = infer(n["input"])
            keys = tuple(n.get("keys") or [f.name for f in inp.fields])
            fm = field_map(inp)
            for k in keys:
                if k not in fm:
                    raise QRYValidationError([diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Distinct key {k!r} not found")])
            mn = 1 if inp.rows.min > 0 else 0
            b = Bound(RowBound(mn, inp.rows.max), inp.fields, (), (keys,))
        elif op == "aggregate":
            inp = infer(n["input"])
            fm = field_map(inp)
            group_by = list(n.get("group_by", []))
            for g in group_by:
                if g not in fm:
                    raise QRYValidationError([diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Group key {g!r} not found")])
            out_fields = [fm[g] for g in group_by]
            for agg in n.get("aggregates", []):
                out_fields.append(Field(agg.get("name"), agg.get("type", "numeric"), agg.get("nullable", True)))
            if group_by:
                row_min = 0 if inp.rows.min == 0 else 1
                row_max = inp.rows.max
            else:
                row_min = 1
                row_max = 1
            b = Bound(RowBound(row_min, row_max), tuple(out_fields), (), (tuple(group_by),) if group_by else tuple())
        elif op in {"union_all", "union_distinct"}:
            inputs = [infer(i) for i in n.get("inputs", [])]
            if not inputs:
                raise QRYValidationError([diag("QRY-SEM-003", "missing_input", f"node:{nid}", "Union requires inputs")])
            for other in inputs[1:]:
                if not schema_compatible(inputs[0], other):
                    raise QRYValidationError([diag("QRY-SEM-007", "union_schema_mismatch", f"node:{nid}", "Union inputs have incompatible schemas")])
            minv = sum(x.rows.min for x in inputs) if op == "union_all" else (1 if sum(x.rows.min for x in inputs) > 0 else 0)
            maxv = max_add([x.rows.max for x in inputs])
            b = Bound(RowBound(minv, maxv), inputs[0].fields)
        elif op == "join":
            left = infer(n["left"])
            right = infer(n["right"])
            join_type = n.get("join_type", "inner")
            rel = n.get("relationship", "many_to_many")
            if join_type not in {"inner", "left", "right", "full", "semi", "anti"}:
                raise QRYValidationError([diag("QRY-SEM-012", "invalid_join_type", f"node:{nid}", f"Invalid join type {join_type!r}")])
            lf = tuple(Field("left." + f.name, f.type, f.nullable) for f in left.fields)
            rf = tuple(Field("right." + f.name, f.type, f.nullable) for f in right.fields)
            if join_type in {"semi", "anti"}:
                fields = left.fields
            else:
                fields = lf + rf
            if join_type == "semi" or join_type == "anti":
                row_min, row_max = 0, left.rows.max
            elif join_type == "inner":
                row_min = 0
                if rel == "many_to_one":
                    row_max = left.rows.max
                elif rel == "one_to_many":
                    row_max = right.rows.max
                elif rel == "one_to_one":
                    row_max = max_min(left.rows.max, right.rows.max)
                else:
                    row_max = max_mul(left.rows.max, right.rows.max)
            elif join_type == "left":
                row_min = left.rows.min
                rmax = right.rows.max
                row_max = left.rows.max if rel in {"many_to_one", "one_to_one"} else max_mul(left.rows.max, max(1, rmax) if rmax is not None else None)
            elif join_type == "right":
                row_min = right.rows.min
                lmax = left.rows.max
                row_max = right.rows.max if rel in {"one_to_many", "one_to_one"} else max_mul(max(1, lmax) if lmax is not None else None, right.rows.max)
            else:  # full
                row_min = max(left.rows.min, right.rows.min)
                prod = max_mul(max(1, left.rows.max) if left.rows.max is not None else None, max(1, right.rows.max) if right.rows.max is not None else None)
                row_max = prod
            b = Bound(RowBound(row_min, row_max), fields)
        else:
            raise QRYValidationError([diag("QRY-SEM-010", "unknown_operation", f"node:{nid}", f"Unknown op {op!r}")])
        visiting.remove(nid)
        memo[nid] = b
        return b

    root = query.get("root")
    if root not in nodes:
        raise QRYValidationError([diag("QRY-SEM-002", "missing_root", "query.root", f"Root node {root!r} not found")])
    infer(root)
    return memo


def root_bound(query: dict[str, Any]) -> Bound:
    return infer_all_bounds(query)[query["root"]]
