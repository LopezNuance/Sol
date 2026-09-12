"""Exact scan evaluator over exploded RFC-SOL-0001 artifacts.

Implements spec sections 30 and 37.3 (Phase 3):

* exact scans over the authoritative exploded representation
  (profile ``solqry-authoritative-exploded/v1``); no physical indexes --
  a correct scan of one artifact is sufficient to validate semantics;
* budget-limited execution with continuations (30.2, 30.3):
  - completion states: complete / incomplete_with_continuation /
    failed / cancelled;
  - an incomplete result never carries the ``exact`` guarantee
    (30.2: only settled work may be labeled exact);
  - a continuation token binds the query digest, the source manifest,
    the policies, the evaluator identities, and the partial-result
    state (30.3); resuming against a different instance or a later
    branch head fails with QRY-EXEC-002;
* execution records per 30.4, validated against
  ``qry_execution.schema.json``.

Settledness (when omitted work cannot affect the result, 30.2):

  read:            settled iff the source scan is exhausted
  unary ops:       settled iff the input is settled
  set ops / join:  settled iff all inputs are settled
  limit n:        settled iff the input has produced >= n rows

``evaluate`` and ``least_fixpoint`` are not executable by the first
exact evaluator (semantic evaluation is Phase 6; fixpoint semantics are
out of scope) and produce the deterministic diagnostic QRY-EXEC-003.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .canonical import canonical_json, query_digest, source_manifest
from .diagnostics import Diagnostic, diag
from .engine import semantic_diagnostics

# Authoritative exploded layout relations (profile
# solqry-authoritative-exploded/v1): artifact.sol.d/<relation>/*.json
ARTIFACT_RELATIONS = ("actors", "cells", "commits", "records", "runs")

# Ops the first exact evaluator cannot execute (deterministic diagnostic).
NOT_EXECUTABLE_OPS = {
    "evaluate": "semantic evaluation is provided by a registered semantic evaluator (spec 37.6)",
    "least_fixpoint": "fixpoint computation is out of scope for the first exact evaluator",
}

ACTOR_ID = "tool:sol_query_engine"


# ---------------------------------------------------------------------------
# Diagnostics (execution layer)

def _exec_diag(rule: str, code: str, target: str, message: str) -> Diagnostic:
    return diag(rule, code, target, message)


# ---------------------------------------------------------------------------
# Artifact scanning (authoritative exploded representation)

def _extract(obj: Any, dotted: str) -> Any:
    """Dot-path extraction into a JSON object; missing -> None."""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def artifact_tree_digest(artifact_dir: Path) -> str:
    """Content digest of an exploded artifact (30.4 source-commit pin).

    Deterministic: files sorted by relative path; each file's bytes
    hashed; the tree digest is the sha256 over the sorted
    (relpath, file_digest) pairs. Two artifacts with identical content
    trees have identical digests.
    """
    entries = []
    for p in sorted(artifact_dir.rglob("*")):
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            entries.append([str(p.relative_to(artifact_dir)), h])
    return "object:sha256:" + hashlib.sha256(canonical_json(entries).encode("utf-8")).hexdigest()


def scan_artifact_relation(artifact_dir: Path, relation: str,
                           schema: list[dict[str, Any]],
                           offset: int = 0, limit: int | None = None) -> tuple[list[tuple], int]:
    """Exact scan of one relation of an exploded artifact.

    Returns (rows, total): rows in deterministic file order starting at
    ``offset`` (at most ``limit`` rows when given), and the total number
    of rows in the relation. A missing relation directory is an empty
    relation; an unparseable record file raises ExactExecutionError
    (QRY-EXEC-007).
    """
    if relation not in ARTIFACT_RELATIONS:
        raise ExactExecutionError([_exec_diag("QRY-EXEC-004", "invalid_artifact_relation",
                                              f"artifact:{artifact_dir}",
                                              f"Relation {relation!r} is not in the authoritative layout")])
    rel_dir = artifact_dir / relation
    files = sorted(rel_dir.glob("*.json")) if rel_dir.is_dir() else []
    rows: list[tuple] = []
    for i, p in enumerate(files):
        if i < offset:
            continue
        if limit is not None and len(rows) >= limit:
            break
        try:
            obj = json.loads(p.read_text())
        except Exception as e:
            raise ExactExecutionError([_exec_diag("QRY-EXEC-007", "artifact_scan_error",
                                                  str(p), f"Unparseable record file: {e}")])
        rows.append(tuple(_extract(obj, f.get("path", f["name"])) for f in schema))
    return rows, len(files)


class ExactExecutionError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        super().__init__("; ".join(d.message for d in diagnostics))


# ---------------------------------------------------------------------------
# Execution state and continuation binding (30.3)

@dataclass(frozen=True)
class ExecutionState:
    """Partial-result state: per-source scan offsets (rows already
    scanned). The state is a content-addressed object (30.3: a
    continuation binds to the same partial-result state)."""

    offsets: dict[str, int] = field(default_factory=dict)

    def canonical(self) -> str:
        return canonical_json({"offsets": {k: self.offsets[k] for k in sorted(self.offsets)}})

    def digest(self) -> str:
        return "object:sha256:" + hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()


def _policies_of(query: dict[str, Any]) -> list[str]:
    return sorted({n["policy"] for n in query.get("nodes", [])
                   if n.get("op") == "policy_boundary" and isinstance(n.get("policy"), str)})


def _evaluators_of(query: dict[str, Any]) -> list[str]:
    return sorted({n["evaluator"] for n in query.get("nodes", [])
                   if n.get("op") == "evaluate" and isinstance(n.get("evaluator"), str)})


def continuation_binding(query: dict[str, Any], state: ExecutionState) -> dict[str, Any]:
    """30.3 binding: same query digest, same source manifest, same
    policies, same evaluator identities, same partial-result state.
    The token is a content digest of the binding, so a resumed run can
    verify it against the current query."""
    binding = {
        "query_digest": query_digest(query),
        "source_manifest": source_manifest(query)["manifest_digest"],
        "policies": _policies_of(query),
        "evaluator_identities": _evaluators_of(query),
        "partial_result_object": state.digest(),
    }
    token = "cont:sha256:" + hashlib.sha256(canonical_json(binding).encode("utf-8")).hexdigest()
    return {"token": token, **binding}


# ---------------------------------------------------------------------------
# Plan evaluation (exact, deterministic order)

def _tuple_key(v: Any) -> str:
    return json.dumps(v, sort_keys=True)


def _sort_key(values: list[Any]) -> str:
    return "|".join(_tuple_key(v) for v in values)


def _select_rows(rows: list[tuple], fields: list[str], terms: list[dict[str, Any]]) -> list[tuple]:
    idx = {t["field"]: fields.index(t["field"]) for t in terms}

    def ok(r: tuple) -> bool:
        for t in terms:
            v = r[idx[t["field"]]]
            if v is None:
                return False
            op = t["op"]
            val = t["value"]
            if op == "eq":
                r_ = v == val
            elif op == "ne":
                r_ = v != val
            elif op == "lt":
                r_ = v < val
            elif op == "lte":
                r_ = v <= val
            elif op == "gt":
                r_ = v > val
            elif op == "gte":
                r_ = v >= val
            else:
                raise ExactExecutionError([_exec_diag("QRY-EXEC-008", "unknown_predicate_op",
                                                      "predicate", f"Unknown predicate op {op!r}")])
            if not r_:
                return False
        return True

    return [r for r in rows if ok(r)]


def _aggregate_value(func: str, values: list[Any]) -> Any:
    vals = [v for v in values if v is not None]
    if func == "count_set":
        return len(set(_tuple_key(v) for v in vals))
    if not vals:
        return None
    if func == "sum":
        return sum(vals)
    if func == "min":
        return min(vals, key=_tuple_key)
    if func == "max":
        return max(vals, key=_tuple_key)
    if func == "avg":
        return sum(vals) / len(vals)
    raise ExactExecutionError([_exec_diag("QRY-EXEC-008", "unknown_aggregate",
                                          "aggregate", f"Unknown aggregate func {func!r}")])


def _eval_node(n: dict[str, Any], query: dict[str, Any],
               scans: dict[str, SourceScan],
               values: dict[str, tuple[list[str], list[tuple]]],
               settled: dict[str, bool]) -> None:
    op = n.get("op")
    if op in NOT_EXECUTABLE_OPS:
        raise ExactExecutionError([_exec_diag("QRY-EXEC-003", "op_not_executable",
                                              f"node:{n.get('id')}",
                                              f"Op {op!r} is not executable by the first exact evaluator: "
                                              + NOT_EXECUTABLE_OPS[op])])

    if op == "read":
        src_name = n["source"]
        src = query["sources"][src_name]
        if "artifact" in src:
            scan = scans[src_name]
            fields = [f["name"] for f in src["schema"]]
            values[n["id"]] = (fields, list(scan.rows))
            settled[n["id"]] = scan.exhausted
        elif "tuples" in src:
            fields = [f["name"] for f in src["schema"]]
            rows = [tuple(t) for t in scans[src_name].rows]
            values[n["id"]] = (fields, rows)
            settled[n["id"]] = scans[src_name].exhausted
        else:
            raise ExactExecutionError([_exec_diag("QRY-EXEC-004", "source_not_exact",
                                                  f"source:{src_name}",
                                                  "Source has no exact instance (tuples or artifact)")])
        return

    def inp(nid: str) -> tuple[list[str], list[tuple]]:
        return values[nid]

    if op == "filter":
        f, rows = inp(n["input"])
        values[n["id"]] = (f, _select_rows(rows, f, n.get("predicate", {}).get("terms", [])))
        settled[n["id"]] = settled[n["input"]]
    elif op == "temporal_slice":
        f, rows = inp(n["input"])
        terms = []
        if n.get("from") is not None:
            terms.append({"field": n["field"], "op": "gte", "value": n["from"]})
        if n.get("to") is not None:
            terms.append({"field": n["field"], "op": "lte", "value": n["to"]})
        values[n["id"]] = (f, _select_rows(rows, f, terms))
        settled[n["id"]] = settled[n["input"]]
    elif op == "project":
        f, rows = inp(n["input"])
        idx = [f.index(s["expr"]) if not s.get("literal") else None for s in n.get("fields", [])]
        out_f = [s.get("name") or s.get("expr") for s in n.get("fields", [])]
        out_rows = []
        for r in rows:
            out_rows.append(tuple(r[i] if i is not None else s.get("literal")
                                  for i, s in zip(idx, n.get("fields", []))))
        values[n["id"]] = (out_f, out_rows)
        settled[n["id"]] = settled[n["input"]]
    elif op == "rename":
        f, rows = inp(n["input"])
        mapping = n.get("mapping", {})
        values[n["id"]] = ([mapping.get(x, x) for x in f], rows)
        settled[n["id"]] = settled[n["input"]]
    elif op == "distinct":
        f, rows = inp(n["input"])
        keys = n.get("keys") or f
        ki = [f.index(k) for k in keys]
        seen: set[str] = set()
        out: list[tuple] = []
        for r in rows:
            k = _tuple_key([r[i] for i in ki])
            if k not in seen:
                seen.add(k)
                out.append(r)
        values[n["id"]] = (f, out)
        settled[n["id"]] = settled[n["input"]]
    elif op == "sort":
        f, rows = inp(n["input"])
        bi = [f.index(b) for b in n.get("by", [])]
        values[n["id"]] = (f, sorted(rows, key=lambda r: _sort_key([r[i] for i in bi])))
        settled[n["id"]] = settled[n["input"]]
    elif op == "limit":
        f, rows = inp(n["input"])
        lim = n["limit"]
        values[n["id"]] = (f, rows[:lim])
        # 30.2: a limit is settled once the input has produced >= limit
        # rows in input order; further input cannot change the result.
        settled[n["id"]] = settled[n["input"]] or len(rows) >= lim
    elif op == "aggregate":
        f, rows = inp(n["input"])
        group_by = list(n.get("group_by", []))
        gi = [f.index(g) for g in group_by]
        aggs = n.get("aggregates", [])
        ai = {a["name"]: f.index(a["field"]) for a in aggs if a.get("field")}
        groups: dict[str, list[tuple]] = {}
        order: list[str] = []
        for r in rows:
            k = _tuple_key([r[i] for i in gi])
            if k not in groups:
                groups[k] = []
                order.append(k)
            groups[k].append(r)
        out_f = group_by + [a["name"] for a in aggs]
        out_rows = []
        for k in order:
            grp = groups[k]
            key_vals = tuple(grp[0][i] for i in gi)
            agg_vals = tuple(_aggregate_value(a["func"], [r[ai[a["name"]]] for r in grp])
                             for a in aggs if a.get("field"))
            out_rows.append(key_vals + agg_vals)
        values[n["id"]] = (out_f, out_rows)
        settled[n["id"]] = settled[n["input"]]
    elif op in {"union_all", "union_distinct"}:
        inps = [inp(i) for i in n.get("inputs", [])]
        f = inps[0][0]
        rows: list[tuple] = []
        for _, r in inps:
            rows.extend(r)
        if op == "union_distinct":
            seen: set[str] = set()
            rows = [r for r in rows if _tuple_key(list(r)) not in seen and not seen.add(_tuple_key(list(r)))]
        values[n["id"]] = (f, rows)
        settled[n["id"]] = all(settled[i] for i in n.get("inputs", []))
    elif op in {"intersect", "difference"}:
        (lf, lrows), (rf, rrows) = (inp(n["inputs"][0]), inp(n["inputs"][1]))
        rset = set(map(tuple, rrows))
        if op == "intersect":
            out = [r for r in lrows if tuple(r) in rset]
        else:
            out = [r for r in lrows if tuple(r) not in rset]
        values[n["id"]] = (lf, out)
        settled[n["id"]] = settled[n["inputs"][0]] and settled[n["inputs"][1]]
    elif op == "join":
        lf, lrows = inp(n["left"])
        rf, rrows = inp(n["right"])
        on = n.get("on", [])
        li = [lf.index(c["left"]) for c in on]
        ri = [rf.index(c["right"]) for c in on]
        out: list[tuple] = []
        for lt in lrows:
            for rt in rrows:
                if all(lt[a] == rt[b] for a, b in zip(li, ri)):
                    out.append(tuple(lt) + tuple(rt))
        values[n["id"]] = (lf + rf, out)
        settled[n["id"]] = settled[n["left"]] and settled[n["right"]]
    elif op in {"annotate", "policy_boundary"}:
        f, rows = inp(n["input"])
        if op == "annotate":
            cols = n.get("columns", [])
            extra_idx = []
            for c in cols:
                if c.get("literal") is not None and "expr" not in c:
                    extra_idx.append(("lit", c["literal"]))
                else:
                    extra_idx.append(("field", f.index(c["expr"])))
            new_rows = [r + tuple(v if kind == "lit" else r[i] for kind, v in extra_idx) for r in rows]
            values[n["id"]] = (f + [c["name"] for c in cols], new_rows)
        else:
            values[n["id"]] = (f, rows)
        settled[n["id"]] = settled[n["input"]]
    else:
        raise ExactExecutionError([_exec_diag("QRY-EXEC-003", "op_not_executable",
                                              f"node:{n.get('id')}", f"Op {op!r} is not executable")])


def _topo_order(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic topological order from the root (dependencies first)."""
    nodes = {n["id"]: n for n in query.get("nodes", [])}
    order: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(nid: str | None) -> None:
        if not nid or nid in seen or nid not in nodes:
            return
        seen.add(nid)
        n = nodes[nid]
        for c in _node_inputs(n):
            visit(c)
        order.append(n)

    visit(query.get("root"))
    return order


