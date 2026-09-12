from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math

@dataclass(frozen=True)
class Field:
    name: str
    type: str = "unknown"
    nullable: bool = True

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "nullable": self.nullable}

@dataclass(frozen=True)
class RowBound:
    min: int = 0
    max: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {"min": self.min, "max": self.max}

@dataclass(frozen=True)
class Bound:
    rows: RowBound
    fields: tuple[Field, ...]
    order: tuple[str, ...] = ()
    unique_keys: tuple[tuple[str, ...], ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "rows": self.rows.to_json(),
            "fields": [f.to_json() for f in self.fields],
            "order": list(self.order),
            "unique_keys": [list(k) for k in self.unique_keys],
        }

    @staticmethod
    def from_json(obj: dict[str, Any]) -> Bound:
        rows = obj.get("rows", {})
        fields = tuple(Field(**f) for f in obj.get("fields", []))
        order = tuple(obj.get("order", []))
        unique_keys = tuple(tuple(k) for k in obj.get("unique_keys", []))
        return Bound(RowBound(rows.get("min", 0), rows.get("max")), fields, order, unique_keys)


def max_add(values: list[int | None]) -> int | None:
    if any(v is None for v in values):
        return None
    return sum(v for v in values if v is not None)


def max_mul(a: int | None, b: int | None) -> int | None:
    if a is None or b is None:
        return None
    return a * b


def max_min(a: int | None, b: int | None) -> int | None:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def apply_selectivity(bound: Bound, min_sel: float, max_sel: float) -> Bound:
    row_min = math.floor(bound.rows.min * min_sel)
    row_max = None if bound.rows.max is None else math.ceil(bound.rows.max * max_sel)
    return Bound(RowBound(row_min, row_max), bound.fields, (), bound.unique_keys)


def field_map(bound: Bound) -> dict[str, Field]:
    return {f.name: f for f in bound.fields}


def schema_compatible(a: Bound, b: Bound) -> bool:
    if len(a.fields) != len(b.fields):
        return False
    for fa, fb in zip(a.fields, b.fields):
        if fa.name != fb.name or fa.type != fb.type:
            return False
    return True
