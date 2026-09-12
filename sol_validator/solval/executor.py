"""Reference executor (RFC-SOL-0001 section 12.5).

Executes a linear artifact's cells in committed execution order against a
declared kernel model and produces committed run records, output bindings,
provenance, and failure records per sections 30/31/32.

Safety (INV-07, section 49): the reference executor never executes cell
source as code. Cell source is matched against registered kernel
operations; unregistered source is a failure, not an execution. Opening or
rendering an artifact never implies execution; execution requires explicit
confirmation when the manifest declares execution_requires_confirmation.

Committed-run semantics (sections 30/31):
  success           all cells completed; all declared outputs bound.
  partial_success   a prefix completed; the prefix's outputs commit
                    atomically with the paired failure record (same run_id).
  failure           the first cell failed; no partial outputs commit.
Cells at or beyond the failure point are unexecuted for that run.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections.abc import Callable

from .model import Artifact

DEMO_STARTED_AT = "2026-01-01T01:00:00Z"
DEMO_COMPLETED_AT = "2026-01-01T01:00:02Z"
DEMO_COMMIT_AT = "2026-01-01T01:00:02Z"


class CellExecutionError(Exception):
    """A registered kernel operation failed."""


@dataclass
class Kernel:
    """A registry of registered cell computations.

    Handlers are looked up by exact cell source (cells that carry source)
    or by cell_id (cells without source, e.g. display cells). A handler
    returns a dict mapping declared output names to output bytes.
    """

    by_source: dict[str, Callable[[], dict[str, bytes]]] = field(default_factory=dict)
    by_cell_id: dict[str, Callable[[], dict[str, bytes]]] = field(default_factory=dict)

    def register_source(self, source: str, handler: Callable[[], dict[str, bytes]]) -> Kernel:
        self.by_source[source] = handler
        return self

    def register_cell(self, cell_id: str, handler: Callable[[], dict[str, bytes]]) -> Kernel:
        self.by_cell_id[cell_id] = handler
        return self

    def lookup(self, cell: dict[str, Any]) -> Callable[[], dict[str, bytes]] | None:
        source = cell.get("source")
        if isinstance(source, str) and source:
            return self.by_source.get(source)
        return self.by_cell_id.get(cell.get("cell_id", ""))


@dataclass
class ExecutionResult:
    run_id: str
    status: str
    cells_executed: list[str]
    output_bindings: list[dict[str, Any]]
    failure_record: dict[str, Any] | None
    commit_id: str
    artifact_path: Path
    diagnostics: list[str] = field(default_factory=list)


def _next_ids(artifact: Artifact) -> tuple[str, str, str]:
    """Deterministic next run/failure/commit ids (demo: 100-series)."""
    return "run_100", "failure_100", "commit_100"


def execute(
    artifact_path: str | Path,
    kernel: Kernel,
    out_path: str | Path,
    run_actor: str = "tool:sol_executor",
    commit_author: str = "human:alice",
    confirm: bool = False,
) -> ExecutionResult:
    """Execute the artifact linearly and commit the result to out_path.

    The source artifact is copied; the result (run record, failure record,
    new objects, result commit, updated manifest, regenerated machine
    summary) is written to out_path and must validate cleanly.
    """
    artifact_path = Path(artifact_path)
    out_path = Path(out_path)
    if out_path.exists():
        shutil.rmtree(out_path)
    shutil.copytree(artifact_path, out_path)
    art = Artifact.load(out_path)

    manifest = art.manifest
    if manifest.get("security", {}).get("execution_requires_confirmation") and not confirm:
        raise PermissionError(
            "manifest declares execution_requires_confirmation; pass confirm=True"
        )
    if manifest.get("execution", {}).get("structure") != "linear":
        raise ValueError("reference executor v0.1 supports linear execution only")

    order = [
        ref.split(":", 1)[1] if ref.startswith("cell:") else ref
        for ref in (art.execution_structure or {}).get("cells", [])
    ]
    executed: list[str] = []
    bindings: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    objects: dict[str, bytes] = {}

    for cid in order:
        cell = art.cells.get(cid)
        if cell is None:
            raise ValueError(f"execution structure references missing cell {cid}")
        produces = cell.get("produces") or []
        # Code cells perform computation: the reference executor requires a
        # registered kernel operation for any code cell that carries source,
        # with or without a declared output contract (INV-07).
        needs_handler = bool(produces) or (
            cell.get("cell_type") == "sol:cell/code" and isinstance(cell.get("source"), str) and cell.get("source")
        )
        if not needs_handler:
            executed.append(f"cell:{cid}")
            continue
        handler = kernel.lookup(cell)
        if handler is None:
            failure = {
                "failed_cell": f"cell:{cid}",
                "error_type": "UnregisteredSource",
                "message": "cell source has no registered kernel operation; the reference executor never executes unregistered code",
            }
            break
        try:
            outputs = handler()
        except CellExecutionError as e:
            failure = {"failed_cell": f"cell:{cid}", "error_type": type(e).__name__, "message": str(e)}
            break
        except Exception as e:
            failure = {"failed_cell": f"cell:{cid}", "error_type": type(e).__name__, "message": str(e)}
            break
        for entry in produces:
            name = entry.get("name")
            if name not in outputs:
                failure = {
                    "failed_cell": f"cell:{cid}",
                    "error_type": "MissingDeclaredOutput",
                    "message": f"kernel operation did not produce declared output {name!r}",
                }
                break
            data = outputs[name]
            digest = hashlib.sha256(data).hexdigest()
            objects[digest] = data
            bindings.append(
                {
                    "named_output": f"cell:{cid}#{name}",
                    "object_ref": f"object:sha256:{digest}",
                    "mime_type": entry.get("mime_type", "application/octet-stream"),
                }
            )
        if failure:
            break
        executed.append(f"cell:{cid}")

    run_id, failure_id, commit_id = _next_ids(art)
    prefix = len(executed) > 0
    if failure is None:
        status = "success"
    elif prefix:
        status = "partial_success"
    else:
        status = "failure"
        bindings = []  # no partial outputs commit (section 31/32)

    source_commit = f"commit:{manifest.get('current_commit')}"
    run = {
        "run_id": run_id,
        "source_commit": source_commit,
        "result_commit": f"commit:{commit_id}",
        "actor_id": run_actor,
        "task_ref": "record:task_001" if "task_001" in art.records else None,
        "entry_point": executed[0] if executed else (f"cell:{order[0]}" if order else None),
        "status": status,
        "cells_executed": executed,
        "environment_id": manifest.get("environment", {}).get("environment_id", ""),
        "started_at": DEMO_STARTED_AT,
        "completed_at": DEMO_COMPLETED_AT,
        "output_bindings": bindings,
    }
    if run.get("task_ref") is None:
        run.pop("task_ref")
    if run.get("entry_point") is None:
        run.pop("entry_point")

    changes: list[dict[str, Any]] = []
    if failure is not None:
        failure_record = {
            "record_id": failure_id,
            "record_type": "sol:record/failure",
            "run_id": f"run:{run_id}",
            "source_commit": source_commit,
            "actor_id": run_actor,
            "failed_cell": failure["failed_cell"],
            "error_type": failure["error_type"],
            "message": failure["message"],
            "environment_id": manifest.get("environment", {}).get("environment_id", ""),
            "summary": f"Execution failed at {failure['failed_cell']}; see failure details.",
            "created_at": DEMO_COMPLETED_AT,
            "retryable": True,
            "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
        }
        changes.append({"op": "add_record", "record_id": failure_id})
    else:
        failure_record = None
    for b in bindings:
        changes.append({"op": "bind_output", "named_output": b["named_output"], "object_id": b["object_ref"]})

    commit = {
        "commit_id": commit_id,
        "parents": [source_commit],
        "branch": "main",
        "author": commit_author,
        "message": f"Executor run {run_id} ({status})",
        "changes": changes,
        "created_at": DEMO_COMMIT_AT,
    }

    # Write committed state.
    def dump(p: Path, obj: Any):
        p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")

    for digest, data in objects.items():
        (out_path / "objects" / "sha256" / digest).write_bytes(data)
    dump(out_path / "runs" / f"{run_id}.json", run)
    if failure_record is not None:
        dump(out_path / "records" / f"{failure_id}.json", failure_record)
    dump(out_path / "commits" / f"{commit_id}.json", commit)
    manifest["current_commit"] = commit_id
    dump(out_path / "manifest.json", manifest)

    # Regenerate the machine summary (Appendix C shared function).
    from .validate import generate_machine_summary

    art2 = Artifact.load(out_path)
    dump(out_path / "renders" / "machine_summary.json", generate_machine_summary(art2))

    from .validate import validate_path

    diags = [d.rule_id for d in validate_path(out_path)]
    return ExecutionResult(
        run_id=run_id,
        status=status,
        cells_executed=executed,
        output_bindings=bindings,
        failure_record=failure_record,
        commit_id=commit_id,
        artifact_path=out_path,
        diagnostics=diags,
    )
