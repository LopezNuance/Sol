"""Phase 5 corpus unit tests: source-fact plan-shape rules, the
execution-record harness (spec 30), and the QV2 output-domain fix."""
from pathlib import Path
import json

from qryref.canonical import source_manifest
from qryref.engine import semantic_diagnostics
from qryref.validate import validate_case_dir

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "corpus" / "cases"
REPO = ROOT.parent

VALS = [{"name": "v", "type": "i64", "nullable": False}]


def _q(sources, nodes, root="r", **kw):
    q = {"schema_version": "qry.query.v0.3", "query_id": "t",
         "sources": sources, "nodes": nodes, "root": root}
    q.update(kw)
    return q


# ---------------------------------------------------------------------------
# QV2-01/05: the difference's output domain (left side) must be bounded

def test_qv2_unbounded_left_side_fires():
    q = _q({"u": {"schema": VALS, "unbounded": True},
            "c": {"schema": VALS, "tuples": [[1]]}},
           [{"id": "ru", "op": "read", "source": "u"},
            {"id": "rc", "op": "read", "source": "c"},
            {"id": "d", "op": "difference", "inputs": ["ru", "rc"]}],
           "d")
    got = {d.rule_id for d in semantic_diagnostics(q)}
    assert {"QV2-01", "QV2-05"} <= got


def test_qv2_unbounded_right_side_is_safe():
    # An unbounded right side only tests membership; the output stays
    # bounded by the left side, so no QV2 diagnostic.
    q = _q({"c": {"schema": VALS, "tuples": [[1]]},
            "u": {"schema": VALS, "unbounded": True}},
           [{"id": "rc", "op": "read", "source": "c"},
            {"id": "ru", "op": "read", "source": "u"},
            {"id": "d", "op": "difference", "inputs": ["rc", "ru"]}],
           "d")
    got = {d.rule_id for d in semantic_diagnostics(q)}
    assert "QV2-01" not in got and "QV2-05" not in got


# ---------------------------------------------------------------------------
# QV1: source-fact rules

def test_qv1_branch_without_commit():
    q = _q({"s": {"schema": VALS, "branch": "main"}},
           [{"id": "r", "op": "read", "source": "s"}])
    got = {d.rule_id for d in semantic_diagnostics(q)}
    assert {"QV1-02", "QV1-03"} <= got


def test_qv1_resolved_commit_is_clean():
    q = _q({"s": {"schema": VALS, "branch": "main",
                  "commit": "object:sha256:" + "00" * 32,
                  "tuples": [[1]]}},
           [{"id": "r", "op": "read", "source": "s"}])
    got = {d.rule_id for d in semantic_diagnostics(q)}
    assert not ({"QV1-02", "QV1-03"} & got)


def test_qv1_mismatched_side_commits():
    q = _q({"s": {"schema": VALS,
                  "lower": {"tuples": [[1]], "commit": "object:sha256:" + "aa" * 32},
                  "upper": {"tuples": [[1], [2]], "commit": "object:sha256:" + "bb" * 32}}},
           [{"id": "r", "op": "read", "source": "s"}])
    got = {d.rule_id for d in semantic_diagnostics(q)}
    assert "QV1-05" in got


# ---------------------------------------------------------------------------
# Canonicalization: source facts are part of the source identity

def test_source_manifest_sensitive_to_source_facts():
    base = {"schema": VALS, "tuples": [[1]]}
    m0 = source_manifest({"sources": {"s": base}})["manifest_digest"]
    for fact in ("bag", "approximate", "unbounded"):
        m = source_manifest({"sources": {"s": {**base, fact: True}}})["manifest_digest"]
        assert m != m0, fact
    m = source_manifest({"sources": {"s": {**base, "branch": "main"}}})["manifest_digest"]
    assert m != m0


def test_side_commit_sensitive():
    base = {"schema": VALS, "lower": {"tuples": [[1]]}, "upper": {"tuples": [[1]]}}
    m0 = source_manifest({"sources": {"s": base}})["manifest_digest"]
    s = {"schema": VALS,
         "lower": {"tuples": [[1]], "commit": "object:sha256:" + "aa" * 32},
         "upper": {"tuples": [[1]]}}
    assert source_manifest({"sources": {"s": s}})["manifest_digest"] != m0


# ---------------------------------------------------------------------------
# Execution-record harness (spec 30)

