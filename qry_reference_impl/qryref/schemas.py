from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .diagnostics import Diagnostic, diag

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def validate_json_schema(instance: dict, schema_name: str, target: str) -> list[Diagnostic]:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    out: list[Diagnostic] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        path = "/" + "/".join(str(p) for p in err.path) if err.path else "/"
        out.append(diag("QRY-SCHEMA-001", "schema", f"{target}{path}", err.message))
    return out
