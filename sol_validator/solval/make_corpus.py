from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


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


def obj_ref(store: dict[str, bytes], data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = sha(data)
    store[h] = data
    return f"object:sha256:{h}"


def digest_ref(data: bytes | str) -> str:
    return f"digest:sha256:{sha(data)}"


def base_state() -> tuple[dict[str, Any], dict[str, bytes]]:
    """Assemble GOLD-01 from the RFC-SOL-0001 spec examples (Phase 4).

    Content is the RFC's own examples (sections 15, 16, 18, 21-27, 30, 41,
    42, 47, 48) with placeholder digests replaced by real sha256 digests of
    the actual content. This is the Change Control "examples must validate"
    gate and resolves erratum E-001: the 9999... duplication in the section
    18 / section 22 fragments is resolved by construction -- contract_hash
    is the digest of the produces contract, instruction_ref is the internal
    object reference to the instruction content (distinct digests of
    distinct content).

    run_012 is the reexecution run referenced by the section 27.3
    verification example; it re-executes the pipeline through cell_014 and
    rebinds the metrics table (identical content, deduplicated per section
    43). The concordance report object is the section 27.3 evidence object.
    """
    store: dict[str, bytes] = {}
    # Objects (section 42; content-addressed, real digests). Insertion order
    # matters for PATH-013 (first object is corrupted and must be referenced).
    metrics_obj = obj_ref(store, b"checkpoint,loss,eos_rate\nM0,3.42,0.71\nM200,2.98,0.43\n")
    plot_obj = obj_ref(store, b"fake-png-eos-plot")
    schema_obj = obj_ref(store, b"{schema: metrics_table}")
    instr_obj = obj_ref(store, b"Compare checkpoints M0, M200, and M2000.")
    sbom_obj = obj_ref(store, b"SPDX placeholder")
    reexec_obj = obj_ref(store, b"rerun metrics match within tolerance")
    strict_cfg_obj = obj_ref(store, b"delta_tie = 0.01")

    produces_014 = [
        {"name": "metrics_table", "mime_type": "application/x-parquet", "schema_ref": schema_obj}
    ]
    # E-001: contract_hash is the digest of the authored output contract
    # (section 18: "detected by commit diff over the produces array").
    contract_hash = digest_ref(json.dumps(produces_014, sort_keys=True, separators=(",", ":")))

    state: dict[str, Any] = {
        # Section 15 (runtime manifest), with the Q2 environment floor.
        "manifest": {
            "sol_version": "0.1",
            "artifact_type": "sol_notebook",
            "artifact_id": "art_01j9x7k9k5m2c8v6h3p4q2r1s0",
            "title": "Model Evaluation Report",
            "current_commit": "commit_042",
            "required_features": [
                "sol:feature/linear_execution",
                "sol:feature/internal_object_store",
                "sol:feature/machine_summary",
            ],
            "optional_features": ["sol:feature/signatures", "sol:feature/external_evidence"],
            "runtime": {
                "primary_language": "python",
                "language_version": "3.12",
                "kernel_adapter": "sol-kernel-python",
            },
            "environment": {
                "environment_id": "env_001",
                "package_manifest": digest_ref("requirements lock"),
                "kernel": "python",
                "kernel_version": "3.12",
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
            # Section 27.4: derived from verification records (one passed
            # reexecution of a subset of the artifact's assertions).
            "reproducibility_status": "partially_reproducible",
        },
        # Section 28.1 (linear execution) + section 41 / decision Q4 branch
        # records (branch heads are part of the Level 1 skeleton, section 11).
        "execution_structure": {
            "type": "linear",
            "cells": [
                "cell:cell_001",
                "cell:cell_010",
                "cell:cell_011",
                "cell:cell_014",
                "cell:cell_015",
                "cell:cell_claim_anchor_007",
            ],
            "branches": [
                {
                    "branch_id": "branch_001",
                    "name": "main",
                    "base_commit": None,
                    "head_commit": "commit:commit_042",
                    "created_by": "human:alice",
                    "purpose": "Primary integration branch.",
                },
                {
                    "branch_id": "branch_007",
                    "name": "strict_metric_threshold",
                    "base_commit": "commit:commit_042",
                    "head_commit": "commit:commit_043",
                    "created_by": "human:alice",
                    "purpose": "Test whether stricter pass criteria change the selected checkpoint.",
                },
            ],
        },
        # Sections 16.3-16.5 (actors), with the Q8 agent floor.
        "actors": {
            "human:alice": {
                "actor_id": "human:alice",
                "actor_type": "human",
                "display_name": "Alice",
                "auth_ref": "identity_provider:user_123",
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
        # Sections 18, 19, 8.3 (cells). cell_014 is the section 18 example.
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
                "contract_hash": contract_hash,
                "depends_on": ["cell:cell_010", "cell:cell_011"],
                "produces": produces_014,
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
                "produces": [{"name": "eos_plot", "mime_type": "image/png"}],
                "actor_id": "human:alice",
            },
            # Section 8.3 (anchor cell) + section 21 (record anchors field).
            "cell_claim_anchor_007": {
                "cell_id": "cell_claim_anchor_007",
                "cell_type": "sol:cell/anchor",
                "summary": "Places claim_007 into the narrative.",
                "source_hash": digest_ref("record:claim_007"),
                "anchors_record": "record:claim_007",
                "render_hint": {"style": "callout"},
                "actor_id": "agent:eval_reviewer_001",
            },
        },
        # Sections 21-27 (semantic records).
        "records": {
            "task_001": {
                "record_id": "task_001",
                "record_type": "sol:record/task",
                "task_type": "human_instruction",
                "summary": "Compare checkpoints M0, M200, and M2000.",
                # E-001: the section 22 example's 9999... placeholder is the
                # object reference to the instruction content itself.
                "instruction_ref": instr_obj,
                "created_by": "human:alice",
                "created_at": "2026-01-01T00:00:00Z",
                "data_sensitivity": "internal",
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
                "confidence_basis": "computed from metric delta and bootstrap interval",
                "created_by": "agent:eval_reviewer_001",
                "created_at": "2026-01-01T00:05:00Z",
                "depends_on": ["cell:cell_014#metrics_table", "cell:cell_014"],
                "supersedes": [],
                "superseded_by": None,
                "anchors": ["cell:cell_claim_anchor_007"],
                "status": {"lifecycle": "active", "staleness": "current", "verification": "verified"},
            },
            "evidence_011": {
                "record_id": "evidence_011",
                "record_type": "sol:record/evidence",
                "summary": "Metrics table showing M200 has lower EOS rate.",
                "evidence_type": "metric_table",
                "source_ref": "cell:cell_014#metrics_table",
                "source_object": metrics_obj,
                "supports": ["record:claim_007"],
                "derived_from": ["cell:cell_014", "run:run_008"],
                "created_by": "tool:sol_executor",
                "created_at": "2026-01-01T00:00:12Z",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
            "decision_002": {
                "record_id": "decision_002",
                "record_type": "sol:record/decision",
                "summary": "Promote M200 for next-stage testing.",
                "decision_type": "branch_selection",
                "candidates": ["branch:main", "branch:branch_007"],
                "selected": "branch:main",
                "decision_rule": "lowest_invalidated_outputs_then_human_review",
                "made_by": "human:alice",
                "based_on": ["record:claim_007", "record:evidence_011"],
                "created_at": "2026-01-01T00:05:00Z",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
            # Section 27.3 example (reexecution verification of claim_007,
            # referencing the reexecution run_012 and the concordance report).
            "verification_005": {
                "record_id": "verification_005",
                "record_type": "sol:record/verification",
                "summary": "Reexecution verification of claim_007.",
                "target": "record:claim_007",
                "method": "sol:verify/reexecution",
                "performed_by": "tool:sol_executor",
                "result": "passed",
                "concordance": {"type": "tolerance", "metric": "eos_rate_delta", "tolerance": 0.001},
                "evidence": ["run:run_012", reexec_obj],
                "created_at": "2026-01-01T00:10:00Z",
                "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
            },
        },
        # Section 30 (run records). run_008 is the section 30 example reduced
        # to this artifact's cells; run_012 is the reexecution run.
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
                "resource_usage": {"wall_time_ms": 12000, "cpu_time_ms": 8400, "peak_memory_bytes": 104857600},
            },
            "run_012": {
                "run_id": "run_012",
                "source_commit": "commit:commit_042",
                "result_commit": None,
                "actor_id": "tool:sol_executor",
                "task_ref": "record:task_001",
                "entry_point": "cell:cell_001",
                "status": "success",
                "cells_executed": ["cell:cell_001", "cell:cell_010", "cell:cell_011", "cell:cell_014"],
                "environment_id": "env_001",
                "started_at": "2026-01-01T00:09:00Z",
                "completed_at": "2026-01-01T00:09:05Z",
                "output_bindings": [
                    {"named_output": "cell:cell_014#metrics_table", "object_ref": metrics_obj, "mime_type": "application/x-parquet"},
                ],
                "resource_usage": {"wall_time_ms": 5000, "cpu_time_ms": 4100, "peak_memory_bytes": 52428800},
            },
        },
        # Commit history (sections 34, 41): main head commit_042; branch_007
        # carries commit_043 (stricter threshold, section 41 example).
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
            "commit_043": {
                "commit_id": "commit_043",
                "parents": ["commit:commit_042"],
                "branch": "branch_007",
                "author": "human:alice",
                "message": "Try stricter tie threshold",
                "changes": [
                    {"op": "modify_cell", "target": "cell:cell_010", "path": "/source", "value_ref": strict_cfg_obj},
                ],
                "created_at": "2026-01-01T00:05:00Z",
            },
        },
        # Object records (section 42; decisions Q3/Q5). Sizes are the
        # uncompressed byte lengths of the stored content.
        "object_records": {
            metrics_obj.rsplit(":", 1)[-1]: {
                "object_id": metrics_obj,
                "mime_type": "application/x-parquet",
                "compression": "sol:compression/none",
                "size_bytes": len(store[metrics_obj.rsplit(":", 1)[-1]]),
                "created_by": "cell:cell_014",
                "created_by_run": "run:run_008",
                "data_sensitivity": "internal",
            },
            plot_obj.rsplit(":", 1)[-1]: {
                "object_id": plot_obj,
                "mime_type": "image/png",
                "compression": "sol:compression/gzip",
                "size_bytes": len(store[plot_obj.rsplit(":", 1)[-1]]),
                "created_by": "cell:cell_015",
                "created_by_run": "run:run_008",
                "data_sensitivity": "internal",
            },
            schema_obj.rsplit(":", 1)[-1]: {
                "object_id": schema_obj,
                "mime_type": "application/json",
                "compression": "sol:compression/none",
                "size_bytes": len(store[schema_obj.rsplit(":", 1)[-1]]),
                "created_by": "cell:cell_014",
            },
            instr_obj.rsplit(":", 1)[-1]: {
                "object_id": instr_obj,
                "mime_type": "text/plain",
                "compression": "sol:compression/none",
                "size_bytes": len(store[instr_obj.rsplit(":", 1)[-1]]),
                "created_by": "human:alice",
            },
            sbom_obj.rsplit(":", 1)[-1]: {
                "object_id": sbom_obj,
                "mime_type": "application/spdx+json",
                "compression": "sol:compression/gzip",
                "size_bytes": len(store[sbom_obj.rsplit(":", 1)[-1]]),
                "created_by": "human:alice",
            },
            reexec_obj.rsplit(":", 1)[-1]: {
                "object_id": reexec_obj,
                "mime_type": "text/plain",
                "compression": "sol:compression/none",
                "size_bytes": len(store[reexec_obj.rsplit(":", 1)[-1]]),
                "created_by": "tool:sol_executor",
                "created_by_run": "run:run_012",
            },
            strict_cfg_obj.rsplit(":", 1)[-1]: {
                "object_id": strict_cfg_obj,
                "mime_type": "text/x-python-config",
                "compression": "sol:compression/none",
                "size_bytes": len(store[strict_cfg_obj.rsplit(":", 1)[-1]]),
                "created_by": "human:alice",
            },
        },
        # The committed render (section 47 example). output_object is a
        # placeholder here; write_gold01 fills the real digest in the second
        # pass (the renderer never executes code, INV-07).
        "renders": {
            "render_012": {
                "render_id": "render_012",
                "source_commit": "commit:commit_042",
                "target": "html",
                "created_at": "2026-01-01T00:10:00Z",
                "output_object": None,
                "includes_records": ["record:claim_007"],
                "stale_disclosures": [],
            }
        },
    }
    return state, store


def write_artifact(path: Path, state: dict[str, Any], store: dict[str, bytes], expected: list[str] | None = None, corrupt_objects: bool = False, write_summary: bool = True):
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
    dump(path / "diagnostics.json", state.get("diagnostics", []))
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
    # Write object records (decisions Q3/Q5; exploded layout: objects/records/).
    if state.get("object_records"):
        (path / "objects" / "records").mkdir(parents=True)
        for digest, orec in state["object_records"].items():
            dump(path / "objects" / "records" / f"{digest}.json", orec)
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


def write_gold01(path: Path, state: dict[str, Any], store: dict[str, bytes]):
    """Write GOLD-01 with its committed render (section 47) in two passes.

    Pass 1 writes the artifact without the render record. Pass 2 renders the
    committed HTML view from the written state (the renderer never executes
    code, INV-07), stores the HTML as an internal object, records render_012
    (section 47 example), and regenerates the machine summary.
    """
    write_artifact(path, state, store, expected=[])
    from .model import Artifact
    from .render import render_html
    from .validate import generate_machine_summary

    def dump(p: Path, obj: Any):
        p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")

    art = Artifact.load(path)
    html_doc = render_html(art, source_commit="commit_042")
    html_bytes = html_doc.encode("utf-8")
    html_obj = obj_ref(store, html_bytes)
    digest = html_obj.rsplit(":", 1)[-1]
    state["renders"]["render_012"]["output_object"] = html_obj
    state["object_records"][digest] = {
        "object_id": html_obj,
        "mime_type": "text/html",
        "compression": "sol:compression/none",
        "size_bytes": len(html_bytes),
        "created_by": "tool:sol_executor",
        "data_sensitivity": "internal",
    }
    dump(path / "renders" / "render_012.json", state["renders"]["render_012"])
    (path / "objects" / "sha256" / digest).write_bytes(html_bytes)
    # Re-render check: the committed view must be exactly what the renderer
    # produces from the final committed state (determinism, section 47).
    assert render_html(Artifact.load(path), source_commit="commit_042") == html_doc
    dump(path / "objects" / "records" / f"{digest}.json", state["object_records"][digest])
    art2 = Artifact.load(path)
    dump(path / "renders" / "machine_summary.json", generate_machine_summary(art2))


def mutate_for_pathology(name: str, state: dict[str, Any], store: dict[str, bytes]) -> list[str]:
    """Mutate state/store for a pathology and return expected rule IDs."""
    r = []
    if name == "PATH-001":
        state["runs"]["run_008"]["cells_executed"] = ["cell:cell_001", "cell:cell_014", "cell:cell_010"]
        r = ["V2-01"]
    elif name == "PATH-002":
        # cell_014 declares cell_010/cell_011 (section 18 example), so the
        # undeclared read targets cell_015, which it does not declare.
        state["runs"]["run_008"]["dependency_hints"] = [{"cell_id": "cell_014", "undeclared_reads": ["cell:cell_015"]}]
        r = ["V2-06"]
    elif name == "PATH-003":
        state["records"]["evidence_011"]["status"] = {"lifecycle": "active", "staleness": "stale", "verification": "needs_reverification"}
        state["records"]["verification_005"]["status"] = {"lifecycle": "active", "staleness": "stale", "verification": "unverified"}
        # Leave claim incorrectly current/verified.
        # V3-08 also fires: the single supporting evidence is stale, so the
        # aggregate evidence rule independently requires the claim to be stale.
        r = ["V2-05", "V3-01", "V3-08"]
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
        # The committed render (render_012) already includes claim_007
        # without disclosures, so the stale status alone breaks V5-02.
        # V2-05 also fires: decision_002 is based_on the now-stale claim.
        r = ["V5-02", "V2-05"]
    elif name == "PATH-008":
        state["commits"]["commit_042"]["author"] = "human:ghost"
        # V4-01/V4-03 also fire: the unknown author is not an allowed committer
        # on protected main and carries no capabilities.
        r = ["V1-02", "V4-01", "V4-03"]
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
        # Invalidate every valid binding of the named output (run_008 and
        # the reexecution run_012) so the reference no longer resolves.
        state["runs"]["run_008"]["output_bindings"][0]["status"] = "invalidated"
        state["runs"]["run_012"]["output_bindings"][0]["status"] = "invalidated"
        # V2-05 also fires: claim_007 depends_on the invalidated named
        # output (section 21) and was not marked stale.
        r = ["V1-05", "V2-05"]
    elif name == "PATH-024":
        state["manifest"]["required_features"].append("sol:feature/not_supported")
        r = ["V0-03"]
    elif name == "PATH-026":
        # Q7: cell summary must be non-empty.
        state["cells"]["cell_001"]["summary"] = ""
        r = ["V0-07"]
    elif name == "PATH-027":
        # Q8: agent actors require delegated_by.
        del state["actors"]["agent:eval_reviewer_001"]["delegated_by"]
        r = ["V0-08"]
    elif name == "PATH-028":
        # Q10: all three status dimensions are mandatory.
        del state["records"]["claim_007"]["status"]["verification"]
        r = ["V0-09"]
    elif name == "PATH-029":
        # Q3: object records must use a registered compression identifier.
        d = sha(b"checkpoint,loss,eos_rate\nM0,3.42,0.71\nM200,2.98,0.43\n")
        state["object_records"] = {
            d: {
                "object_id": f"object:sha256:{d}",
                "mime_type": "application/x-parquet",
                "compression": "sol:compression/lzma",
                "size_bytes": 42,
            }
        }
        r = ["V0-10"]
    elif name == "PATH-030":
        # Q11: machine summary must carry the stale component (corrupted post-generation).
        r = ["V0-11", "V5-03"]
    elif name == "PATH-031":
        # Q2: manifest environment requires package_manifest.
        del state["manifest"]["environment"]["package_manifest"]
        r = ["V0-12"]
    elif name == "PATH-025":
        state["records"]["verification_bad"] = {
            "record_id": "verification_bad",
            "record_type": "sol:record/verification",
            "target": "record:claim_007",
            "method": "sol:verify/reexecution",
            "performed_by": "tool:sol_executor",
            "result": "failed",
            "concordance": {"type": "divergent"},
            "summary": "Failed reexecution verification.",
            "created_at": "2026-01-01T00:11:00Z",
            "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
        }
        # Leave target verified.
        r = ["V3-02"]
    return r


def failure_record(run_id: str) -> dict[str, Any]:
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
        "summary": "Execution failed before completion; see failure details.",
        "created_at": "2026-01-01T00:02:00Z",
        "retryable": True,
        "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
    }