def _node_inputs(n: dict[str, Any]) -> list[str]:
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


# ---------------------------------------------------------------------------
# Source materialization

@dataclass
class SourceScan:
    name: str
    rows: list[tuple]      # cumulative rows scanned so far (scan order)
    new_rows: int          # rows newly scanned in this step
    exhausted: bool
    total: int


def _materialize_sources(query: dict[str, Any], budget: int,
                         state: ExecutionState, base_dir: Path) -> dict[str, SourceScan]:
    """Advance each source's scan frontier (sorted name order) by at most
    the remaining budget, and materialize the cumulative prefix.

    The budget is a global row count of *new* rows across sources;
    sources are scanned in sorted name order, each in its deterministic
    scan order. Tuples sources scan in canonical (sorted) order so the
    scan order is a function of the query digest. The plan is evaluated
    over the cumulative prefix, so a resumed step sees all rows scanned
    so far (30.3: the continuation binds the same partial-result state).
    """
    scans: dict[str, SourceScan] = {}
    remaining = budget
    for name in sorted(query.get("sources", {})):
        src = query["sources"][name]
        offset = state.offsets.get(name, 0)
        if "artifact" in src:
            art = src["artifact"]
            art_dir = (base_dir / art["path"]).resolve()
            if not art_dir.is_dir():
                raise ExactExecutionError([_exec_diag("QRY-EXEC-007", "artifact_scan_error",
                                                      f"source:{name}",
                                                      f"Artifact directory not found: {art['path']}")])
            actual = artifact_tree_digest(art_dir)
            if actual != art["digest"]:
                raise ExactExecutionError([_exec_diag("QRY-EXEC-001", "artifact_digest_mismatch",
                                                      f"source:{name}",
                                                      f"Pinned digest {art['digest']} does not match "
                                                      f"artifact content {actual}; the instance changed "
                                                      "(30.3: no silent resume against a later branch head)")])
            all_rows, total = scan_artifact_relation(art_dir, art["relation"],
                                                     src["schema"])
        elif "tuples" in src:
            all_rows = sorted((tuple(t) for t in src["tuples"]), key=lambda t: _tuple_key(list(t)))
            total = len(all_rows)
        else:
            raise ExactExecutionError([_exec_diag("QRY-EXEC-004", "source_not_exact",
                                                  f"source:{name}",
                                                  "Source has no exact instance (tuples or artifact)")])
        take = max(0, min(remaining, total - offset))
        rows = all_rows[:offset + take]
        remaining -= take
        scans[name] = SourceScan(name=name, rows=rows, new_rows=take,
                                 exhausted=offset + take >= total, total=total)
    return scans


