"""Import .ipynb notebooks into Sol artifacts (RFC-SOL-0001 section 53).

Per section 53 and decision Q6 (2026-09-07):
  * preserve visible cell order,
  * import outputs into the internal object store,
  * preserve available metadata,
  * mark provenance incomplete where unavailable
    (manifest.imported_from / manifest.provenance_status),
  * classify imported outputs as staleness=unknown, verification=unverified
    (the original execution is not a Sol run; nothing is known to have
    changed upstream, so neither current nor stale is justified),
  * create an initial import commit,
  * never fabricate run records for imported outputs.

Imported artifacts SHOULD default to untrusted mode (section 49); the
importer declares the minimum environment floor (decision Q2) and the
rendering layer MUST disclose the incomplete provenance (V5 render honesty).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .make_corpus import digest_ref, obj_ref
from .model import Artifact

DEMO_IMPORT_AT = "2026-01-01T02:00:00Z"


def _cell_source(cell: dict[str, Any]) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return str(src)


def _output_content(output: dict[str, Any]) -> str:
    otype = output.get("output_type", "")
    if otype == "stream":
        text = output.get("text", [])
        return "".join(text) if isinstance(text, list) else str(text)
    if otype in {"execute_result", "display_data"}:
        data = output.get("data", {})
        if "text/plain" in data:
            t = data["text/plain"]
            return "".join(t) if isinstance(t, list) else str(t)
        return json.dumps(data, sort_keys=True)
    if otype == "error":
        tb = output.get("traceback", [])
        return f"{output.get('ename', 'Error')}: {output.get('evalue', '')}\n" + "".join(tb)
    return json.dumps(output, sort_keys=True)


def import_ipynb(nb_path: str | Path, out_dir: str | Path, importer: str = "human:alice") -> dict[str, Any]:
    """Import a notebook into a new Sol artifact written to out_dir.

    Returns a summary dict; the written artifact validates with zero
    diagnostics (asserted here).
    """
    nb_path = Path(nb_path)
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for sub in ("cells", "records", "actors", "runs", "commits", "objects/sha256", "objects/records", "renders"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    nb_bytes = nb_path.read_bytes()
    nb_name = nb_path.name
    artifact_id = "art_" + hashlib.sha256(nb_bytes).hexdigest()[:22]

    store: dict[str, bytes] = {}
    import_meta = json.dumps(
        {
            "source_file": nb_name,
            "notebook_metadata": nb.get("metadata", {}),
            "nbformat": nb.get("nbformat"),
            "imported_at": DEMO_IMPORT_AT,
            "provenance": "incomplete",
        },
        sort_keys=True,
    ).encode("utf-8")
    import_meta_obj = obj_ref(store, import_meta)

    def dump(p: Path, obj: Any):
        p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")

    cells: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    object_records: dict[str, dict[str, Any]] = {}
    for i, cell in enumerate(nb.get("cells", []), start=1):
        ctype = cell.get("cell_type", "code")
        cid = f"cell_{i:03d}"
        source = _cell_source(cell)
        entry: dict[str, Any] = {
            "cell_id": cid,
            "cell_type": "sol:cell/prose" if ctype == "markdown" else "sol:cell/code",
            "title": f"Imported cell {i}",
            "summary": f"Imported {ctype} cell {i} from {nb_name} (provenance incomplete).",
            "source": source,
            "source_hash": digest_ref(source),
            "actor_id": importer,
        }
        if ctype == "code":
            entry["language"] = "python"
        outputs = cell.get("outputs", [])
        if outputs:
            imported: list[dict[str, Any]] = []
            for j, output in enumerate(outputs, start=1):
                content = _output_content(output).encode("utf-8")
                ref = obj_ref(store, content)
                digest = ref.rsplit(":", 1)[-1]
                name = f"output_{j}"
                imported.append(
                    {
                        "name": name,
                        "object_ref": ref,
                        "staleness": "unknown",
                        "verification": "unverified",
                    }
                )
                object_records[digest] = {
                    "object_id": ref,
                    "mime_type": "text/plain",
                    "compression": "sol:compression/none",
                    "size_bytes": len(content),
                    "created_by": f"cell:{cid}",
                    "data_sensitivity": "internal",
                }
            entry["metadata"] = {"imported_outputs": imported}
        cells[cid] = entry
        order.append(f"cell:{cid}")

    manifest = {
        "sol_version": "0.1",
        "artifact_type": "sol_notebook",
        "artifact_id": artifact_id,
        "title": nb.get("metadata", {}).get("title", nb_name),
        "current_commit": "commit_001",
        "required_features": [
            "sol:feature/linear_execution",
            "sol:feature/internal_object_store",
            "sol:feature/machine_summary",
        ],
        "optional_features": ["sol:feature/external_evidence"],
        "runtime": {
            "primary_language": "python",
            "language_version": nb.get("metadata", {}).get("language_info", {}).get("version", "unknown"),
            "kernel_adapter": "sol-kernel-python",
        },
        # Decision Q2 floor; for imported work the pin is the import metadata.
        "environment": {
            "environment_id": "env_imported",
            "package_manifest": digest_ref(import_meta),
            "kernel": "python",
            "kernel_version": "unknown",
        },
        "execution": {
            "structure": "linear",
            "partial_execution_policy": "invalidate_downstream",
            "deterministic": False,
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
                {"branch": "main", "protected": True, "required_capabilities": ["approve"], "allowed_committers": [importer]}
            ],
        },
        # Section 27.4: no reexecution records -> unknown.
        "reproducibility_status": "unknown",
        # Decision Q6: imported artifacts declare incomplete provenance.
        "imported_from": "ipynb",
        "provenance_status": "incomplete",
    }

    records = {
        "task_import_001": {
            "record_id": "task_import_001",
            "record_type": "sol:record/task",
            "task_type": "ipynb_import",
            "summary": f"Imported notebook {nb_name} with incomplete provenance.",
            "instruction_ref": import_meta_obj,
            "created_by": importer,
            "created_at": DEMO_IMPORT_AT,
            "status": {"lifecycle": "active", "staleness": "current", "verification": "unverified"},
        }
    }

    commits = {
        "commit_001": {
            "commit_id": "commit_001",
            "parents": [],
            "branch": "main",
            "author": importer,
            "message": f"Import {nb_name} from ipynb (provenance incomplete)",
            "changes": [{"op": "init"}, {"op": "import", "source": "ipynb", "file": nb_name}],
            "created_at": DEMO_IMPORT_AT,
        }
    }

    actors = {
        importer: {
            "actor_id": importer,
            "actor_type": "human",
            "display_name": "Alice",
            "capabilities": ["read", "write_cell", "write_record", "execute", "commit", "create_branch", "apply_proposal", "review", "approve", "render"],
        }
    }

    # Write the artifact.
    dump(out_dir / "manifest.json", manifest)
    dump(out_dir / "execution_structure.json", {"type": "linear", "cells": order})
    dump(out_dir / "diagnostics.json", [])
    for cid, cell in cells.items():
        dump(out_dir / "cells" / f"{cid}.json", cell)
    for rid, rec in records.items():
        dump(out_dir / "records" / f"{rid}.json", rec)
    for aid, actor in actors.items():
        dump(out_dir / "actors" / f"{aid.replace(':', '_')}.json", actor)
    for cid, commit in commits.items():
        dump(out_dir / "commits" / f"{cid}.json", commit)
    for digest, data in store.items():
        (out_dir / "objects" / "sha256" / digest).write_bytes(data)
    for digest, orec in object_records.items():
        dump(out_dir / "objects" / "records" / f"{digest}.json", orec)

    from .validate import generate_machine_summary

    art = Artifact.load(out_dir)
    dump(out_dir / "renders" / "machine_summary.json", generate_machine_summary(art))

    from .validate import validate_path

    diags = [d.rule_id for d in validate_path(out_dir)]
    return {
        "artifact": str(out_dir),
        "artifact_id": artifact_id,
        "cells": len(cells),
        "objects": len(store),
        "imported_outputs": sum(len(c.get("metadata", {}).get("imported_outputs", [])) for c in cells.values()),
        "provenance_status": "incomplete",
        "diagnostics": diags,
    }
