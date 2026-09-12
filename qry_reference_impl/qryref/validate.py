from __future__ import annotations
import argparse
import json
from pathlib import Path
from .schemas import validate_json_schema
from .engine import semantic_diagnostics, root_bound, QRYValidationError
from .certificate import validate_certificate
from .diagnostics import Diagnostic, diag
from .certified import CertifiedBound, infer_certified, match_core, validate_bound_record


def load_json(path: Path):
    return json.loads(path.read_text())


def validate_v3_case(query: dict, path: Path, check_match: bool) -> list[Diagnostic]:
    """v0.3 certified path: infer certified bounds, validate the claimed
    bound record (13.19), and for clean cases require the claim to match
    the inference (or be a registered tighter bound, 13.18)."""
    diags: list[Diagnostic] = []
    bounds_path = path / "expected_bounds.json"
    if not bounds_path.exists():
        return [diag("QRY-SCHEMA-001", "missing_file", str(bounds_path), "expected_bounds.json missing for v0.3 case")]
    try:
        record = load_json(bounds_path)
    except Exception as e:
        return [diag("QRY-SCHEMA-001", "json_parse", str(bounds_path), str(e))]
    diags.extend(validate_json_schema(record, "qry_bounds_v3.schema.json", "expected_bounds"))
    if diags:
        return diags
    try:
        inference = infer_certified(query)
    except QRYValidationError as e:
        return e.diagnostics
    claim = CertifiedBound.from_json(record["root_bound"])
    diags.extend(validate_bound_record(query, claim, inference, record=record))
    if check_match:
        if not match_core(inference[query["root"]], claim):
            diags.append(diag("QRY-BOUND-001", "bound_mismatch", "expected_bounds.root_bound",
                              "Claimed bound does not match the inferred bound and is not a registered tighter bound"))
    return diags


def validate_rewrite_case(query: dict, path: Path) -> list[Diagnostic]:
    """Rewrite case (Phase 4, spec 25/36): query.json + rewrite.json +
    expected.json. Runs the rewrite kernel, compares the outcome against
    expected.json, and -- for applied rewrites over exact sources --
    verifies exact-result equivalence with the exact evaluator."""
    from collections import Counter
    from .canonical import canonicalize_query
    from .exact import execute_step
    from .rewrites import RewriteRequest, apply_rewrite

    diags: list[Diagnostic] = []
    rewrite = load_json(path / "rewrite.json")
    expected = load_json(path / "expected.json")
    outcome = apply_rewrite(query, RewriteRequest.from_dict(rewrite))
    diags.extend(outcome.diagnostics)
    if outcome.applied:
        if not expected.get("applied"):
            diags.append(diag("QRY-RW-100", "rewrite_expected_mismatch", "expected.json",
                              "Rewrite applied but the case expects rejection"))
        else:
            if canonicalize_query(outcome.rewritten_query) != canonicalize_query(expected["rewritten_query"]):
                diags.append(diag("QRY-RW-101", "rewrite_result_mismatch", "expected.json",
                                  "Rewritten query does not match the expected rewritten query"))
            if all("tuples" in s for s in query.get("sources", {}).values()):
                before = execute_step(query, 10**6)
                after = execute_step(outcome.rewritten_query, 10**6)
                if before.diagnostics or after.diagnostics:
                    diags.append(diag("QRY-RW-102", "rewrite_equivalence_failed", "expected.json",
                                      "Exact evaluation failed: "
                                      + "; ".join(d.rule_id for d in before.diagnostics + after.diagnostics)))
                elif Counter(map(tuple, before.rows)) != Counter(map(tuple, after.rows)):
                    diags.append(diag("QRY-RW-102", "rewrite_equivalence_failed", "expected.json",
                                      "Pre/post rewrite exact results differ (value or multiplicity)"))
        if expected.get("record") and outcome.record:
            for k, v in expected["record"].items():
                if outcome.record.get(k) != v:
                    diags.append(diag("QRY-RW-103", "rewrite_record_mismatch",
                                      f"expected.json:record.{k}",
                                      f"Application record field {k!r} does not match"))
    elif expected.get("applied"):
        diags.append(diag("QRY-RW-100", "rewrite_expected_mismatch", "expected.json",
                          "Rewrite rejected but the case expects application"))
    return diags


