"""Phase 9 gate harness: the v0.3.0 freeze gate (spec 44).

Re-evidences all 19 freeze-gate conditions from committed repository
artifacts with fresh digests, and writes the freeze report
(``freeze_report_v030.json`` at the repo root by default). The report
is a pure function of the repository state (no wall-clock fields), so
every digest in it recomputes from the committed files; the historical
``freeze_report.json`` (v0.1 reconstruction, 18/19) is retained
untouched.

Usage:
  python3 -m qryref.gate_check [OUTPUT.json]

Exit status: 0 when 19/19 (status FROZEN), 1 otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from .canonical import canonical_json, query_digest
from .check_certificate import check_file
from .disclosure import BASELINE_COUNT_BUCKETS, _valid_bucket_partition
from .rules import BOUND_RULES, VALIDATION_RULES
from .validate import validate_case_dir

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CASES = ROOT / "corpus" / "cases"
CERTS = ROOT / "certificates" / "rewrites"

# Gate condition 1: the 16 core logical operators and the bound-transfer
# rule that licenses each (Phase 1; the aggregate family covers Group).
OP_RULES = {
    "Annotate": "sol:bound/annotate/v1",
    "Difference": "sol:bound/difference/v1",
    "Distinct": "sol:bound/distinct/v1",
    "Evaluate": "sol:bound/structural_containment/v1",
    "Group": "sol:bound/count_set/v1",
    "Intersect": "sol:bound/intersect/v1",
    "Join": "sol:bound/join/v1",
    "LeastFixpoint": "sol:bound/least_fixpoint/v1",
    "Limit": "sol:bound/limit/v1",
    "Order": "sol:bound/order/v1",
    "Project": "sol:bound/project/v1",
    "Relation": "sol:bound/relation/v1",
    "Rename": "sol:bound/rename/v1",
    "Select": "sol:bound/select/v1",
    "TemporalSlice": "sol:bound/temporal_slice/v1",
    "Union": "sol:bound/union/v1",
}
AGGREGATE_FAMILY = ["sol:bound/count_set/v1", "sol:bound/sum/v1",
                    "sol:bound/min_max/v1", "sol:bound/avg_optional_prefix/v1"]

# Gate condition 18: the mandatory kernel and its adversarial corpus case
# per rule (37.4).
MANDATORY_RULES = [
    "sol:rewrite/associate_exact_join/v1",
    "sol:rewrite/normalize_union/v1",
    "sol:rewrite/prune_exact_projection/v1",
    "sol:rewrite/push_exact_selection_through_join/v1",
    "sol:rewrite/substitute_exact_machine_summary/v1",
]
ADVERSARIAL_CASES = {
    "sol:rewrite/associate_exact_join/v1": "QPATH-045",
    "sol:rewrite/normalize_union/v1": "QPATH-046",
    "sol:rewrite/prune_exact_projection/v1": "QPATH-044",
    "sol:rewrite/push_exact_selection_through_join/v1": "QPATH-022",
    "sol:rewrite/substitute_exact_machine_summary/v1": "QPATH-034",
}

TITLES = {
    1: "Bound-transfer rules are defined for every core logical operator",
    2: "Unsupported guarantee compositions deterministically reject or downgrade",
    3: "Canonical typed AST and canonicalization schemas are published",
    4: "At least one Substrait mapping profile is documented",
    5: "Rewrite-rule registration, proof-evidence classes, and assurance obligations are implemented",
    6: "Logical-disclosure baseline and validator rules are implemented",
    7: "Semantic evaluator materialization and evaluation-key contracts are implemented",
    8: "Exact evaluator runs over the exploded RFC-SOL-0001 representation",
    9: "Machine-summary substitution succeeds only for proven covering queries",
    10: "Every mandatory golden and pathological case passes with deterministic diagnostics",
    11: "Query and execution records validate against published schemas",
    12: "At least one end-to-end bounded query demonstrates honest budget degradation",
    13: "Structural one-sided bounds are implemented and pass QGOLD-013 through QGOLD-016",
    14: "Bounded-result provenance distinguishes lower-membership certification from upper-bound derivation and upper-only non-exclusion",
    15: "Assurance evidence participates in ordinary Sol staleness propagation, and stale assurance evaluates effectively as unknown",
    16: "Rewrites spanning policy or evaluator boundaries default to non-preserving unless explicitly proven",
    17: "sol:bound/avg_optional_prefix/v1 or an equal-or-stronger registered AVG rule passes its golden and pathological cases when inexact AVG support is claimed",
    18: "The mandatory rewrite kernel has machine-checkable property tests and at least one adversarial corpus case per rule; claimed proven rules meet the accepted proof-artifact profile",
    19: "Logical and physical leakage claims are separated, and no physical side-channel equivalence is inferred from logical rewriting alone",
}


def _load(p: Path):
    return json.loads(p.read_text())


def _case(name: str) -> tuple[set, set, bool]:
    """Run the corpus harness over one case. Returns (got, expected,
    ok) with ok = exact diagnostic-set match: the manifest is the
    complete contract (37.5 determinism)."""
    p = CASES / name
    manifest = _load(p / "manifest.json")
    expected = set(manifest.get("expected_diagnostics", []))
    diags = validate_case_dir(p, check_match=not expected, manifest=manifest)
    got = {d.rule_id for d in diags}
    return got, expected, got == expected


def _digest_of(obj: dict, field: str = "report_digest") -> str:
    content = {k: v for k, v in obj.items() if k != field}
    return "sha256:" + hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Conditions


def cond_1() -> dict:
    coverage = {op: rule for op, rule in sorted(OP_RULES.items())}
    ok = all(rule in BOUND_RULES for rule in OP_RULES.values()) \
        and all(rule in BOUND_RULES for rule in AGGREGATE_FAMILY)
    return {"passed": ok,
            "evidence": {"coverage": coverage,
                         "aggregate_family": AGGREGATE_FAMILY}}


def cond_2() -> dict:
    got003, exp003, ok003 = _case("QPATH-003")
    got006, exp006, ok006 = _case("QPATH-006")
    ok = ok003 and ok006 and "QV5-06" in VALIDATION_RULES
    return {"passed": ok,
            "evidence": {"QPATH-003": sorted(got003),
                         "QPATH-006": sorted(got006),
                         "qv5_06_registered": "QV5-06" in VALIDATION_RULES}}


def cond_3() -> dict:
    schemas = ["qry_query.schema.json", "qry_bounds_v3.schema.json",
               "qry_bounds.schema.json", "qry_certificate.schema.json",
               "qry_execution.schema.json"]
    ok = all((ROOT / "schemas" / s).exists() for s in schemas)
    q = _load(CASES / "QGOLD-001" / "query.json")
    return {"passed": ok,
            "evidence": {"schemas": [f"schemas/{s}" for s in schemas],
                         "query_digest": query_digest(q)}}


def cond_4() -> dict:
    profile_p = ROOT / "substrait" / "qry_substrait_profile.yaml"
    rec_p = ROOT / "substrait" / "mapping_digest.json"
    doc_p = ROOT / "substrait" / "mapping.md"
    rec = _load(rec_p)
    recomputed = "sha256:" + hashlib.sha256(
        canonical_json(yaml.safe_load(profile_p.read_text())).encode("utf-8")).hexdigest()
    ok = doc_p.exists() and recomputed == rec.get("mapping_digest")
    return {"passed": ok,
            "evidence": {"mapping_digest": rec.get("mapping_digest"),
                         "mapping_digest_recomputed": recomputed,
                         "profile_document": "qry_reference_impl/substrait/mapping.md",
                         "profile": "qry_reference_impl/substrait/qry_substrait_profile.yaml"}}


def cond_5() -> dict:
    reg_p = CERTS / "registry_report.json"
    reg = _load(reg_p)
    ok = _digest_of(reg) == reg.get("report_digest") \
        and all(r in reg["rules"] for r in MANDATORY_RULES)
    return {"passed": ok,
            "evidence": {"mandatory_rules": MANDATORY_RULES,
                         "registered": sorted(reg["rules"]),
                         "report_digest": reg.get("report_digest")}}


def cond_6() -> dict:
    rules = ["QV8-08", "QV9-03", "QV9-04", "QV9-05", "QV9-08"]
    ok = all(r in VALIDATION_RULES for r in rules) \
        and _valid_bucket_partition(BASELINE_COUNT_BUCKETS) \
        and "10-19" in BASELINE_COUNT_BUCKETS
    cases = {}
    for name in ("QGOLD-011", "QPATH-005", "QPATH-027", "QPATH-028", "QPATH-029"):
        got, exp, c_ok = _case(name)
        cases[name] = c_ok
        ok = ok and c_ok
    return {"passed": ok,
            "evidence": {"bucketed_cardinality": f"bucket:{'10-19'}",
                         "count_buckets": BASELINE_COUNT_BUCKETS,
                         "cases": cases,
                         "validator_rules": rules}}


def cond_7() -> dict:
    got, exp, ok = _case("QGOLD-009")
    q = _load(CASES / "QGOLD-009" / "query.json")
    assessment = next(s["assessment"] for s in q["sources"].values()
                      if "assessment" in s)
    return {"passed": ok,
            "evidence": {"case": "QGOLD-009",
                         "configuration_digest": assessment["configuration_digest"],
                         "evaluation_id": assessment["evaluation_id"],
                         "evaluator_id": assessment["evaluator_id"],
                         "result_object": assessment["result_object"]}}


def _runs_report() -> dict:
    return _load(ROOT / "evaluator_runs" / "report.json")


def cond_8() -> dict:
    runs = _runs_report()
    all_runs = [r for inst in runs["instances"].values() for r in inst["runs"]]
    ok = _digest_of(runs) == runs.get("report_digest") \
        and all(r["status"] == "complete" and r["guarantee"] == "exact"
                for r in all_runs)
    return {"passed": ok,
            "evidence": {"all_runs_complete_exact": len(all_runs),
                         "instances": {k: v["cases"] for k, v in
                                       runs["instances"].items()},
                         "profile": runs.get("profile"),
                         "report_digest": runs.get("report_digest")}}


def cond_9() -> dict:
    got005, exp005, ok005 = _case("QGOLD-005")
    got034, exp034, ok034 = _case("QPATH-034")
    expected = _load(CASES / "QGOLD-005" / "expected.json")
    ok = ok005 and ok034 and expected.get("applied") is True
    return {"passed": ok,
            "evidence": {"covering_applied": bool(expected.get("applied")),
                         "lossy_diagnostics": sorted(got034),
                         "lossy_rejected": "QV8-04" in got034}}


def cond_10() -> dict:
    rep = _load(ROOT / "corpus" / "report.json")
    ok = _digest_of(rep) == rep.get("report_digest") \
        and rep["normative"]["passed"] == rep["normative"]["total"] == 64 \
        and rep["supplemental"]["passed"] == rep["supplemental"]["total"] == 72
    return {"passed": ok,
            "evidence": {"normative": rep["normative"],
                         "report_digest": rep.get("report_digest"),
                         "supplemental": rep["supplemental"]}}


def cond_11() -> dict:
    cases = {}
    ok = (ROOT / "schemas" / "qry_execution.schema.json").exists()
    for name in ("QGOLD-001", "QGOLD-012", "QPATH-012", "QPATH-035"):
        got, exp, c_ok = _case(name)
        cases[name] = c_ok
        ok = ok and c_ok and (CASES / name / "execution.json").exists()
    return {"passed": ok,
            "evidence": {"cases": cases,
                         "schemas": ["schemas/qry_execution.schema.json",
                                     "schemas/qry_query.schema.json"]}}


def cond_12() -> dict:
    demo = _runs_report()["demo"]
    ok = demo["statuses"][-1] == "complete" \
        and demo["guarantees"][-1] == "exact" \
        and "incomplete_with_continuation" in demo["statuses"]
    return {"passed": ok,
            "evidence": {"final_rows": demo["final_rows"],
                         "guarantees": demo["guarantees"],
                         "query_digest": demo["query_digest"],
                         "result_object": demo["result_object"],
                         "statuses": demo["statuses"]}}


def cond_13() -> dict:
    cases = {}
    ok = True
    for name in ("QGOLD-013", "QGOLD-014", "QGOLD-015", "QGOLD-016"):
        _, _, c_ok = _case(name)
        cases[name] = c_ok
        ok = ok and c_ok
    return {"passed": ok, "evidence": {"cases": cases}}


def cond_14() -> dict:
    got018, exp018, ok018 = _case("QGOLD-018")
    got037, exp037, ok037 = _case("QPATH-037")
    got038, exp038, ok038 = _case("QPATH-038")
    ok = ok018 and ok037 and ok038
    return {"passed": ok,
            "evidence": {"golden": ok018,
                         "pathologies": {"QPATH-037": sorted(got037),
                                         "QPATH-038": sorted(got038)}}}


def cond_15() -> dict:
    got, exp, ok = _case("QPATH-023")
    return {"passed": ok and "QV5-10" in got,
            "evidence": {"case": "QPATH-023",
                         "diagnostics": sorted(got),
                         "stale_evaluates_as_unknown": "QV5-10" in got}}


def cond_16() -> dict:
    got026, exp026, ok026 = _case("QPATH-026")
    got021, exp021, ok021 = _case("QGOLD-021")
    expected = _load(CASES / "QGOLD-021" / "expected.json")
    ok = ok026 and ok021 and expected.get("applied") is True \
        and {"QV7-07", "QV9-09"} <= got026
    return {"passed": ok,
            "evidence": {"boundary_crossing_rejected": sorted(got026),
                         "disclosure_proof_applied": bool(expected.get("applied")),
                         "proof_certificate": "certificates/rewrites/disclosure-proof.json"}}


def cond_17() -> dict:
    got020, exp020, ok020 = _case("QGOLD-020")
    got042, exp042, ok042 = _case("QPATH-042")
    bounds = _load(CASES / "QGOLD-020" / "expected_bounds.json")
    ok = ok020 and ok042 and "QV5-12" in got042
    return {"passed": ok,
            "evidence": {"QGOLD-020": ok020,
                         "QPATH-042": sorted(got042),
                         "intervals": bounds["root_bound"]["intervals"],
                         "rule_id": bounds["root_bound"]["bound_rule"]}}


def cond_18() -> dict:
    ok = True
    certificates = []
    for slug in ("join-associativity", "machine-summary-substitution",
                 "projection-pruning", "selection-pushdown",
                 "union-normalization"):
        p = CERTS / f"{slug}.json"
        c = _load(p)
        c_ok, detail = check_file(p)
        ok = ok and c_ok
        certificates.append({"cases": c.get("cases"),
                             "path": f"qry_reference_impl/certificates/rewrites/{p.name}",
                             "rule_slug": c.get("rule_slug"),
                             "transcript_digest": c.get("transcript_digest"),
                             "verified": c_ok})
    # The disclosure proof and the committed covering proofs verify too.
    for name in ("disclosure-proof.json", "covering-proof.json",
                 "covering-proof-gold.json", "covering-proof-heuristic.json"):
        ok = ok and check_file(CERTS / name)[0]
    adversarial = {}
    for rule, case in ADVERSARIAL_CASES.items():
        _, _, c_ok = _case(case)
        adversarial[rule] = [case]
        ok = ok and c_ok
    return {"passed": ok,
            "evidence": {"adversarial_cases": adversarial,
                         "certificates": certificates,
                         "disclosure_proof_verified": True,
                         "covering_proofs_verified": True}}


def cond_19() -> dict:
    got043, exp043, ok043 = _case("QPATH-043")
    got029, exp029, ok029 = _case("QPATH-029")
    got011, exp011, ok011 = _case("QGOLD-011")
    ok = ok043 and ok029 and ok011 \
        and {"QV7-09", "QV9-10"} <= got043 and "QV9-08" in got029
    return {"passed": ok,
            "evidence": {"cases": {"QGOLD-011": ok011,
                                   "QPATH-029": sorted(got029),
                                   "QPATH-043": sorted(got043)},
                         "physical_side_channel_equivalence":
                             "not_claimed: no physical conformance profile is "
                             "published for v0.3.0 (25.3); logical rewrites "
                             "cannot claim physical non-inference (QV7-09, "
                             "QV9-10)"}}


CONDITIONS = [cond_1, cond_2, cond_3, cond_4, cond_5, cond_6, cond_7,
              cond_8, cond_9, cond_10, cond_11, cond_12, cond_13,
              cond_14, cond_15, cond_16, cond_17, cond_18, cond_19]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("output", nargs="?",
                    default=str(REPO / "freeze_report_v030.json"))
    args = ap.parse_args(argv)

    conditions = []
    for i, fn in enumerate(CONDITIONS, start=1):
        result = fn()
        conditions.append({
            "number": i,
            "title": TITLES[i],
            "passed": result["passed"],
            "evidence": result["evidence"],
        })
    passed = sum(1 for c in conditions if c["passed"])
    report = {
        "format": "solqry-freeze-gate-report/v1",
        "spec": "RFC-SOL-QRY-0001 v0.3.0 design draft, 44",
        "authoritative_feedback_source":
            "executable bound-algebra implementation, validators, and the "
            "committed corpus, certificate, and recorded-run artifacts",
        "conditions": conditions,
        "passed": passed,
        "failed": len(conditions) - passed,
        "status": "FROZEN" if passed == len(conditions) else "NOT_FROZEN",
    }
    report["report_digest"] = _digest_of(report)
    out = Path(args.output)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    out.chmod(0o644)
    for c in conditions:
        print(f"{'ok' if c['passed'] else 'FAIL'}\t{c['number']:>2}\t{c['title']}")
    print(f"{passed}/{len(conditions)} gate conditions satisfied; "
          f"status {report['status']}; report {out} report_digest "
          f"{report['report_digest']}")
    return 0 if passed == len(conditions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
