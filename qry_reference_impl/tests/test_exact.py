"""Phase 3 tests: exact scan evaluator over exploded RFC-SOL-0001
artifacts, budget/continuation with honest completion states (spec 30,
37.3; gate conditions 8 and 12)."""
import json
import shutil
from pathlib import Path


from qryref.exact import (
    artifact_tree_digest,
    execute_step,
    resume_step,
    scan_artifact_relation,
)
from qryref.record_runs import CENSUS_SCHEMA, census_query, demo_query
from qryref.schemas import validate_json_schema

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DEMO_ART = ROOT / "demos" / "budget_degradation" / "artifact.sol.d"
GOLD01 = REPO / "corpus" / "GOLD-01" / "artifact.sol.d"


def q(sources, nodes, root, **kw):
    query = {
        "schema_version": "qry.query.v0.3",
        "query_id": "t",
        "sources": sources,
        "nodes": nodes,
        "root": root,
    }
    query.update(kw)
    return query


# ---------------------------------------------------------------------------
# Artifact scanning (authoritative exploded representation)

def test_artifact_scan_gold01():
    rows, total = scan_artifact_relation(GOLD01, "records", CENSUS_SCHEMA)
    assert total == 5
    assert rows[0] == ("claim_007", "sol:record/claim", "active", "current", "verified")
    ids = [r[0] for r in rows]
    assert ids == sorted(ids)  # deterministic file order


def test_artifact_scan_offset_limit():
    rows, total = scan_artifact_relation(GOLD01, "records", CENSUS_SCHEMA,
                                         offset=2, limit=1)
    assert total == 5
    assert len(rows) == 1
    assert rows[0][0] == "evidence_011"


def test_artifact_tree_digest_deterministic_and_content_sensitive(tmp_path):
    d1 = artifact_tree_digest(GOLD01)
    d2 = artifact_tree_digest(GOLD01)
    assert d1 == d2 and d1.startswith("object:sha256:")
    copy = tmp_path / "art"
    shutil.copytree(GOLD01, copy)
    assert artifact_tree_digest(copy) == d1
    (copy / "records" / "claim_007.json").write_text(
        (copy / "records" / "claim_007.json").read_text() + "\n// touched\n")
    assert artifact_tree_digest(copy) != d1


def test_missing_relation_is_empty(tmp_path):
    art = tmp_path / "art"
    (art / "records").mkdir(parents=True)
    (art / "records" / "r1.json").write_text('{"record_id": "r1"}')
    rows, total = scan_artifact_relation(art, "commits", CENSUS_SCHEMA)
    # Missing relation directory: empty relation, not an error.
    assert total == 0 and rows == []


# ---------------------------------------------------------------------------
# Full scans (gate 8 shape)

def test_full_scan_complete_exact():
    digest = artifact_tree_digest(GOLD01)
    query = census_query(str(GOLD01.relative_to(REPO)), digest)
    result = execute_step(query, 5, base_dir=REPO)
    assert not result.diagnostics
    assert result.status == "complete"
    assert result.record["guarantee"]["kind"] == "exact"
    assert result.record["rows_returned"] == 5
    assert result.record["continuation"] is None
    assert [list(r) for r in result.rows] == json.loads(
        (ROOT / "evaluator_runs" / "corpus" / "GOLD-01" / "rows.json").read_text())


def test_digest_pin_mismatch_fails():
    query = census_query(str(GOLD01.relative_to(REPO)),
                         "object:sha256:" + "0" * 64)
    result = execute_step(query, 5, base_dir=REPO)
    assert result.status == "failed"
    assert [d.rule_id for d in result.diagnostics] == ["QRY-EXEC-001"]


# ---------------------------------------------------------------------------
# Budget, continuations, honest completion states (30.2, 30.3; gate 12)

def demo_steps(budget=2):
    query = demo_query()
    state, continuation = None, None
    steps = []
    for _ in range(10):
        if state is None:
            result = execute_step(query, budget, base_dir=REPO)
        else:
            result = resume_step(query, budget, continuation, state, base_dir=REPO)
        assert not result.diagnostics, result.diagnostics
        steps.append(result)
        if result.status == "complete":
            return query, steps
        state = result.state
        continuation = result.record["continuation"]
    raise AssertionError("demo did not complete")


