from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_json_dir(path: Path, id_field: str | None = None) -> dict[str, Any]:
    items: dict[str, Any] = {}
    if not path.exists():
        return items
    for p in sorted(path.glob("*.json")):
        obj = _load_json_file(p)
        if id_field and isinstance(obj, dict) and id_field in obj:
            items[obj[id_field]] = obj
        else:
            items[p.stem] = obj
    return items


@dataclass
class Artifact:
    root: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    execution_structure: dict[str, Any] = field(default_factory=dict)
    cells: dict[str, dict[str, Any]] = field(default_factory=dict)
    records: dict[str, dict[str, Any]] = field(default_factory=dict)
    actors: dict[str, dict[str, Any]] = field(default_factory=dict)
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    commits: dict[str, dict[str, Any]] = field(default_factory=dict)
    renders: dict[str, dict[str, Any]] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    object_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, root: str | Path) -> Artifact:
        root = Path(root)
        art = cls(root=root)
        manifest_path = root / "manifest.json"
        if manifest_path.exists():
            art.manifest = _load_json_file(manifest_path)
        exec_path = root / "execution_structure.json"
        if exec_path.exists():
            art.execution_structure = _load_json_file(exec_path)
        art.cells = _load_json_dir(root / "cells", "cell_id")
        art.records = _load_json_dir(root / "records", "record_id")
        art.actors = _load_json_dir(root / "actors", "actor_id")
        art.runs = _load_json_dir(root / "runs", "run_id")
        art.commits = _load_json_dir(root / "commits", "commit_id")
        art.renders = _load_json_dir(root / "renders", "render_id")
        diag_path = root / "diagnostics.json"
        if diag_path.exists():
            loaded = _load_json_file(diag_path)
            art.diagnostics = loaded if isinstance(loaded, list) else []
        orec_dir = root / "objects" / "records"
        if orec_dir.exists():
            for p in sorted(orec_dir.glob("*.json")):
                obj = _load_json_file(p)
                if isinstance(obj, dict) and isinstance(obj.get("object_id"), str):
                    digest = obj["object_id"].rsplit(":", 1)[-1]
                    art.object_records[digest] = obj
        exp_path = root / "expected_diagnostics.json"
        if exp_path.exists():
            art.expected = _load_json_file(exp_path)
        return art

    def object_path(self, digest: str) -> Path:
        # Support both flat and two-level sha256 object layouts.
        flat = self.root / "objects" / "sha256" / digest
        if flat.exists():
            return flat
        nested = self.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest
        return nested

    def all_records_of_type(self, suffix: str) -> list[dict[str, Any]]:
        return [r for r in self.records.values() if r.get("record_type") == f"sol:record/{suffix}"]

    def record(self, ref_or_id: str) -> dict[str, Any] | None:
        rid = ref_or_id.split(":", 1)[1] if ref_or_id.startswith("record:") else ref_or_id
        return self.records.get(rid)

    def cell(self, ref_or_id: str) -> dict[str, Any] | None:
        cid = ref_or_id.split(":", 1)[1] if ref_or_id.startswith("cell:") else ref_or_id
        if "#" in cid:
            cid = cid.split("#", 1)[0]
        return self.cells.get(cid)