def validate_execution_case(query: dict, path: Path, manifest: dict | None) -> list[Diagnostic]:
    """Execution-record case (Phase 5, spec 30/36): query.json +
    execution.json. The record must validate against
    qry_execution.schema.json, be bound to the case query (30.3), and
    match the status/guarantee pinned by the manifest. A budget-truncated
    run (incomplete_with_continuation) may not carry the exact guarantee
    (QV5-07, 30.2). When the case carries resume_source.json (a later
    branch head), the continuation must fail its 30.3 binding against the
    resume query (QRY-EXEC-002)."""
    from .canonical import query_digest, source_manifest

    diags: list[Diagnostic] = []
    exec_path = path / "execution.json"
    try:
        record = load_json(exec_path)
    except Exception as e:
        return [diag("QRY-SCHEMA-002", "json_parse", str(exec_path), str(e))]
    diags.extend(validate_json_schema(record, "qry_execution.schema.json", "execution"))
    if diags:
        return diags
    qd = query_digest(query)
    sm = source_manifest(query)["manifest_digest"]
    if record.get("query_digest") != qd or record.get("source_manifest") != sm:
        diags.append(diag("QRY-CORPUS-001", "execution_record_mismatch", "execution.json",
                          "Execution record is not bound to the case query (30.3): "
                          "query digest or source manifest mismatch"))
    if manifest is not None:
        want_status = manifest.get("expected_status")
        want_guarantee = manifest.get("expected_guarantee")
        if want_status and record.get("status") != want_status:
            diags.append(diag("QRY-CORPUS-002", "execution_status_mismatch", "execution.json",
                              f"Execution status {record.get('status')!r} does not match "
                              f"the case pin {want_status!r}"))
        if want_guarantee:
            got_g = (record.get("guarantee") or {}).get("kind")
            if got_g != want_guarantee:
                diags.append(diag("QRY-CORPUS-002", "execution_guarantee_mismatch", "execution.json",
                                  f"Execution guarantee {got_g!r} does not match "
                                  f"the case pin {want_guarantee!r}"))
    # QV5-07: budget truncation weakens the guarantee or marks the result
    # incomplete (30.2); truncation is an execution fact, so the check
    # lives here, not in plan validation.
    if record.get("status") == "incomplete_with_continuation" \
            and (record.get("guarantee") or {}).get("kind") == "exact":
        diags.append(diag("QV5-07", "truncation_labeled_exact", "execution.json:guarantee",
                          "Budget-truncated (incomplete) execution carries the exact guarantee"))
    # Continuation drift (QPATH-035): resuming against a later branch head
    # must fail the 30.3 binding.
    resume_path = path / "resume_source.json"
    if resume_path.exists():
        cont = record.get("continuation")
        if not cont:
            diags.append(diag("QRY-CORPUS-003", "missing_continuation", "execution.json",
                              "Case declares a resume source but the record has no continuation"))
        else:
            try:
                resume_src = load_json(resume_path)
            except Exception as e:
                diags.append(diag("QRY-SCHEMA-003", "json_parse", str(resume_path), str(e)))
            else:
                names = list(query.get("sources", {}))
                if len(names) != 1:
                    diags.append(diag("QRY-CORPUS-004", "resume_source_mismatch", str(resume_path),
                                      "Resume check requires exactly one query source"))
                else:
                    resume_query = {**query, "sources": {names[0]: resume_src}}
                    diags.extend(semantic_diagnostics(resume_query))
                    rqd = query_digest(resume_query)
                    rsm = source_manifest(resume_query)["manifest_digest"]
                    if cont.get("query_digest") != rqd or cont.get("source_manifest") != rsm:
                        diags.append(diag("QRY-EXEC-002", "continuation_binding_mismatch",
                                          "continuation",
                                          "Continuation binding mismatch (30.3): resuming against "
                                          "a later branch head fails the source-manifest binding"))
    return diags


def validate_case_dir(path: Path, check_match: bool = True,
                      manifest: dict | None = None) -> list[Diagnostic]:
    query_path = path / "query.json"
    cert_path = path / "certificate.json"
    bounds_path = path / "expected_bounds.json"
    diags: list[Diagnostic] = []
    if not query_path.exists():
        return [diag("QRY-SCHEMA-000", "missing_file", str(query_path), "query.json missing")]
    try:
        query = load_json(query_path)
    except Exception as e:
        return [diag("QRY-SCHEMA-000", "json_parse", str(query_path), str(e))]
    diags.extend(validate_json_schema(query, "qry_query.schema.json", "query"))
    if diags:
        return sorted(diags, key=lambda d: (d.rule_id, d.target, d.message))
    diags.extend(semantic_diagnostics(query))
    if not diags:
        if (path / "rewrite.json").exists():
            diags.extend(validate_rewrite_case(query, path))
            return sorted(diags, key=lambda d: (d.rule_id, d.target, d.message))
        if (path / "execution.json").exists():
            diags.extend(validate_execution_case(query, path, manifest))
            return sorted(diags, key=lambda d: (d.rule_id, d.target, d.message))
        if query.get("schema_version") == "qry.query.v0.3":
            diags.extend(validate_v3_case(query, path, check_match))
            return sorted(diags, key=lambda d: (d.rule_id, d.target, d.message))
        if bounds_path.exists():
            try:
                expected_bounds = load_json(bounds_path)
                diags.extend(validate_json_schema(expected_bounds, "qry_bounds.schema.json", "expected_bounds"))
                if not diags:
                    actual = root_bound(query).to_json()
                    expected_root = expected_bounds.get("root_bound")
                    if actual != expected_root:
                        diags.append(diag("QRY-BOUND-001", "bound_mismatch", "expected_bounds.root_bound", "Expected root bound does not match inferred bound"))
            except Exception as e:
                diags.append(diag("QRY-BOUND-000", "bounds_error", str(bounds_path), str(e)))
        cert = None
        if cert_path.exists():
            try:
                cert = load_json(cert_path)
                diags.extend(validate_json_schema(cert, "qry_certificate.schema.json", "certificate"))
            except Exception as e:
                diags.append(diag("QRY-CERT-000", "certificate_error", str(cert_path), str(e)))
        if not any(d.rule_id.startswith("QRY-CERT") for d in diags):
            diags.extend(validate_certificate(query, cert))
    return sorted(diags, key=lambda d: (d.rule_id, d.target, d.message))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    case_dir = Path(args.case_dir)
    manifest_path = case_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else None
    diags = validate_case_dir(case_dir, manifest=manifest)
    if args.json:
        print(json.dumps([d.to_json() for d in diags], indent=2, sort_keys=True))
    else:
        if not diags:
            print("valid")
        for d in diags:
            print(f"{d.severity}\t{d.rule_id}\t{d.category}\t{d.target}\t{d.message}")
    return 1 if any(d.severity == "error" for d in diags) else 0

if __name__ == "__main__":
    raise SystemExit(main())