def test_gate12_budget_degradation():
    query, steps = demo_steps()
    assert [s.status for s in steps] == [
        "incomplete_with_continuation",
        "incomplete_with_continuation",
        "complete",
    ]
    assert [s.record["guarantee"]["kind"] for s in steps] == [
        "bounded", "bounded", "exact",
    ]
    # 30.2: no exact label on a budget-truncated result.
    for s in steps[:2]:
        assert s.status != "complete"
        assert s.record["guarantee"]["kind"] != "exact"
    # Cumulative prefixes: each step sees all rows scanned so far.
    assert [list(r) for r in steps[0].rows] == [[2], [4]]
    assert [list(r) for r in steps[1].rows] == [[2], [4], [6]]
    assert [list(r) for r in steps[2].rows] == [[2], [4], [6]]
    # The committed demo report matches the recorded steps.
    report = json.loads(
        (ROOT / "evaluator_runs" / "demo_budget_degradation" / "report.json").read_text())
    assert report["final_rows"] == [[2], [4], [6]]
    assert report["guarantees"] == ["bounded", "bounded", "exact"]
    assert report["statuses"] == [
        "incomplete_with_continuation",
        "incomplete_with_continuation",
        "complete",
    ]


def test_continuation_binding_mismatch():
    query = demo_query()
    first = execute_step(query, 2, base_dir=REPO)
    cont = first.record["continuation"]
    state = first.state

    bad = dict(cont)
    bad["query_digest"] = "digest:sha256:" + "1" * 64
    result = resume_step(query, 2, bad, state, base_dir=REPO)
    assert result.status == "failed"
    assert [d.rule_id for d in result.diagnostics] == ["QRY-EXEC-002"]

    bad2 = dict(cont)
    bad2["token"] = "cont:sha256:" + "2" * 64
    result = resume_step(query, 2, bad2, state, base_dir=REPO)
    assert [d.rule_id for d in result.diagnostics] == ["QRY-EXEC-002"]

    # A continuation from a *different* query does not resume.
    other = demo_query()
    other["query_id"] = "t-other"
    result = resume_step(other, 2, cont, state, base_dir=REPO)
    assert [d.rule_id for d in result.diagnostics] == ["QRY-EXEC-002"]


def test_limit_settles_early():
    # limit 1 over a 3-row tuples source with budget 1: the limit is
    # satisfied after one row, so the result is complete/exact even
    # though the source scan is not exhausted (30.2).
    query = q(
        {"s": {"schema": [{"name": "v", "type": "i64"}], "tuples": [[3], [1], [2]]}},
        [{"id": "r", "op": "read", "source": "s"},
         {"id": "l", "op": "limit", "input": "r", "limit": 1}],
        "l")
    result = execute_step(query, 1)
    assert result.status == "complete"
    assert result.record["guarantee"]["kind"] == "exact"
    # Canonical (sorted) scan order: the first row is [1].
    assert [list(r) for r in result.rows] == [[1]]


def test_tuples_source_exact():
    query = q(
        {"s": {"schema": [{"name": "v", "type": "i64"}], "tuples": [[3], [1], [2]]}},
        [{"id": "r", "op": "read", "source": "s"},
         {"id": "f", "op": "filter", "input": "r",
          "predicate": {"terms": [{"field": "v", "op": "gte", "value": 2}]}},
         {"id": "o", "op": "sort", "input": "f", "by": ["v"]}],
        "o")
    result = execute_step(query, 3)
    assert result.status == "complete"
    assert [list(r) for r in result.rows] == [[2], [3]]