# ---------------------------------------------------------------------------
# Execution

@dataclass
class ExecutionResult:
    """One budgeted step of an exact evaluation (30.2, 30.4)."""

    record: dict[str, Any]
    rows: list[tuple]
    state: ExecutionState | None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.record["status"]


def rows_digest(rows: list[tuple]) -> str:
    """Content digest of a result row list (30.4 result bounds pin)."""
    return "object:sha256:" + hashlib.sha256(
        canonical_json([list(r) for r in rows]).encode("utf-8")).hexdigest()


def execute_step(query: dict[str, Any], budget: int,
                 state: ExecutionState | None = None,
                 base_dir: Path | None = None,
                 run_id: str | None = None) -> ExecutionResult:
    """Run one budgeted step of an exact evaluation.

    ``budget`` is the maximum number of source rows scanned in this
    step (global across sources). ``state`` is the continuation state
    from a previous step (None for a fresh run). ``base_dir`` resolves
    relative artifact paths (the repository root).
    """
    base_dir = base_dir or Path.cwd()
    qd = query_digest(query)
    sm = source_manifest(query)["manifest_digest"]

    def failed(diagnostics: list[Diagnostic]) -> ExecutionResult:
        record = {
            "schema_version": "qry.execution.v0.3",
            "query_run_id": run_id or "qrun:failed",
            "query_ref": f"record:query_{query.get('query_id')}",
            "query_digest": qd,
            "source_manifest": sm,
            "actor_id": ACTOR_ID,
            "status": "failed",
            "continuation": None,
            "guarantee": None,
            "assurance": {"status": "unknown", "effective_status": "unknown",
                          "evidence": [], "depends_on": []},
            "provenance_mode": "none",
            "rows_returned": 0,
            "resource_usage": {"records_read": 0, "object_bytes_read": 0,
                               "semantic_evaluations": 0, "wall_time_ms": 0},
            "logical_rewrites": [],
        }
        return ExecutionResult(record=record, rows=[], state=None, diagnostics=diagnostics)

    diags = semantic_diagnostics(query)
    if diags:
        return failed(diags)
    if not isinstance(budget, int) or budget < 1:
        return failed([_exec_diag("QRY-EXEC-005", "invalid_budget", "budget",
                                  "Budget must be a positive integer")])

    try:
        scans = _materialize_sources(query, budget, state or ExecutionState(), base_dir)
        values: dict[str, tuple[list[str], list[tuple]]] = {}
        settled: dict[str, bool] = {}
        for n in _topo_order(query):
            _eval_node(n, query, scans, values, settled)
        fields, rows = values[query["root"]]
    except ExactExecutionError as e:
        return failed(e.diagnostics)

    offsets = {name: (state.offsets.get(name, 0) if state else 0) + s.new_rows
               for name, s in sorted(scans.items())}
    new_state = ExecutionState(offsets=offsets)

    if settled[query["root"]]:
        status, guarantee, continuation = "complete", "exact", None
    else:
        status, guarantee = "incomplete_with_continuation", "bounded"
        continuation = {
            "token": continuation_binding(query, new_state)["token"],
            "query_digest": qd,
            "source_manifest": sm,
            "partial_result_object": new_state.digest(),
        }

    records_read = sum(s.total for s in scans.values())
    record = {
        "schema_version": "qry.execution.v0.3",
        "query_run_id": run_id or "qrun:" + hashlib.sha256(
            canonical_json({"query_digest": qd, "source_manifest": sm,
                            "state": new_state.digest()}).encode("utf-8")).hexdigest()[:16],
        "query_ref": f"record:query_{query.get('query_id')}",
        "query_digest": qd,
        "source_manifest": sm,
        "actor_id": ACTOR_ID,
        "status": status,
        "continuation": continuation,
        "guarantee": {"kind": guarantee, "result_object": rows_digest(rows)},
        "assurance": {
            "status": "validated",
            "effective_status": "validated",
            "evidence": [sm],
            "depends_on": sorted(query.get("sources", {})),
        },
        "provenance_mode": "tuple",
        "rows_returned": len(rows),
        "resource_usage": {"records_read": records_read, "object_bytes_read": 0,
                           "semantic_evaluations": 0, "wall_time_ms": 0},
        "logical_rewrites": [],
    }
    if status == "complete":
        return ExecutionResult(record=record, rows=rows, state=None)
    return ExecutionResult(record=record, rows=rows, state=new_state)


