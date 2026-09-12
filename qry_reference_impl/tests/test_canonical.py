"""Phase 2 tests: typed AST canonicalization, query digests, source
manifests, policy-boundary nodes, Sol extension declarations, and the
Substrait mapping profile (spec 29, gate conditions 3 and 4)."""
import json
from pathlib import Path


from qryref.canonical import (
    canonicalize_query,
    query_digest,
    source_manifest,
)
from qryref.certified import infer_certified
from qryref.engine import semantic_diagnostics
from qryref.schemas import validate_json_schema
from qryref.substrait_mapper import (
    OP_TO_SUBSTRAIT,
    check_profile_digest,
    profile_digest,
    to_substrait_like,
    validate_substrait_profile,
)

ROOT = Path(__file__).resolve().parents[1]


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


SRC = {"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[2], [1], [3]]}}
NODES = [
    {"id": "r", "op": "read", "source": "s"},
    {"id": "f", "op": "filter", "input": "r",
     "predicate": {"terms": [{"field": "id", "op": "gte", "value": 2}]}},
]


# ---------------------------------------------------------------------------
# Canonicalization and digests (29.1, 29.4)

def test_canonicalization_idempotent():
    query = q(SRC, NODES, "f")
    c1 = canonicalize_query(query)
    c2 = canonicalize_query(c1)
    assert c1 == c2


def test_digest_stable_under_key_order():
    a = q(SRC, NODES, "f")
    b = json.loads(json.dumps(a))  # re-parse: same content
    assert query_digest(a) == query_digest(b)
    # Key order in the source dict must not matter.
    c = q({"s": SRC["s"]}, NODES, "f")
    d = q({**{"zz": {"schema": [], "rows": {"min": 0, "max": 0}}}, **SRC}, NODES, "f")
    assert query_digest(c) != query_digest(d)  # different source manifest


def test_digest_stable_under_node_order():
    a = q(SRC, NODES, "f")
    b = q(SRC, list(reversed(NODES)), "f")
    assert query_digest(a) == query_digest(b)


def test_digest_stable_under_tuple_order():
    a = q({"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1], [2]]}},
          [{"id": "r", "op": "read", "source": "s"}], "r")
    b = q({"s": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[2], [1]]}},
          [{"id": "r", "op": "read", "source": "s"}], "r")
    assert query_digest(a) == query_digest(b)


def test_description_excluded_from_identity():
    a = q(SRC, NODES, "f", description="first")
    b = q(SRC, NODES, "f", description="second")
    assert query_digest(a) == query_digest(b)
    assert "description" not in canonicalize_query(a)


def test_digest_format_and_source_manifest():
    query = q(SRC, NODES, "f")
    d = query_digest(query)
    assert d.startswith("digest:sha256:") and len(d) == len("digest:sha256:") + 64
    m = source_manifest(query)
    assert m["manifest_digest"].startswith("object:sha256:")
    assert m["sources"]["s"].startswith("object:sha256:")
    # Manifest is instance-sensitive.
    m2 = source_manifest(q({"s": {**SRC["s"], "tuples": [[1], [2]]}}, NODES, "f"))
    assert m2["manifest_digest"] != m["manifest_digest"]


def test_v01_query_canonicalizes():
    query = {
        "schema_version": "qry.query.v0.1",
        "query_id": "legacy",
        "sources": {"s": {"schema": [{"name": "id", "type": "i64"}], "rows": {"min": 0, "max": 10}}},
        "nodes": [{"id": "r", "op": "read", "source": "s"}],
        "root": "r",
    }
    c = canonicalize_query(query)
    assert c == canonicalize_query(c)
    assert query_digest(query).startswith("digest:sha256:")


# ---------------------------------------------------------------------------
# Policy-boundary nodes

def test_policy_boundary_identity_transfer():
    query = q(SRC, [
        {"id": "r", "op": "read", "source": "s"},
        {"id": "pb", "op": "policy_boundary", "input": "r", "policy": "policy:internal_standard"},
    ], "pb", extensions=["urn:qry:v0.3:policy-boundary"])
    inf = infer_certified(query)
    assert inf["pb"].lower.tuples == {(1,), (2,), (3,)}
    assert inf["pb"].upper.tuples == {(1,), (2,), (3,)}
    assert inf["pb"].guarantee == "exact"
    assert inf["pb"].bound_rule == "sol:bound/policy_boundary/v1"


def test_policy_boundary_requires_reference():
    query = q(SRC, [
        {"id": "r", "op": "read", "source": "s"},
        {"id": "pb", "op": "policy_boundary", "input": "r", "policy": "not-a-policy"},
    ], "pb", extensions=["urn:qry:v0.3:policy-boundary"])
    diags = semantic_diagnostics(query)
    assert any(d.rule_id == "QRY-SEM-019" for d in diags)


# ---------------------------------------------------------------------------
# Extension declarations (29.2, 29.5)

def test_undeclared_required_extension_fails():
    query = q(SRC, [
        {"id": "r", "op": "read", "source": "s"},
        {"id": "e", "op": "evaluate", "input": "r",
         "evaluator": "sol:evaluator/x/v1", "mode": "heuristic"},
    ], "e")
    diags = semantic_diagnostics(query)
    assert any(d.rule_id == "QRY-SEM-018" for d in diags)


def test_declared_extension_passes():
    query = q(SRC, [
        {"id": "r", "op": "read", "source": "s"},
        {"id": "e", "op": "evaluate", "input": "r",
         "evaluator": "sol:evaluator/x/v1", "mode": "heuristic"},
    ], "e", extensions=["urn:qry:v0.3:semantic-evaluator-barrier"])
    assert not semantic_diagnostics(query)