def add_proposal_lifecycle(state: dict[str, Any], store: dict[str, bytes], self_review: bool = False, divergent: bool = False):
    new_source = obj_ref(store, "metrics = compute_metrics_by_prompt_class(results)")
    prop = {
        "record_id": "proposal_003",
        "record_type": "sol:record/proposal",
        "base_commit": "commit:commit_041",
        "changes": [{"op": "modify_cell", "target": "cell:cell_014", "path": "/source", "value_ref": new_source}],
        "predicted_invalidations": ["cell:cell_015#eos_plot", "record:claim_007", "record:decision_002"],
        "rationale": "Break EOS rate out by prompt category.",
        "summary": "Proposes breaking EOS rate out by prompt category.",
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
        "comment": "Accepted. Rerun downstream plots after applying.",
        "summary": "Review of proposal_003.",
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
        if name == "GOLD-01":
            write_gold01(out_dir / name / "artifact.sol.d", state, store)
            (out_dir / name / "README.md").write_text(
                "# GOLD-01\n\n"
                "Golden corpus artifact, assembled from the RFC-SOL-0001 spec\n"
                "examples (sections 15, 16, 18, 21-27, 30, 41, 42, 47, 48) with\n"
                "placeholder digests replaced by real sha256 digests of the actual\n"
                "content. This is the Change Control \"examples must validate\" gate\n"
                "and resolves erratum E-001 (see docs/errata/RFC-SOL-0001-errata.md).\n"
                "Must validate with zero diagnostics.\n",
                encoding="utf-8",
            )
        else:
            write_artifact(out_dir / name / "artifact.sol.d", state, store, expected=[])
            (out_dir / name / "README.md").write_text(f"# {name}\n\nGolden corpus artifact.\n", encoding="utf-8")
    # Paths
    for n in range(1, 32):
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
        if name == "PATH-030":
            # Drop a required Q11 component after generation.
            p = artifact / "renders" / "machine_summary.json"
            summary = json.loads(p.read_text())
            del summary["stale"]
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