def resume_step(query: dict[str, Any], budget: int,
                continuation: dict[str, Any],
                state: ExecutionState,
                base_dir: Path | None = None,
                run_id: str | None = None) -> ExecutionResult:
    """Resume a budgeted evaluation from a continuation (30.3).

    Verifies the full binding: the token must match the recomputed
    binding for the current query, and the state's content digest must
    match the bound partial-result object. Any mismatch fails with
    QRY-EXEC-002 (no silent resume against a different query, instance,
    or partial state).
    """
    binding = continuation_binding(query, state)
    bound = {k: continuation.get(k) for k in
             ("token", "query_digest", "source_manifest", "partial_result_object")}
    if (bound["token"] != binding["token"]
            or bound["query_digest"] != binding["query_digest"]
            or bound["source_manifest"] != binding["source_manifest"]
            or bound["partial_result_object"] != binding["partial_result_object"]):
        return _resume_failed(
            query, "QRY-EXEC-002", "continuation",
            "Continuation binding mismatch (30.3): token, query digest, source "
            "manifest, or partial-result state does not match the current query")
    return execute_step(query, budget, state=state, base_dir=base_dir, run_id=run_id)


def _resume_failed(query: dict[str, Any], rule: str, target: str, message: str) -> ExecutionResult:
    qd = query_digest(query)
    sm = source_manifest(query)["manifest_digest"]
    record = {
        "schema_version": "qry.execution.v0.3",
        "query_run_id": "qrun:failed",
        "query_ref": f"record:query_{query.get('query_id')}",
        "query_digest": qd,
        "source_manifest": sm,
        "actor_id": ACTOR_ID,
        "status": "failed",
        "continuation": None,
        "guarantee": None,
        "assurance": {"status": "unknown", "effective_status": "unknown",
                      "evidence": [], "depends_on": []},
        "provenance_mode": "none",
        "rows_returned": 0,
        "resource_usage": {"records_read": 0, "object_bytes_read": 0,
                           "semantic_evaluations": 0, "wall_time_ms": 0},
        "logical_rewrites": [],
    }
    return ExecutionResult(record=record, rows=[], state=None,
                           diagnostics=[diag(rule, "continuation_binding_mismatch", target, message)])