def _census_query(query_id="t"):
    from qryref.exact import artifact_tree_digest
    from qryref.record_runs import CENSUS_SCHEMA
    relpath = "sol_validator/corpus/GOLD-01/artifact.sol.d"
    art = REPO / relpath
    return _q({"records": {"schema": CENSUS_SCHEMA,
                           "artifact": {"path": relpath, "relation": "records",
                                        "digest": artifact_tree_digest(art)}}},
              [{"id": "r", "op": "read", "source": "records"},
               {"id": "s", "op": "sort", "input": "r", "by": ["record_id"]}],
              "s", query_id=query_id)


def _exec_case(tmp_path, query, record, manifest=None, resume=None):
    d = tmp_path / "case"
    d.mkdir()
    (d / "query.json").write_text(json.dumps(query))
    (d / "execution.json").write_text(json.dumps(record))
    m = {"case_id": "T", "expected_diagnostics": []}
    if manifest:
        m.update(manifest)
    (d / "manifest.json").write_text(json.dumps(m))
    if resume is not None:
        (d / "resume_source.json").write_text(json.dumps(resume))
    return d, m


def test_execution_record_binding_mismatch(tmp_path):
    from qryref.exact import execute_step
    q = _census_query("t-binding")
    res = execute_step(q, 5, base_dir=REPO, run_id="qrun:test:binding")
    assert res.status == "complete"
    bad = dict(res.record)
    bad["query_digest"] = "digest:sha256:" + "0" * 64
    d, m = _exec_case(tmp_path, q, bad)
    got = {x.rule_id for x in validate_case_dir(d, manifest=m)}
    assert "QRY-CORPUS-001" in got


def test_execution_qv5_07_truncation_labeled_exact(tmp_path):
    from qryref.exact import execute_step
    q = _census_query("t-qv507")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:test:qv507")
    assert res.status == "incomplete_with_continuation"
    rec = res.record
    rec["guarantee"]["kind"] = "exact"  # the defective claim
    d, m = _exec_case(tmp_path, q, rec,
                      manifest={"expected_status": "incomplete_with_continuation",
                                "expected_guarantee": "exact"})
    got = {x.rule_id for x in validate_case_dir(d, manifest=m)}
    assert "QV5-07" in got


def test_execution_honest_bounded_run_is_clean(tmp_path):
    from qryref.exact import execute_step
    q = _census_query("t-honest")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:test:honest")
    assert res.status == "incomplete_with_continuation"
    assert res.record["guarantee"]["kind"] == "bounded"
    d, m = _exec_case(tmp_path, q, res.record,
                      manifest={"expected_status": "incomplete_with_continuation",
                                "expected_guarantee": "bounded"})
    got = {x.rule_id for x in validate_case_dir(d, manifest=m)}
    assert not got


def test_execution_resume_drift_fails_binding(tmp_path):
    from qryref.exact import execute_step
    q = _census_query("t-drift")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:test:drift")
    assert res.status == "incomplete_with_continuation"
    # The later branch head: same artifact, branch reference, no commit.
    resume_src = {**q["sources"]["records"], "branch": "main"}
    d, m = _exec_case(tmp_path, q, res.record, resume=resume_src)
    got = {x.rule_id for x in validate_case_dir(d, manifest=m)}
    assert {"QV1-03", "QRY-EXEC-002"} <= got


def test_execution_resume_same_manifest_still_binds(tmp_path):
    from qryref.exact import execute_step
    q = _census_query("t-same")
    res = execute_step(q, 2, base_dir=REPO, run_id="qrun:test:same")
    # A resume source identical to the original still binds (no drift).
    d, m = _exec_case(tmp_path, q, res.record,
                      resume=q["sources"]["records"])
    got = {x.rule_id for x in validate_case_dir(d, manifest=m)}
    assert "QRY-EXEC-002" not in got


# ---------------------------------------------------------------------------
# Corpus-level regression: the 64 normative cases stay green

def test_normative_corpus_green():
    from qryref.validate_corpus import is_normative
    cases = sorted(p for p in CASES.iterdir() if p.is_dir())
    normative = [p for p in cases if is_normative(p.name)]
    assert len(normative) == 64
    for p in normative:
        manifest = json.loads((p / "manifest.json").read_text())
        expected = set(manifest.get("expected_diagnostics", []))
        got = {d.rule_id for d in validate_case_dir(p, check_match=not expected,
                                                    manifest=manifest)}
        if expected:
            assert expected.issubset(got), (p.name, expected, got)
        else:
            assert not got, (p.name, got)
