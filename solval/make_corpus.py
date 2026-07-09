from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .validate import generate_machine_summary
from .model import Artifact

ROOT_FEATURES = [
    "sol:feature/linear_execution",
    "sol:feature/internal_object_store",
    "sol:feature/machine_summary",
    "sol:feature/external_evidence",
]


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def obj_ref(store: Dict[str, bytes], data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = sha(data)
    store[h] = data
    return f"object:sha256:{h}"


def digest_ref(data: bytes | str) -> str:
    return f"digest:sha256:{sha(data)}"


def base_state() -> Tuple[Dict[str, Any], Dict[str, bytes]]:
    store: Dict[str, bytes] = {}
    metrics_obj = obj_ref(store, b"checkpoint,loss,eos_rate\nM0,3.42,0.71\nM200,2.98,0.43\n")
    plot_obj = obj_ref(store, b"fake-png-eos-plot")
    schema_obj = obj_ref(store, b"{schema: metrics_table}")
    instr_obj = obj_ref(store, b"Compare checkpoints M0, M200, and M2000.")
    sbom_obj = obj_ref(store, b"SPDX placeholder")
    reexec_obj = obj_ref(store, b"rerun metrics match within tolerance")

    state: Dict[str, Any] = {
        "manifest": {
            "sol_version": "0.1",
            "artifact_type": "sol_notebook",
            "artifact_id": "art_01j9x7k9k5m2c8v6h3p4q2r1s0",
            "required_features": list(ROOT_FEATURES),
            "optional_features": ["sol:feature/signatures"],
            "title": "Model Evaluation Report",
            "current_commit": "commit_042",
            "runtime": {
                "primary_language": "python",
                "language_version": "3.12",
                "kernel_adapter": "sol-kernel-python",
            },
            "environment": {
                "environment_id": "env_001",
                "package_manifest": digest_ref("requirements lock"),
                "sbom_ref": sbom_obj,
            },
            "execution": {
                "structure": "linear",
                "partial_execution_policy": "invalidate_downstream",
                "deterministic": False,
                "random_seed": 1234,
            },
            "security": {
                "sandbox_profile": "sandbox_minimal",
                "network_access": False,
                "execution_requires_confirmation": True,
            },
            "rendering": {"default_view": "html", "allowed_views": ["html", "markdown", "audit", "machine_summary"]},
            "authorization": {
                "permit_self_application": False,
                "protected_branches": [
                    {"branch": "main", "protected": True, "required_capabilities": ["approve"], "allowed_committers": ["human:alice"]}
                ],
            },
            "reproducibility_status": "unknown",
        },
        "execution_structure": {
            "type": "linear",
            "cells": ["cell:cell_001", "cell:cell_010", "cell:cell_011", "cell:cell_014", "cell:cell_015"],
        },
        "actors": {
            "human:alice": {
                "actor_id": "human:alice",
                "actor_type": "human",
                "display_name": "Alice",
                "capabilities": [
                    "read", "write_cell", "write_record", "execute", "commit", "create_branch", "apply_proposal",
                    "review", "approve", "render", "sign", "redact", "export"
                ],
            },
            "agent:eval_reviewer_001": {
                "actor_id": "agent:eval_reviewer_001",
                "actor_type": "agent",
                "model_id": "provider/model-name",
                "model_version": "2026-01-01",
                "configuration_digest": digest_ref("agent configuration"),
                "prompt_template_digest": digest_ref("prompt template"),
                "tool_policy_digest": digest_ref("tool policy"),
                "delegated_by": "human:alice",
                "autonomy_level": "review_required",
            },
            "tool:sol_executor": {
                "actor_id": "tool:sol_executor",
                "actor_type": "tool",
                "tool_name": "sol-executor",
                "tool_version": "0.1",
                "environment_id": "env_001",
                "capabilities": ["read", "execute", "commit", "render"],
            },
        },
        "cells": {
            "cell_001": {
                "cell_id": "cell_001",
                "cell_type": "sol:cell/prose",
                "title": "Task",
                "summary": "Introduces the checkpoint comparison task.",
                "source": "Compare checkpoints.",
                "source_hash": digest_ref("Compare checkpoints."),
                "actor_id": "human:alice",
            },
            "cell_010": {
                "cell_id": "cell_010",
                "cell_type": "sol:cell/config",
                "title": "Config",
                "summary": "Defines evaluation thresholds.",
                "source": "delta_tie = 0.02",
                "source_hash": digest_ref("delta_tie = 0.02"),
                "depends_on": ["cell:cell_001"],
                "actor_id": "human:alice",
            },
            "cell_011": {
                "cell_id": "cell_011",
                "cell_type": "sol:cell/data",
                "title": "Dataset",
                "summary": "Binds the evaluation dataset.",
                "source": "eval_dataset = frozen_dataset_v1",
                "source_hash": digest_ref("eval_dataset = frozen_dataset_v1"),
                "depends_on": ["cell:cell_010"],
                "actor_id": "human:alice",
            },
            "cell_014": {
                "cell_id": "cell_014",
                "cell_type": "sol:cell/code",
                "title": "Compute Evaluation Metrics",
                "summary": "Computes loss, accuracy, and EOS rate for each checkpoint.",
                "language": "python",
                "source": "metrics = compute_metrics(results)",
                "source_hash": digest_ref("metrics = compute_metrics(results)"),
                "contract_hash": digest_ref("metrics_table:application/x-parquet"),
                "depends_on": ["cell:cell_011"],
                "produces": [
                    {"name": "metrics_table", "mime_type": "application/x-parquet", "schema_ref": schema_obj}
                ],
                "actor_id": "human:alice",
            },
            "cell_015": {
                "cell_id": "cell_015",
                "cell_type": "sol:cell/display",
                "title": "Metrics Table",
                "summary": "Displays the current metrics table.",
                "source_hash": digest_ref("display metrics"),
                "depends_on": ["cell:cell_014"],
                "display_ref": "cell:cell_014#metrics_table",
                "actor_id": "human:alice",
            },
        },
        "records": {
            "task_001": {
                "record_id": "task_001",
                "record_type": "sol:record/task",
                "task_type": "human_instruction",
                "summary": "Compare checkpoints M0, M200, and M2000.",
                "instruction_ref": instr_obj,
                "created_by": "human:alice",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
            "evidence_011": {
                "record_id": "evidence_011",
                "record_type": "sol:record/evidence",
                "evidence_type": "metric_table",
                "summary": "Metrics table showing M200 has lower EOS rate.",
                "source_ref": "cell:cell_014#metrics_table",
                "source_object": metrics_obj,
                "supports": ["record:claim_007"],
                "derived_from": ["cell:cell_014", "run:run_008"],
                "created_by": "tool:sol_executor",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
            "claim_007": {
                "record_id": "claim_007",
                "record_type": "sol:record/claim",
                "summary": "M200 has lower EOS hazard than M0 on open-ended prompts.",
                "statement": "Checkpoint M200 has lower EOS hazard than M0 on open-ended prompts.",
                "claim_type": "empirical_result",
                "supporting_evidence": ["record:evidence_011"],
                "confidence": 0.82,
                "confidence_basis": "computed from metric delta",
                "created_by": "agent:eval_reviewer_001",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "verified"},
            },
            "decision_002": {
                "record_id": "decision_002",
                "record_type": "sol:record/decision",
                "summary": "Promote M200 for next-stage testing.",
                "decision_type": "branch_selection",
                "candidates": ["branch:main"],
                "selected": "branch:main",
                "decision_rule": "human_review_after_metrics",
                "made_by": "human:alice",
                "based_on": ["record:claim_007", "record:evidence_011"],
                "created_at": "2026-01-01T00:00:00Z",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
            "verification_005": {
                "record_id": "verification_005",
                "record_type": "sol:record/verification",
                "target": "record:claim_007",
                "method": "sol:verify/reexecution",
                "performed_by": "tool:sol_executor",
                "result": "passed",
                "concordance": {"type": "tolerance", "metric": "eos_rate_delta", "tolerance": 0.001},
                "evidence": ["run:run_008", reexec_obj],
                "created_at": "2026-01-01T00:10:00Z",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
        },
        "runs": {
            "run_008": {
                "run_id": "run_008",
                "source_commit": "commit:commit_041",
                "result_commit": "commit:commit_042",
                "actor_id": "tool:sol_executor",
                "task_ref": "record:task_001",
                "entry_point": "cell:cell_001",
                "status": "success",
                "cells_executed": ["cell:cell_001", "cell:cell_010", "cell:cell_011", "cell:cell_014", "cell:cell_015"],
                "environment_id": "env_001",
                "started_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:00:12Z",
                "output_bindings": [
                    {"named_output": "cell:cell_014#metrics_table", "object_ref": metrics_obj, "mime_type": "application/x-parquet"},
                    {"named_output": "cell:cell_015#eos_plot", "object_ref": plot_obj, "mime_type": "image/png"},
                ],
            }
        },
        "commits": {
            "commit_041": {
                "commit_id": "commit_041",
                "parents": [],
                "branch": "main",
                "author": "human:alice",
                "message": "Initial artifact",
                "changes": [{"op": "init"}],
                "created_at": "2026-01-01T00:00:00Z",
            },
            "commit_042": {
                "commit_id": "commit_042",
                "parents": ["commit:commit_041"],
                "branch": "main",
                "author": "human:alice",
                "message": "Run evaluation",
                "changes": [
                    {"op": "bind_output", "named_output": "cell:cell_014#metrics_table", "object_id": metrics_obj},
                    {"op": "bind_output", "named_output": "cell:cell_015#eos_plot", "object_id": plot_obj},
                ],
                "created_at": "2026-01-01T00:00:12Z",
            },
        },
        "renders": {
            "report": {
                "render_id": "report",
                "source_commit": "commit:commit_042",
                "target": "html",
                "includes_records": ["record:claim_007"],
                "stale_disclosures": [],
            }
        },
    }
    return state, store


def write_artifact(path: Path, state: Dict[str, Any], store: Dict[str, bytes], expected: List[str] | None = None, corrupt_objects: bool = False, write_summary: bool = True):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / "cells").mkdir()
    (path / "records").mkdir()
    (path / "actors").mkdir()
    (path / "runs").mkdir()
    (path / "commits").mkdir()
    (path / "objects" / "sha256").mkdir(parents=True)
    (path / "renders").mkdir()
    def dump(p: Path, obj: Any):
        p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    dump(path / "manifest.json", state["manifest"])
    dump(path / "execution_structure.json", state["execution_structure"])
    for dname, key in [("cells", "cell_id"), ("records", "record_id"), ("actors", "actor_id"), ("runs", "run_id"), ("commits", "commit_id")]:
        for obj in state[dname].values():
            fname = obj[key].replace(":", "_") + ".json"
            dump(path / dname / fname, obj)
    # Write object store.
    for digest, data in store.items():
        out = path / "objects" / "sha256" / digest
        if corrupt_objects and digest == next(iter(store.keys())):
            out.write_bytes(b"corrupted")
        else:
            out.write_bytes(data)
    # Write renders other than machine summary first.
    for rid, obj in state.get("renders", {}).items():
        dump(path / "renders" / f"{rid}.json", obj)
    # Generate machine summary from written artifact.
    if write_summary:
        from .model import Artifact
        from .validate import generate_machine_summary
        art = Artifact.load(path)
        summary = generate_machine_summary(art)
        dump(path / "renders" / "machine_summary.json", summary)
    dump(path / "expected_diagnostics.json", {"expected_rule_ids": expected or []})


def mutate_for_pathology(name: str, state: Dict[str, Any], store: Dict[str, bytes]) -> List[str]:
    """Mutate state/store for a pathology and return expected rule IDs."""
    r = []
    if name == "PATH-001":
        state["runs"]["run_008"]["cells_executed"] = ["cell:cell_001", "cell:cell_014", "cell:cell_010"]
        r = ["V2-01"]
    elif name == "PATH-002":
        state["runs"]["run_008"]["dependency_hints"] = [{"cell_id": "cell_014", "undeclared_reads": ["cell:cell_010"]}]
        r = ["V2-06"]
    elif name == "PATH-003":
        state["records"]["evidence_011"]["status"] = {"lifecycle": "active", "staleness": "stale", "verification": "needs_reverification"}
        state["records"]["verification_005"]["status"] = {"lifecycle": "active", "staleness": "stale", "verification": "unverified"}
        # Leave claim incorrectly current/verified.
        r = ["V2-05", "V3-01"]
    elif name == "PATH-004":
        state["records"]["claim_007"]["status_transition"] = {"from": "stale", "to": "current", "via": "direct_write"}
        r = ["V3-02"]
    elif name == "PATH-005":
        state["commits"]["commit_042"]["changes"].append({"op": "apply_proposal", "proposal": "record:proposal_missing"})
        r = ["V3-05"]
    elif name == "PATH-006":
        state["records"]["evidence_011"]["source_object"] = "object:sha256:metrics_table"
        r = ["V0-05", "V0-06"]
    elif name == "PATH-007":
        state["records"]["claim_007"]["status"] = {"lifecycle": "active", "staleness": "stale", "verification": "needs_reverification"}
        state["renders"]["report"]["includes_records"] = ["record:claim_007"]
        state["renders"]["report"]["stale_disclosures"] = []
        r = ["V5-02"]
    elif name == "PATH-008":
        state["commits"]["commit_042"]["author"] = "human:ghost"
        r = ["V1-02"]
    elif name == "PATH-009":
        state["commits"]["commit_042"]["author"] = "agent:eval_reviewer_001"
        state["commits"]["commit_042"]["branch"] = "main"
        r = ["V4-01"]
    elif name == "PATH-010":
        add_proposal_lifecycle(state, store, self_review=True)
        r = ["V4-02"]
    elif name == "PATH-011":
        state["runs"]["run_008"]["status"] = "partial_success"
        state["runs"]["run_008"]["cells_executed"] = ["cell:cell_001", "cell:cell_010"]
        # Still binds output from cell_014, beyond prefix.
        state["records"]["failure_002"] = failure_record("run_008")
        r = ["V2-03"]
    elif name == "PATH-012":
        state["records"]["evidence_011"]["source_object"] = "file:metrics_table.parquet"
        # This is not parsed by current ref grammar, so also add a missing object ref reachable from evidence.
        state["records"]["evidence_011"]["snapshot_object"] = "object:sha256:" + "0"*64
        r = ["V0-06", "V1-06"]
    elif name == "PATH-013":
        r = ["V1-07"]
        state["_corrupt_objects"] = True
    elif name == "PATH-014":
        del state["records"]["verification_005"]
        r = ["V3-01"]
    elif name == "PATH-015":
        state["manifest"]["reproducibility_status"] = "reproducible"
        # remove reexecution verification
        del state["records"]["verification_005"]
        state["records"]["claim_007"]["status"]["verification"] = "unverified"
        r = ["V3-03"]
    elif name == "PATH-016":
        state["cells"]["cell_010"]["depends_on"] = ["cell:cell_014"]
        r = ["V2-02"]
    elif name == "PATH-017":
        state["cells"]["gate_003"] = {"cell_id": "gate_003", "cell_type": "sol:cell/gate", "summary": "Bad gate", "source_hash": digest_ref("gate"), "decision_ref": "record:decision_missing"}
        state["execution_structure"]["cells"].append("cell:gate_003")
        r = ["V1-04"]
    elif name == "PATH-018":
        state["cells"]["anchor_bad"] = {"cell_id": "anchor_bad", "cell_type": "sol:cell/anchor", "summary": "Echo", "source_hash": digest_ref("anchor"), "anchors_record": "record:claim_007", "statement": state["records"]["claim_007"]["statement"]}
        state["execution_structure"]["cells"].append("cell:anchor_bad")
        r = ["V1-03"]
    elif name == "PATH-019":
        # Will be handled by writing dishonest machine summary after valid summary generation.
        r = ["V5-03"]
    elif name == "PATH-020":
        state["records"]["evidence_011"] = {
            "record_id": "evidence_011",
            "record_type": "sol:record/evidence",
            "summary": "Unavailable external evidence.",
            "evidence_type": "external_source",
            "external_ref": {"uri": "https://example.invalid/source", "availability": "unavailable"},
            "supports": ["record:claim_007"],
            "created_by": "human:alice",
            "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
        }
        state["records"]["claim_007"]["supporting_evidence"] = ["record:evidence_011"]
        r = ["V3-08"]
    elif name == "PATH-021":
        # Remove metrics object after writing by marking absent from store.
        obj = state["records"]["evidence_011"]["source_object"].split(":")[-1]
        store.pop(obj, None)
        r = ["V0-06", "V1-06"]
    elif name == "PATH-022":
        add_proposal_lifecycle(state, store, divergent=True)
        r = ["V3-05"]
    elif name == "PATH-023":
        state["runs"]["run_008"]["output_bindings"][0]["status"] = "invalidated"
        r = ["V1-05"]
    elif name == "PATH-024":
        state["manifest"]["required_features"].append("sol:feature/not_supported")
        r = ["V0-03"]
    elif name == "PATH-025":
        state["records"]["verification_bad"] = {
            "record_id": "verification_bad",
            "record_type": "sol:record/verification",
            "target": "record:claim_007",
            "method": "sol:verify/reexecution",
            "performed_by": "tool:sol_executor",
            "result": "failed",
            "concordance": {"type": "divergent"},
            "created_at": "2026-01-01T00:11:00Z",
            "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
        }
        # Leave target verified.
        r = ["V3-02"]
    return r


def failure_record(run_id: str) -> Dict[str, Any]:
    return {
        "record_id": "failure_002",
        "record_type": "sol:record/failure",
        "run_id": f"run:{run_id}",
        "source_commit": "commit:commit_042",
        "actor_id": "tool:sol_executor",
        "failed_cell": "cell:cell_014",
        "error_type": "ExampleError",
        "message": "example failure",
        "environment_id": "env_001",
        "created_at": "2026-01-01T00:02:00Z",
        "retryable": True,
    }


def add_proposal_lifecycle(state: Dict[str, Any], store: Dict[str, bytes], self_review: bool = False, divergent: bool = False):
    new_source = obj_ref(store, "metrics = compute_metrics_by_prompt_class(results)")
    prop = {
        "record_id": "proposal_003",
        "record_type": "sol:record/proposal",
        "base_commit": "commit:commit_041",
        "changes": [{"op": "modify_cell", "target": "cell:cell_014", "path": "/source", "value_ref": new_source}],
        "predicted_invalidations": ["record:claim_007"],
        "rationale": "Break EOS rate out by prompt category.",
        "created_by": "agent:eval_reviewer_001",
        "status": {"lifecycle": "applied", "staleness": "current", "verification": "unverified"},
    }
    reviewer = "agent:eval_reviewer_001" if self_review else "human:alice"
    review = {
        "record_id": "review_004",
        "record_type": "sol:record/review",
        "proposal_id": "record:proposal_003",
        "reviewed_by": reviewer,
        "review_status": "accepted",
        "comment": "accepted",
        "created_at": "2026-01-01T00:00:00Z",
        "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
    }
    state["records"]["proposal_003"] = prop
    state["records"]["review_004"] = review
    commit = state["commits"]["commit_042"]
    commit["applied_proposals"] = [{"proposal": "record:proposal_003", "accepted_by": ["record:review_004"]}]
    if divergent:
        commit["changes"].insert(0, {"op": "apply_proposal", "proposal": "record:proposal_003"})
        # Wrong target/path/value_ref: proposal changeset not represented.
        commit["changes"].append({"op": "modify_cell", "target": "cell:cell_010", "path": "/source", "value_ref": new_source})
    else:
        commit["changes"].insert(0, {"op": "apply_proposal", "proposal": "record:proposal_003"})
        commit["changes"].append(prop["changes"][0])


def build_corpus(out_dir: Path):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    # Golds
    for i in range(1, 7):
        state, store = base_state()
        name = f"GOLD-{i:02d}"
        if name == "GOLD-02":
            state["cells"]["cell_016"] = {"cell_id": "cell_016", "cell_type": "sol:cell/code", "title": "Failing follow-up", "summary": "Cell that fails after valid prefix.", "source": "raise RuntimeError()", "source_hash": digest_ref("raise RuntimeError()"), "depends_on": ["cell:cell_015"], "actor_id": "human:alice"}
            state["execution_structure"]["cells"].append("cell:cell_016")
            state["runs"]["run_008"]["status"] = "partial_success"
            state["runs"]["run_008"]["cells_executed"] = ["cell:cell_001", "cell:cell_010", "cell:cell_011", "cell:cell_014", "cell:cell_015"]
            state["records"]["failure_002"] = failure_record("run_008")
            state["records"]["failure_002"]["failed_cell"] = "cell:cell_016"
        elif name == "GOLD-03":
            add_proposal_lifecycle(state, store)
        elif name == "GOLD-04":
            # Recovered after stale: all final statuses current/verified as base.
            pass
        elif name == "GOLD-05":
            snap = obj_ref(store, b"archived external source")
            state["records"]["evidence_012"] = {
                "record_id": "evidence_012",
                "record_type": "sol:record/evidence",
                "summary": "Archived external source.",
                "evidence_type": "external_source",
                "external_ref": {"uri": "https://example.org/paper.pdf", "retrieved_at": "2026-01-01T00:00:00Z", "snapshot_object": snap, "availability": "archived"},
                "supports": ["record:claim_007"],
                "created_by": "human:alice",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            }
            state["records"]["claim_007"]["supporting_evidence"].append("record:evidence_012")
        elif name == "GOLD-06":
            state["manifest"]["imported_from"] = "ipynb"
            state["manifest"]["provenance_status"] = "incomplete"
        write_artifact(out_dir / name / "artifact.sol.d", state, store, expected=[])
        (out_dir / name / "README.md").write_text(f"# {name}\n\nGolden corpus artifact.\n", encoding="utf-8")
    # Paths
    for n in range(1, 26):
        name = f"PATH-{n:03d}"
        state, store = base_state()
        expected = mutate_for_pathology(name, state, store)
        corrupt = bool(state.pop("_corrupt_objects", False))
        artifact = out_dir / name / "artifact.sol.d"
        write_artifact(artifact, state, store, expected=expected, corrupt_objects=corrupt)
        if name == "PATH-019":
            # Corrupt machine summary after generation.
            p = artifact / "renders" / "machine_summary.json"
            summary = json.loads(p.read_text())
            summary["records"].append({"record_id": "claim_fake", "record_type": "sol:record/claim", "summary": "not actually present", "status": {}})
            p.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        (out_dir / name / "README.md").write_text(f"# {name}\n\nPathology corpus artifact. Expected rules: {', '.join(expected)}\n", encoding="utf-8")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Build Sol pathology corpus")
    ap.add_argument("out", nargs="?", default="corpus")
    args = ap.parse_args()
    build_corpus(Path(args.out))
    print(f"wrote corpus to {args.out}")

if __name__ == "__main__":
    main()