def test_set_ops_join_aggregate_exact():
    a = {"schema": [{"name": "v", "type": "i64"}], "tuples": [[1], [2], [3]]}
    b = {"schema": [{"name": "v", "type": "i64"}], "tuples": [[2], [3], [4]]}
    query = q(
        {"a": a, "b": b},
        [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "rb", "op": "read", "source": "b"},
            {"id": "u", "op": "union_all", "inputs": ["ra", "rb"]},
            {"id": "ud", "op": "union_distinct", "inputs": ["ra", "rb"]},
            {"id": "i", "op": "intersect", "inputs": ["ra", "rb"]},
            {"id": "d", "op": "difference", "inputs": ["ra", "rb"]},
            {"id": "j", "op": "join", "left": "ra", "right": "rb",
             "on": [{"left": "v", "right": "v"}]},
        ],
        "u")
    result = execute_step(query, 10)
    assert result.status == "complete"
    values = {n: None for n in ("u", "ud", "i", "d", "j")}
    # Re-evaluate per node to check each op's exact result.
    for root_id in values:
        q2 = dict(query)
        q2["root"] = root_id
        r2 = execute_step(q2, 10)
        values[root_id] = [list(r) for r in r2.rows]
    assert values["u"] == [[1], [2], [3], [2], [3], [4]]
    assert values["ud"] == [[1], [2], [3], [4]]
    assert values["i"] == [[2], [3]]
    assert values["d"] == [[1]]
    assert values["j"] == [[2, 2], [3, 3]]

    agg = q(
        {"s": {"schema": [{"name": "g", "type": "i64"}, {"name": "v", "type": "i64"}],
               "tuples": [[1, 10], [1, 20], [2, 5]]}},
        [{"id": "r", "op": "read", "source": "s"},
         {"id": "a", "op": "aggregate", "input": "r", "group_by": ["g"],
          "aggregates": [{"func": "sum", "field": "v", "name": "s"},
                         {"func": "count_set", "field": "v", "name": "c"}]}],
        "a")
    result = execute_step(agg, 10)
    assert result.status == "complete"
    assert [list(r) for r in result.rows] == [[1, 30, 2], [2, 5, 1]]


def test_evaluate_not_executable():
    query = q(
        {"s": {"schema": [{"name": "v", "type": "i64"}], "tuples": [[1]]}},
        [{"id": "r", "op": "read", "source": "s"},
         {"id": "e", "op": "evaluate", "input": "r",
          "evaluator": "sol:evaluator/x/v1", "mode": "heuristic"}],
        "e", extensions=["urn:qry:v0.3:semantic-evaluator-barrier"])
    result = execute_step(query, 1)
    assert result.status == "failed"
    assert [d.rule_id for d in result.diagnostics] == ["QRY-EXEC-003"]


# ---------------------------------------------------------------------------
# Recorded runs (committed evidence, reproducible)

def test_recorded_runs_validate_against_schema():
    runs = list((ROOT / "evaluator_runs").rglob("*.json"))
    run_files = [p for p in runs if p.name == "run.json" or p.name.startswith("step_")]
    assert len(run_files) == 68 + 3
    for p in run_files:
        rec = json.loads(p.read_text())
        assert not validate_json_schema(rec, "qry_execution.schema.json", "execution"), p


def test_recorded_runs_reproducible():
    import hashlib
    def tree_digest():
        h = hashlib.sha256()
        for p in sorted((ROOT / "evaluator_runs").rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(ROOT)).encode())
                h.update(p.read_bytes())
        return h.hexdigest()

    before = tree_digest()
    from qryref import record_runs
    assert record_runs.main() == 0
    assert tree_digest() == before


def test_report_digest_recomputable():
    report = json.loads((ROOT / "evaluator_runs" / "report.json").read_text())
    from qryref.canonical import canonical_json
    import hashlib
    content = {k: v for k, v in report.items() if k != "report_digest"}
    assert report["report_digest"] == "sha256:" + hashlib.sha256(
        canonical_json(content).encode("utf-8")).hexdigest()
    assert report["instances"]["corpus"]["cases"] == 31
    assert report["instances"]["sol_validator_corpus"]["cases"] == 37
    for instance in report["instances"].values():
        for run in instance["runs"]:
            assert run["status"] == "complete"
            assert run["guarantee"] == "exact"