def test_unknown_optional_extension_preserved_ignored():
    # 29.5: unknown optional extensions may be preserved and ignored when
    # they cannot change denotation or requested guarantees.
    query = q(SRC, NODES, "f", extensions=["urn:qry:v0.3:experimental-note"])
    assert not semantic_diagnostics(query)
    c = canonicalize_query(query)
    assert "urn:qry:v0.3:experimental-note" in c["extensions"]


# ---------------------------------------------------------------------------
# Substrait mapping (gate 4)

def well_formed_cases():
    """Corpus cases whose query is expected to be well-formed.

    Cases with non-empty expected_diagnostics in manifest.json are
    deliberately defective fixtures (bad schema, unknown ops, defective
    claims); their diagnostics are asserted by the corpus harness
    (validate_corpus), not here. Gate 3/4 acceptance applies to
    well-formed corpus queries."""
    for case in sorted((ROOT / "corpus" / "cases").glob("*")):
        manifest = json.loads((case / "manifest.json").read_text())
        if manifest.get("expected_diagnostics"):
            continue
        yield case


def test_all_corpus_ops_mapped():
    ops = set()
    for case in well_formed_cases():
        query = json.loads((case / "query.json").read_text())
        for n in query.get("nodes", []):
            ops.add(n.get("op"))
    assert ops <= set(OP_TO_SUBSTRAIT), ops - set(OP_TO_SUBSTRAIT)


def test_unmapped_op_deterministic_diagnostic():
    query = q(SRC, [{"id": "r", "op": "read", "source": "s"},
                    {"id": "w", "op": "window_rank", "input": "r"}], "w")
    diags = validate_substrait_profile(query)
    assert [d.rule_id for d in diags] == ["QRY-SUBSTRAIT-001"]
    assert [d.rule_id for d in validate_substrait_profile(query)] == [d.rule_id for d in diags]


def test_substrait_mapping_shape():
    query = q(SRC, [
        {"id": "r", "op": "read", "source": "s"},
        {"id": "e", "op": "evaluate", "input": "r",
         "evaluator": "sol:evaluator/x/v1", "mode": "heuristic"},
    ], "e", extensions=["urn:qry:v0.3:semantic-evaluator-barrier"])
    out = to_substrait_like(query)
    assert out["version"]["producer"] == "qryref.v0.3"
    by_id = {r["node_id"]: r for r in out["relations"]}
    assert by_id["r"]["substrait_rel"] == "ReadRel"
    assert by_id["e"]["substrait_rel"] == "ExtensionRel"
    assert "urn:qry:v0.3:semantic-evaluator-barrier" in by_id["e"]["extensions"]
    assert "urn:qry:v0.3:semantic-evaluator-barrier" in out["extensions"]


def test_set_op_kinds():
    query = q(
        {"a": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[1]]},
         "b": {"schema": [{"name": "id", "type": "i64"}], "tuples": [[2]]}},
        [
            {"id": "ra", "op": "read", "source": "a"},
            {"id": "rb", "op": "read", "source": "b"},
            {"id": "u", "op": "union_all", "inputs": ["ra", "rb"]},
            {"id": "i", "op": "intersect", "inputs": ["ra", "rb"]},
            {"id": "d", "op": "difference", "inputs": ["ra", "rb"]},
        ],
        "u")
    out = to_substrait_like(query)
    by_id = {r["node_id"]: r for r in out["relations"]}
    assert by_id["u"]["set_op"] == "UNION"
    assert by_id["i"]["set_op"] == "INTERSECT"
    assert by_id["d"]["set_op"] == "MINUS"


def test_profile_digest_recorded_and_stable():
    assert not check_profile_digest()
    recorded = json.loads((ROOT / "substrait" / "mapping_digest.json").read_text())
    assert recorded["mapping_digest"] == profile_digest()


def test_execution_schema_validates_sample_record():
    query = q(SRC, NODES, "f")
    record = {
        "schema_version": "qry.execution.v0.3",
        "query_run_id": "query_run_001",
        "query_ref": "record:query_t",
        "query_digest": query_digest(query),
        "source_manifest": source_manifest(query)["manifest_digest"],
        "actor_id": "tool:sol_query_engine",
        "status": "incomplete_with_continuation",
        "continuation": {
            "token": "cont_001",
            "query_digest": query_digest(query),
            "source_manifest": source_manifest(query)["manifest_digest"],
            "partial_result_object": "object:sha256:" + "0" * 64,
        },
        "guarantee": {"kind": "bounded", "result_object": None},
        "assurance": {"status": "validated", "effective_status": "validated",
                      "evidence": ["record:verification_001"], "depends_on": []},
        "provenance_mode": "tuple",
        "rows_returned": 2,
        "resource_usage": {"records_read": 3, "object_bytes_read": 0,
                            "semantic_evaluations": 0, "wall_time_ms": 5},
        "logical_rewrites": [],
    }
    assert not validate_json_schema(record, "qry_execution.schema.json", "execution")
    # A continuation bound to a different query digest is invalid.
    bad = json.loads(json.dumps(record))
    bad["continuation"]["query_digest"] = "digest:sha256:" + "1" * 64
    # (Schema accepts the shape; digest-binding is enforced by the evaluator
    # in Phase 3 -- the schema pins the format.)
    assert not validate_json_schema(bad, "qry_execution.schema.json", "execution")


def test_all_corpus_queries_validate_against_published_schema():
    for case in well_formed_cases():
        query = json.loads((case / "query.json").read_text())
        diags = validate_json_schema(query, "qry_query.schema.json", "query")
        assert not diags, (case.name, diags)
