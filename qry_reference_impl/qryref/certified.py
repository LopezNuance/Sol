"""Certified answer-bound algebra for SOL-QRY v0.3.0.

Implements the certified lower/upper relation model of spec section 13:
a certified bounded result is (L, U) with L ⊆ R ⊆ U, the invariant
L ⊆ U MUST hold (13.1), canonical guarantee kinds (13.2), assurance
records separate from guarantee (13.3), explicit unavailable sides
(13.5), componentwise transfer for positive monotone operators (13.7),
structural one-sided containment (13.7.1), difference (13.8),
complement (13.9), recursion (13.10), aggregate bound rules
(13.11-13.14), mixed-guarantee composition (13.16), partial-bound
availability (13.17), validity versus tightness (13.18), and
guarantee validation (13.19). Bound provenance follows sections
12.5-12.9: lower-membership modes, upper-bound derivation fields, and
upper-only non-exclusion.

The v0.1 row-count bound path (bounds.py) is untouched; this module is
the v0.3 certified path, selected by schema_version "qry.query.v0.3".
Sources may declare:
  * "tuples"  -> exact instance (L = U = tuples)
  * "lower"/"upper" -> certified bounded instance
  * neither   -> no certified side (guarantee heuristic)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .bounds import Field
from .diagnostics import Diagnostic, diag
from .disclosure import disclosure_diagnostics
from .evaluators import contract_of
from .v3_semantic import claim_semantic_diagnostics
from .engine import QRYValidationError
from .rules import AGGREGATE_RULES, BOUND_RULES

# ---------------------------------------------------------------------------
# Vocabulary (spec 13.2, 13.3, 12.4)

GUARANTEE_KINDS = ("exact", "lower_bound", "upper_bound", "bounded", "heuristic")
ASSURANCE_STATUSES = ("proven", "validated", "contract_asserted", "tested", "unaudited", "unknown")
EVIDENCE_KINDS = (
    "mechanized_proof",
    "checked_certificate",
    "formal_derivation",
    "exhaustive_finite_check",
    "property_test",
    "adversarial_corpus",
    "contract_assertion",
)
LOWER_MODES = ("none", "tuple", "why", "how", "full_graph")
POSITIVE_MODES = ("why", "how", "full_graph")

_STATUS_RANK = {
    "proven": 0,
    "validated": 1,
    "contract_asserted": 2,
    "tested": 3,
    "unaudited": 4,
    "unknown": 5,
}

RULE_RELATION = "sol:bound/relation/v1"
RULE_SELECT = "sol:bound/select/v1"
RULE_PROJECT = "sol:bound/project/v1"
RULE_RENAME = "sol:bound/rename/v1"
RULE_ORDER = "sol:bound/order/v1"
RULE_LIMIT = "sol:bound/limit/v1"
RULE_DISTINCT = "sol:bound/distinct/v1"
RULE_UNION = "sol:bound/union/v1"
RULE_INTERSECT = "sol:bound/intersect/v1"
RULE_JOIN = "sol:bound/join/v1"
RULE_DIFFERENCE = "sol:bound/difference/v1"
RULE_ANNOTATE = "sol:bound/annotate/v1"
RULE_STRUCTURAL = "sol:bound/structural_containment/v1"
RULE_LFP = "sol:bound/least_fixpoint/v1"
RULE_TEMPORAL = "sol:bound/temporal_slice/v1"
RULE_POLICY_BOUNDARY = "sol:bound/policy_boundary/v1"
RULE_COUNT_SET = "sol:bound/count_set/v1"
RULE_SUM = "sol:bound/sum/v1"
RULE_MIN_MAX = "sol:bound/min_max/v1"
RULE_AVG = "sol:bound/avg_optional_prefix/v1"


def _tuple_key(t: tuple) -> str:
    return json.dumps(list(t), sort_keys=True)


# ---------------------------------------------------------------------------
# Relation objects

@dataclass(frozen=True)
class Relation:
    """A finite relation: schema + tuple set (concrete certified side)."""

    fields: tuple[Field, ...]
    tuples: frozenset[tuple]

    def to_json(self) -> dict[str, Any]:
        return {
            "fields": [f.to_json() for f in self.fields],
            "tuples": [list(t) for t in sorted(self.tuples, key=_tuple_key)],
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Relation:
        fields = tuple(Field(**f) for f in obj.get("fields", []))
        tuples = frozenset(tuple(t) for t in obj.get("tuples", []))
        return cls(fields, tuples)

    def canonical(self) -> str:
        obj = {
            "fields": [f.to_json() for f in self.fields],
            "tuples": [list(t) for t in sorted(self.tuples, key=_tuple_key)],
        }
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        """Content-addressed object reference (Q4 decision)."""
        return "object:sha256:" + hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    def field_index(self, name: str) -> int | None:
        for i, f in enumerate(self.fields):
            if f.name == name:
                return i
        return None

    def select(self, terms: list[dict[str, Any]]) -> Relation:
        if not terms:
            return self
        idx = {t["field"]: self.field_index(t["field"]) for t in terms}
        if any(i is None for i in idx.values()):
            raise KeyError(next(t["field"] for t in terms if idx[t["field"]] is None))

        def ok(t: tuple) -> bool:
            for term in terms:
                v = t[idx[term["field"]]]
                op = term["op"]
                if v is None:
                    return False
                if op == "eq":
                    r = v == term["value"]
                elif op == "ne":
                    r = v != term["value"]
                elif op == "lt":
                    r = v < term["value"]
                elif op == "lte":
                    r = v <= term["value"]
                elif op == "gt":
                    r = v > term["value"]
                elif op == "gte":
                    r = v >= term["value"]
                else:
                    raise ValueError(f"unknown predicate op {op!r}")
                if not r:
                    return False
            return True

        return Relation(self.fields, frozenset(t for t in self.tuples if ok(t)))

    def project(self, specs: list[dict[str, Any]]) -> Relation:
        out_fields: list[Field] = []
        src_idx: list[int | None] = []
        literals: list[Any] = []
        for s in specs:
            expr = s.get("expr")
            name = s.get("name") or expr
            if s.get("literal"):
                out_fields.append(Field(name, s.get("type", "unknown"), s.get("nullable", False)))
                src_idx.append(None)
                literals.append(s.get("value"))
            else:
                i = self.field_index(expr)
                if i is None:
                    raise KeyError(expr)
                base = self.fields[i]
                out_fields.append(Field(name, s.get("type", base.type), s.get("nullable", base.nullable)))
                src_idx.append(i)
                literals.append(None)

        def proj(t: tuple) -> tuple:
            return tuple(lit if si is None else t[si] for si, lit in zip(src_idx, literals))

        return Relation(tuple(out_fields), frozenset(proj(t) for t in self.tuples))

    def rename(self, mapping: dict[str, str]) -> Relation:
        fields = tuple(Field(mapping.get(f.name, f.name), f.type, f.nullable) for f in self.fields)
        return Relation(fields, self.tuples)

    def distinct(self, key_names: list[str]) -> Relation:
        idx = []
        for k in key_names:
            i = self.field_index(k)
            if i is None:
                raise KeyError(k)
            idx.append(i)
        best: dict[tuple, tuple] = {}
        for t in self.tuples:
            k = tuple(t[i] for i in idx)
            if k not in best or _tuple_key(t) < _tuple_key(best[k]):
                best[k] = t
        return Relation(self.fields, frozenset(best.values()))

    @staticmethod
    def union(rels: list[Relation]) -> Relation:
        fields = rels[0].fields
        return Relation(fields, frozenset().union(*[r.tuples for r in rels]))

    @staticmethod
    def intersect(rels: list[Relation]) -> Relation:
        fields = rels[0].fields
        out = rels[0].tuples
        for r in rels[1:]:
            out = out & r.tuples
        return Relation(fields, out)

    def difference(self, other: Relation) -> Relation:
        return Relation(self.fields, self.tuples - other.tuples)

    def join(self, other: Relation, on: list[dict[str, str]]) -> Relation:
        li = [self.field_index(c["left"]) for c in on]
        ri = [other.field_index(c["right"]) for c in on]
        if any(i is None for i in li + ri):
            raise KeyError("join condition field missing")
        fields = self.fields + other.fields
        out = set()
        for lt in self.tuples:
            for rt in other.tuples:
                if all(lt[a] == rt[b] for a, b in zip(li, ri)):
                    out.add(lt + rt)
        return Relation(fields, frozenset(out))

    def annotate(self, columns: list[dict[str, Any]]) -> Relation:
        new_fields: list[Field] = []
        vals: list[Any] = []
        for c in columns:
            name = c["name"]
            if c.get("literal") is not None and "expr" not in c:
                new_fields.append(Field(name, c.get("type", "unknown"), c.get("nullable", False)))
                vals.append(c["literal"])
            else:
                i = self.field_index(c["expr"])
                if i is None:
                    raise KeyError(c["expr"])
                base = self.fields[i]
                new_fields.append(Field(name, c.get("type", base.type), c.get("nullable", base.nullable)))
                vals.append(i)

        def ann(t: tuple) -> tuple:
            extra = []
            for v in vals:
                extra.append(t[v] if isinstance(v, int) else v)
            return t + tuple(extra)

        return Relation(self.fields + tuple(new_fields), frozenset(ann(t) for t in self.tuples))

    def limit(self, n: int, order_fields: tuple[str, ...]) -> Relation:
        idx = [self.field_index(f) for f in order_fields]
        if any(i is None for i in idx):
            raise KeyError("order field missing")

        def sort_key(t: tuple):
            return tuple(_tuple_key((t[i],)) for i in idx)

        return Relation(self.fields, frozenset(sorted(self.tuples, key=sort_key)[:n]))


# ---------------------------------------------------------------------------
# Assurance, provenance, certified bound

@dataclass(frozen=True)
class Assurance:
    status: str
    evidence: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    stale: bool = False

    def effective_status(self) -> str:
        """Stale dependencies evaluate effectively as unknown (13.3)."""
        return "unknown" if self.stale else self.status

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "evidence": list(self.evidence),
            "depends_on": list(self.depends_on),
            "stale": self.stale,
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Assurance:
        return cls(
            status=obj.get("status", "unknown"),
            evidence=tuple(obj.get("evidence", [])),
            depends_on=tuple(obj.get("depends_on", [])),
            stale=bool(obj.get("stale", False)),
        )


@dataclass(frozen=True)
class UpperDerivation:
    """Upper-bound derivation provenance (12.6)."""

    rule_id: str | None = None
    input_relations: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    evaluators: tuple[str, ...] = ()
    rewrites: tuple[str, ...] = ()
    view_substitutions: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "input_relations": list(self.input_relations),
            "sources": list(self.sources),
            "evaluators": list(self.evaluators),
            "rewrites": list(self.rewrites),
            "view_substitutions": list(self.view_substitutions),
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any] | None) -> UpperDerivation | None:
        if obj is None:
            return None
        return cls(
            rule_id=obj.get("rule_id"),
            input_relations=tuple(obj.get("input_relations", [])),
            sources=tuple(obj.get("sources", [])),
            evaluators=tuple(obj.get("evaluators", [])),
            rewrites=tuple(obj.get("rewrites", [])),
            view_substitutions=tuple(obj.get("view_substitutions", [])),
        )


@dataclass(frozen=True)
class LowerMembership:
    """Per-tuple lower-membership provenance entry (12.5)."""

    tuple_: tuple
    mode: str
    cites: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {"tuple": list(self.tuple_), "mode": self.mode, "cites": list(self.cites)}

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> LowerMembership:
        return cls(tuple(obj["tuple"]), obj.get("mode", "tuple"), tuple(obj.get("cites", [])))


@dataclass(frozen=True)
class Provenance:
    lower_membership_mode: str = "tuple"
    lower_memberships: tuple[LowerMembership, ...] = ()
    upper_derivation: UpperDerivation | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "lower_membership_mode": self.lower_membership_mode,
            "lower_memberships": [lm.to_json() for lm in self.lower_memberships],
            "upper_derivation": self.upper_derivation.to_json() if self.upper_derivation is not None else None,
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Provenance:
        return cls(
            lower_membership_mode=obj.get("lower_membership_mode", "tuple"),
            lower_memberships=tuple(LowerMembership.from_json(x) for x in obj.get("lower_memberships", [])),
            upper_derivation=UpperDerivation.from_json(obj.get("upper_derivation")),
        )


@dataclass(frozen=True)
class CertifiedBound:
    """A certified bounded result (L, U) with guarantee, assurance, provenance.

    For aggregate nodes the L/U relations carry the certified/enclosed
    group keys; the per-group certified numeric intervals (13.11-13.14)
    are carried separately in `intervals`, since the aggregate result is
    a certified numeric interval rather than a set of answer tuples.
    """

    guarantee: str
    lower: Relation | None
    upper: Relation | None
    assurance: Assurance
    provenance: Provenance
    may_be_empty_groups: tuple[tuple, ...] = ()
    bound_rule: str | None = None
    order: tuple[str, ...] = ()
    intervals: tuple[dict[str, Any], ...] = ()

    def to_json(self) -> dict[str, Any]:
        exact = self.guarantee == "exact" and self.lower is not None
        return {
            "guarantee": self.guarantee,
            "lower": self.lower.to_json() if self.lower is not None else None,
            "upper": self.upper.to_json() if self.upper is not None else None,
            "lower_object": self.lower.digest() if self.lower is not None else None,
            "upper_object": self.upper.digest() if self.upper is not None else None,
            "result_object": self.lower.digest() if exact else None,
            "assurance": self.assurance.to_json(),
            "provenance": self.provenance.to_json(),
            "may_be_empty_groups": [list(g) for g in self.may_be_empty_groups],
            "bound_rule": self.bound_rule,
            "order": list(self.order),
            "intervals": [dict(iv) for iv in self.intervals],
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> CertifiedBound:
        return cls(
            guarantee=obj["guarantee"],
            lower=Relation.from_json(obj["lower"]) if obj.get("lower") is not None else None,
            upper=Relation.from_json(obj["upper"]) if obj.get("upper") is not None else None,
            assurance=Assurance.from_json(obj.get("assurance", {})),
            provenance=Provenance.from_json(obj.get("provenance", {})),
            may_be_empty_groups=tuple(tuple(g) for g in obj.get("may_be_empty_groups", [])),
            bound_rule=obj.get("bound_rule"),
            order=tuple(obj.get("order", ())),
            intervals=tuple(dict(iv) for iv in obj.get("intervals", [])),
        )

    def core(self) -> dict[str, Any]:
        """The normatively pinned part of a bound record (golden matching)."""
        return {
            "guarantee": self.guarantee,
            "lower": self.lower.to_json() if self.lower is not None else None,
            "upper": self.upper.to_json() if self.upper is not None else None,
            "may_be_empty_groups": sorted((list(g) for g in self.may_be_empty_groups), key=_tuple_key),
            "bound_rule": self.bound_rule,
            "intervals": sorted(
                (json.dumps(dict(iv), sort_keys=True) for iv in self.intervals),
            ),
        }


# ---------------------------------------------------------------------------
# Transfer helpers

def _guarantee(lb: Relation | None, ub: Relation | None) -> str:
    if lb is None and ub is None:
        return "heuristic"
    if lb is not None and ub is not None:
        if lb.tuples == ub.tuples and [f.to_json() for f in lb.fields] == [f.to_json() for f in ub.fields]:
            return "exact"
        return "bounded"
    return "lower_bound" if lb is not None else "upper_bound"


def _compose_assurance(inps: list[CertifiedBound], rule_id: str | None) -> Assurance:
    deps: list[str] = []
    ev: list[str] = []
    stale = False
    worst = 0
    for b in inps:
        a = b.assurance
        worst = max(worst, _STATUS_RANK.get(a.status, 5))
        deps.extend(a.depends_on)
        ev.extend(a.evidence)
        stale = stale or a.stale
    if rule_id:
        deps.append(rule_id)
    status = next((k for k, v in _STATUS_RANK.items() if v == worst), "unknown")
    return Assurance(status, tuple(sorted(set(ev))), tuple(sorted(set(deps))), stale)


def _compose_provenance(
    inps: list[CertifiedBound],
    rule_id: str | None,
    lb: Relation | None,
    ub: Relation | None,
    evaluators: tuple[str, ...] = (),
) -> Provenance:
    srcs: set[str] = set()
    in_rel: list[str] = []
    for b in inps:
        ud = b.provenance.upper_derivation
        if ud is not None:
            srcs.update(ud.sources)
        if b.lower is not None:
            in_rel.append(b.lower.digest())
        if b.upper is not None:
            in_rel.append(b.upper.digest())
    ud = None
    if ub is not None and rule_id:
        ud = UpperDerivation(rule_id, tuple(sorted(set(in_rel))), tuple(sorted(srcs)), tuple(evaluators))
    lms = tuple(LowerMembership(t, "tuple", ()) for t in (lb.tuples if lb is not None else ()))
    return Provenance("tuple", lms, ud)


# ---------------------------------------------------------------------------
# Aggregate bound rules (13.11-13.14)

def _frac_str(f: Fraction) -> str:
    return f"{f.numerator}/{f.denominator}"


def avg_optional_prefix(Lg: list[tuple], Ug: list[tuple], fi: int) -> tuple[Fraction, Fraction, bool] | None:
    """sol:bound/avg_optional_prefix/v1 over one group (13.14).

    Returns (AVG_min, AVG_max, may_be_empty) or None when the rule does
    not apply (empty exact relation -> AVG undefined).
    """
    n_L = len(Lg)
    s_L = sum(t[fi] for t in Lg)
    O = set(Ug) - set(Lg)
    vals = sorted(t[fi] for t in O)
    m = len(vals)
    if n_L == 0 and m == 0:
        return None
    asc = vals
    desc = list(reversed(vals))
    ks = range(0, m + 1) if n_L > 0 else range(1, m + 1)
    best_min: Fraction | None = None
    best_max: Fraction | None = None
    for k in ks:
        cand_min = Fraction(s_L + sum(asc[:k])) / (n_L + k)
        cand_max = Fraction(s_L + sum(desc[:k])) / (n_L + k)
        if best_min is None or cand_min < best_min:
            best_min = cand_min
        if best_max is None or cand_max > best_max:
            best_max = cand_max
    return best_min, best_max, n_L == 0


def _aggregate_rule(aggs: list[dict[str, Any]]) -> str:
    funcs = {a.get("func") for a in aggs}
    if "avg" in funcs:
        return RULE_AVG
    if "sum" in funcs:
        return RULE_SUM
    if "min" in funcs or "max" in funcs:
        return RULE_MIN_MAX
    return RULE_COUNT_SET


def _interval_value(v: Any) -> Any:
    if isinstance(v, Fraction):
        return _frac_str(v)
    return v


def _aggregate_bounds(
    inp: CertifiedBound, node: dict[str, Any]
) -> tuple[Relation | None, Relation | None, list[dict[str, Any]], frozenset[tuple], list[Diagnostic]]:
    """Compute (L_groups, U_groups, intervals, may_be_empty_groups, diags).

    L/U relations carry the certified/enclosed group keys; each aggregate
    function contributes a certified numeric interval per group
    (13.11-13.14). A group appears in L_groups when L has at least one
    tuple with that key, in U_groups when U does.
    """
    diags: list[Diagnostic] = []
    group_by = list(node.get("group_by", []))
    aggs = list(node.get("aggregates", []))
    lb_in, ub_in = inp.lower, inp.upper
    if lb_in is None or ub_in is None:
        # Interval rules require both certified sides (13.17).
        return None, None, [], frozenset(), diags
    gidx = []
    for g in group_by:
        i = lb_in.field_index(g)
        if i is None:
            diags.append(diag("QRY-SEM-006", "missing_field", "node", f"Group key {g!r} not found"))
            return None, None, [], frozenset(), diags
        gidx.append(i)

    def group_map(rel: Relation) -> dict[tuple, list[tuple]]:
        m: dict[tuple, list[tuple]] = {}
        for t in rel.tuples:
            k = tuple(t[i] for i in gidx)
            m.setdefault(k, []).append(t)
        return m

    gl = group_map(lb_in)
    gu = group_map(ub_in)
    all_keys = sorted(set(gl) | set(gu), key=_tuple_key)
    group_fields = tuple(next(f for f in lb_in.fields if f.name == g) for g in group_by)
    L_groups: set[tuple] = set()
    U_groups: set[tuple] = set()
    intervals: list[dict[str, Any]] = []
    may_empty: set[tuple] = set()
    for k in all_keys:
        Lg = gl.get(k, [])
        Ug = gu.get(k, [])
        if Lg:
            L_groups.add(k)
        if Ug:
            U_groups.add(k)
        for a in aggs:
            func = a.get("func")
            name = a.get("name", func)
            if func == "count_set":
                intervals.append({
                    "field": name,
                    "group": list(k),
                    "lower": len(Lg),
                    "upper": len(Ug),
                    "may_be_empty": False,
                })
                continue
            fi = lb_in.field_index(a.get("field", ""))
            if fi is None:
                diags.append(diag("QRY-SEM-006", "missing_field", "node", f"Aggregate field {a.get('field')!r} not found"))
                continue
            vL = [t[fi] for t in Lg]
            vU = [t[fi] for t in Ug]
            if any(v is None for v in vL + vU):
                # Values must be exact and finite; conservative: no interval.
                continue
            if func == "sum":
                O = set(Ug) - set(Lg)
                sL = sum(vL)
                intervals.append({
                    "field": name,
                    "group": list(k),
                    "lower": _interval_value(sL + sum(t[fi] for t in O if t[fi] < 0)),
                    "upper": _interval_value(sL + sum(t[fi] for t in O if t[fi] > 0)),
                    "may_be_empty": False,
                })
            elif func in {"min", "max"}:
                if not Lg:
                    continue
                if func == "min":
                    lo, hi = min(vU), min(vL)
                else:
                    lo, hi = max(vL), max(vU)
                intervals.append({
                    "field": name,
                    "group": list(k),
                    "lower": _interval_value(lo),
                    "upper": _interval_value(hi),
                    "may_be_empty": False,
                })
            elif func == "avg":
                iv = avg_optional_prefix(Lg, Ug, fi)
                if iv is None:
                    continue
                amin, amax, may_empty_g = iv
                intervals.append({
                    "field": name,
                    "group": list(k),
                    "lower": _frac_str(amin),
                    "upper": _frac_str(amax),
                    "may_be_empty": may_empty_g,
                })
                if may_empty_g:
                    may_empty.add(k)
            else:
                diags.append(diag("QRY-SEM-013", "unknown_aggregate", "node", f"Unknown aggregate func {func!r}"))
    return (
        Relation(group_fields, frozenset(L_groups)),
        Relation(group_fields, frozenset(U_groups)),
        intervals,
        frozenset(may_empty),
        diags,
    )


def _lfp(S: Relation, E: Relation, on: dict[str, str]) -> Relation:
    """Positive least fixed point: R = S ∪ {y : ∃x ∈ R, E(x, y)} (13.10)."""
    li = E.field_index(on["left"])
    ri = E.field_index(on["right"])
    R = set(S.tuples)
    changed = True
    while changed:
        changed = False
        new = set()
        for e in E.tuples:
            if e[li] in {t[0] for t in R} and (e[ri],) not in R:
                new.add((e[ri],))
        if new:
            R |= new
            changed = True
    return Relation(S.fields, frozenset(R))


# ---------------------------------------------------------------------------
# Certified inference

def _src_fields(src: dict[str, Any]) -> tuple[Field, ...]:
    return tuple(Field(f["name"], f.get("type", "unknown"), f.get("nullable", True)) for f in src.get("schema", []))


def _node_inputs(n: dict[str, Any]) -> list[str]:
    op = n.get("op")
    if op in {"filter", "project", "rename", "limit", "sort", "distinct", "aggregate",
              "annotate", "evaluate", "temporal_slice"}:
        return [n.get("input")]
    if op == "join":
        return [n.get("left"), n.get("right")]
    if op in {"union_all", "union_distinct", "intersect", "difference"}:
        return list(n.get("inputs", []))
    if op == "least_fixpoint":
        return [n.get("seed"), n.get("edge")]
    return []


def infer_certified(query: dict[str, Any]) -> dict[str, CertifiedBound]:
    """Infer certified (L, U) bounds for every node of a v0.3 query."""
    nodes = {n["id"]: n for n in query.get("nodes", [])}
    root = query.get("root")
    if root not in nodes:
        raise QRYValidationError([diag("QRY-SEM-002", "missing_root", "query.root", f"Root node {root!r} not found")])
    diags: list[Diagnostic] = []
    memo: dict[str, CertifiedBound] = {}
    visiting: set[str] = set()

    def finish(rule: str | None, inps: list[CertifiedBound], lb: Relation | None, ub: Relation | None,
               order: tuple[str, ...] = (), evaluators: tuple[str, ...] = (),
               may_be_empty: frozenset[tuple] = frozenset(), bound_rule: str | None = None,
               intervals: tuple[dict[str, Any], ...] = ()) -> CertifiedBound:
        assurance = _compose_assurance(inps, rule)
        provenance = _compose_provenance(inps, rule, lb, ub, evaluators)
        return CertifiedBound(
            guarantee=_guarantee(lb, ub),
            lower=lb,
            upper=ub,
            assurance=assurance,
            provenance=provenance,
            may_be_empty_groups=tuple(sorted(may_be_empty, key=_tuple_key)),
            bound_rule=bound_rule if bound_rule is not None else rule,
            order=order,
            intervals=intervals,
        )

    def infer(nid: str) -> CertifiedBound:
        if nid in memo:
            return memo[nid]
        if nid not in nodes:
            raise QRYValidationError([diag("QRY-SEM-003", "missing_input", f"node:{nid}", "Node not found")])
        if nid in visiting:
            raise QRYValidationError([diag("QRY-SEM-004", "cycle", f"node:{nid}", "Cycle detected")])
        visiting.add(nid)
        n = nodes[nid]
        op = n.get("op")

        if op == "read":
            src_name = n.get("source")
            if src_name not in query.get("sources", {}):
                raise QRYValidationError([diag("QRY-SEM-005", "unknown_source", f"node:{nid}", f"Source {src_name!r} not declared")])
            src = query["sources"][src_name]
            fields = _src_fields(src)
            if "tuples" in src:
                rel = Relation(fields, frozenset(tuple(t) for t in src["tuples"]))
                lb = ub = rel
            elif "lower" in src or "upper" in src:
                lb = Relation(fields, frozenset(tuple(t) for t in src.get("lower", {}).get("tuples", []))) if "lower" in src else None
                ub = Relation(fields, frozenset(tuple(t) for t in src.get("upper", {}).get("tuples", []))) if "upper" in src else None
                if lb is not None and ub is not None and not (lb.tuples <= ub.tuples):
                    diags.append(diag("QV5-01", "inverted_bounds", f"source:{src_name}",
                                      "Source lower relation contains a tuple absent from the upper relation"))
            else:
                lb = ub = None
            guarantee = _guarantee(lb, ub)
            status = "contract_asserted" if (lb is not None or ub is not None) else "unaudited"
            cb = CertifiedBound(
                guarantee=guarantee,
                lower=lb,
                upper=ub,
                assurance=Assurance(status, (f"source:{src_name}",), (f"source:{src_name}",)),
                provenance=Provenance(
                    lower_membership_mode="tuple",
                    lower_memberships=tuple(LowerMembership(t, "tuple", (f"source:{src_name}",)) for t in (lb.tuples if lb is not None else ())),
                    upper_derivation=UpperDerivation(RULE_RELATION, (), (f"source:{src_name}",)) if ub is not None else None,
                ),
                bound_rule=RULE_RELATION if guarantee != "heuristic" else None,
            )

        elif op == "filter":
            inp = infer(n["input"])
            pred = n.get("predicate") or {}
            terms = pred.get("terms")
            mn = pred.get("min_selectivity", 0.0)
            mx = pred.get("max_selectivity", 1.0)
            if not (0 <= mn <= mx <= 1):
                diags.append(diag("QRY-SEM-008", "invalid_selectivity", f"node:{nid}", "Selectivity must satisfy 0 <= min <= max <= 1"))
            if terms:
                lb = inp.lower.select(terms) if inp.lower is not None else None
                ub = inp.upper.select(terms) if inp.upper is not None else None
                rule = RULE_SELECT
            else:
                # Predicate not concretely evaluable: structural containment (13.7.1).
                base = inp.lower if inp.lower is not None else inp.upper
                lb = Relation(base.fields, frozenset()) if base is not None else None
                ub = inp.upper
                rule = RULE_STRUCTURAL
            cb = finish(rule, [inp], lb, ub)

        elif op == "project":
            inp = infer(n["input"])
            specs = n.get("fields", [])
            ref = inp.lower if inp.lower is not None else inp.upper
            for s in specs:
                if not s.get("literal") and (ref is None or ref.field_index(s.get("expr")) is None):
                    diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Field {s.get('expr')!r} not found"))
            try:
                lb = inp.lower.project(specs) if inp.lower is not None else None
                ub = inp.upper.project(specs) if inp.upper is not None else None
            except KeyError as e:
                diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Field {e} not found"))
                lb = ub = None
            out_names = {s.get("name") or s.get("expr") for s in specs}
            order = tuple(o for o in inp.order if o in out_names)
            cb = finish(RULE_PROJECT, [inp], lb, ub, order=order)

        elif op == "rename":
            inp = infer(n["input"])
            mapping = n.get("mapping", {})
            lb = inp.lower.rename(mapping) if inp.lower is not None else None
            ub = inp.upper.rename(mapping) if inp.upper is not None else None
            order = tuple(mapping.get(o, o) for o in inp.order)
            cb = finish(RULE_RENAME, [inp], lb, ub, order=order)

        elif op == "sort":
            inp = infer(n["input"])
            ref = inp.lower if inp.lower is not None else inp.upper
            if ref is not None:
                for f in n.get("by", []):
                    if ref.field_index(f) is None:
                        diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Sort field {f!r} not found"))
            cb = finish(RULE_ORDER, [inp], inp.lower, inp.upper, order=tuple(n.get("by", [])))

        elif op == "limit":
            inp = infer(n["input"])
            lim = n.get("limit")
            if not isinstance(lim, int) or lim < 0:
                diags.append(diag("QRY-SEM-009", "invalid_limit", f"node:{nid}", "Limit must be a non-negative integer"))
            if inp.guarantee == "exact" and inp.order and inp.lower is not None:
                rel = inp.lower.limit(lim, inp.order)
                cb = finish(RULE_LIMIT, [inp], rel, rel)
            else:
                # 13.15: LIMIT over inexact input needs a position-certainty rule;
                # otherwise the result is labeled heuristic.
                cb = finish(None, [inp], None, None)

        elif op == "distinct":
            inp = infer(n["input"])
            ref = inp.lower if inp.lower is not None else inp.upper
            keys = n.get("keys") or ([f.name for f in ref.fields] if ref is not None else [])
            lb = inp.lower.distinct(keys) if inp.lower is not None else None
            ub = inp.upper.distinct(keys) if inp.upper is not None else None
            cb = finish(RULE_DISTINCT, [inp], lb, ub)

        elif op == "aggregate":
            inp = infer(n["input"])
            L_rel, U_rel, intervals, may_empty, adiags = _aggregate_bounds(inp, n)
            diags.extend(adiags)
            rule = _aggregate_rule(n.get("aggregates", []))
            cb = finish(rule, [inp], L_rel, U_rel, may_be_empty=may_empty, intervals=tuple(intervals))

        elif op == "join":
            left = infer(n["left"])
            right = infer(n["right"])
            jt = n.get("join_type", "inner")
            if jt != "inner":
                # Conservative baseline: non-inner joins leave sides unavailable.
                cb = finish(None, [left, right], None, None)
            else:
                on = n.get("on", [])
                try:
                    lb = left.lower.join(right.lower, on) if (left.lower is not None and right.lower is not None) else None
                    ub = left.upper.join(right.upper, on) if (left.upper is not None and right.upper is not None) else None
                except KeyError as e:
                    diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Join field {e} not found"))
                    lb = ub = None
                cb = finish(RULE_JOIN, [left, right], lb, ub)

        elif op in {"union_all", "union_distinct"}:
            inps = [infer(i) for i in n.get("inputs", [])]
            if not inps:
                raise QRYValidationError([diag("QRY-SEM-003", "missing_input", f"node:{nid}", "Union requires inputs")])
            lb_list = [b.lower for b in inps if b.lower is not None]
            ub_list = [b.upper for b in inps if b.upper is not None]
            lb = Relation.union(lb_list) if lb_list else None
            ub = Relation.union(ub_list) if len(ub_list) == len(inps) else None
            cb = finish(RULE_UNION, inps, lb, ub)

        elif op == "intersect":
            inps = [infer(i) for i in n.get("inputs", [])]
            if len(inps) != 2:
                raise QRYValidationError([diag("QRY-SEM-003", "missing_input", f"node:{nid}", "Intersect requires two inputs")])
            lb = Relation.intersect([b.lower for b in inps]) if all(b.lower is not None for b in inps) else None
            ub_list = [b.upper for b in inps if b.upper is not None]
            if len(ub_list) == 2:
                ub = Relation.intersect(ub_list)
            elif len(ub_list) == 1:
                ub = ub_list[0]
            else:
                ub = None
            cb = finish(RULE_INTERSECT, inps, lb, ub)

        elif op == "difference":
            inps = [infer(i) for i in n.get("inputs", [])]
            if len(inps) != 2:
                raise QRYValidationError([diag("QRY-SEM-003", "missing_input", f"node:{nid}", "Difference requires two inputs")])
            left, right = inps[0], inps[1]
            if left.lower is not None and right.upper is not None:
                lb = left.lower.difference(right.upper)
            else:
                # 13.8: no nontrivial lower from L1 alone; typed empty lower remains valid.
                ref = left.lower if left.lower is not None else left.upper
                lb = Relation(ref.fields, frozenset()) if ref is not None else None
            if left.upper is not None:
                ub = left.upper.difference(right.lower) if right.lower is not None else left.upper
            else:
                ub = None
            cb = finish(RULE_DIFFERENCE, inps, lb, ub)

        elif op == "evaluate":
            inp = infer(n["input"])
            mode = n.get("mode", "heuristic")
            ev = n.get("evaluator", "")
            ref = inp.lower if inp.lower is not None else inp.upper
            if mode == "sound_positive":
                pos = frozenset(tuple(t) for t in n.get("positives", []))
                lb = Relation(ref.fields, pos) if ref is not None else None
                if inp.upper is not None and lb is not None and not (lb.tuples <= inp.upper.tuples):
                    diags.append(diag("QV5-04", "positive_set_outside_upper", f"node:{nid}",
                                      "Certified positive set is not contained in the input upper relation"))
            else:
                lb = Relation(ref.fields, frozenset()) if ref is not None else None
            # 13.7.1/26.6: only a tuple-preserving evaluator may inherit
            # the input upper as a certified containment. A
            # tuple-generating evaluator certifies no upper; the typed
            # empty lower remains valid (no transfer rule licenses the
            # sides, so the bound rule is absent).
            contract = contract_of(ev)
            generates = bool(contract and contract.get("generates_tuples"))
            ub = inp.upper if not generates else None
            cb = finish(RULE_STRUCTURAL if not generates else None, [inp], lb, ub,
                        evaluators=(ev,) if ev else ())

        elif op == "annotate":
            inp = infer(n["input"])
            cols = n.get("columns", [])
            try:
                lb = inp.lower.annotate(cols) if inp.lower is not None else None
                ub = inp.upper.annotate(cols) if inp.upper is not None else None
            except KeyError as e:
                diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Annotate field {e} not found"))
                lb = ub = None
            cb = finish(RULE_ANNOTATE, [inp], lb, ub, order=inp.order)

        elif op == "least_fixpoint":
            seed = infer(n["seed"])
            edge = infer(n["edge"])
            on = n.get("on", {})
            try:
                lb = _lfp(seed.lower, edge.lower, on) if (seed.lower is not None and edge.lower is not None) else None
                ub = _lfp(seed.upper, edge.upper, on) if (seed.upper is not None and edge.upper is not None) else None
            except KeyError as e:
                diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Fixpoint field {e} not found"))
                lb = ub = None
            cb = finish(RULE_LFP, [seed, edge], lb, ub)

        elif op == "temporal_slice":
            inp = infer(n["input"])
            tfield = n.get("field")
            terms = []
            if n.get("from") is not None:
                terms.append({"field": tfield, "op": "gte", "value": n["from"]})
            if n.get("to") is not None:
                terms.append({"field": tfield, "op": "lte", "value": n["to"]})
            try:
                lb = inp.lower.select(terms) if inp.lower is not None else None
                ub = inp.upper.select(terms) if inp.upper is not None else None
            except KeyError as e:
                diags.append(diag("QRY-SEM-006", "missing_field", f"node:{nid}", f"Temporal field {e} not found"))
                lb = ub = None
            cb = finish(RULE_TEMPORAL, [inp], lb, ub, order=inp.order)

        elif op == "policy_boundary":
            # Identity transfer: the node marks a policy boundary in the plan
            # and does not change the relation (gate 16 consumes this marker).
            inp = infer(n["input"])
            cb = finish(RULE_POLICY_BOUNDARY, [inp], inp.lower, inp.upper, order=inp.order)

        else:
            raise QRYValidationError([diag("QRY-SEM-010", "unknown_operation", f"node:{nid}", f"Unknown op {op!r}")])

        visiting.remove(nid)
        memo[nid] = cb
        return cb

    infer(root)
    if diags:
        raise QRYValidationError(diags)
    return memo


# ---------------------------------------------------------------------------
# Claim validation (13.19 guarantee validation)

def validate_bound_record(
    query: dict[str, Any],
    claim: CertifiedBound,
    inference: dict[str, CertifiedBound] | None = None,
    record: dict[str, Any] | None = None,
) -> list[Diagnostic]:
    """Validate a claimed certified bound record against the spec invariants.

    ``record`` is the full bound record (32): its disclosure
    declarations (cardinality disclosure, error behavior,
    non-inference claim) are checked against the query's declared
    leakage policy alongside the claim's provenance."""
    diags: list[Diagnostic] = []

    # Source-level invariant: declared L ⊆ U.
    for name, src in query.get("sources", {}).items():
        if "lower" in src and "upper" in src:
            L = frozenset(tuple(t) for t in src["lower"].get("tuples", []))
            U = frozenset(tuple(t) for t in src["upper"].get("tuples", []))
            if not (L <= U):
                diags.append(diag("QV5-01", "inverted_bounds", f"source:{name}",
                                  "Source lower relation contains a tuple absent from the upper relation"))

    # Claim invariant: L ⊆ U (13.1).
    if claim.lower is not None and claim.upper is not None:
        if not (
            claim.lower.tuples <= claim.upper.tuples
            and [f.to_json() for f in claim.lower.fields] == [f.to_json() for f in claim.upper.fields]
        ):
            diags.append(diag("QV5-01", "inverted_bounds", "root_bound",
                              "Lower relation contains a tuple absent from the upper relation"))

    # Guarantee-kind consistency (13.2).
    g = claim.guarantee
    if g not in GUARANTEE_KINDS:
        diags.append(diag("QV5-02", "unknown_guarantee_kind", "root_bound", f"Unknown guarantee kind {g!r}"))
    else:
        if g in {"lower_bound", "bounded", "exact"} and claim.lower is None:
            diags.append(diag("QV5-02", "missing_certified_side", "root_bound",
                              f"Guarantee {g} claims a certified lower side without a concrete bound relation"))
        if g in {"upper_bound", "bounded", "exact"} and claim.upper is None:
            diags.append(diag("QV5-02", "missing_certified_side", "root_bound",
                              f"Guarantee {g} claims a certified upper side without a concrete bound relation"))
        if g == "exact":
            if claim.lower is not None and claim.upper is not None and claim.lower.tuples != claim.upper.tuples:
                diags.append(diag("QV5-03", "false_exact", "root_bound", "Exact guarantee with L != U"))
            ud = claim.provenance.upper_derivation
            if ud is None or not ud.rule_id:
                diags.append(diag("QV5-03", "false_exact", "root_bound",
                                  "Exact guarantee without a certified derivation"))
        if g == "heuristic" and (claim.lower is not None or claim.upper is not None):
            diags.append(diag("QV5-02", "guarantee_label_mismatch", "root_bound",
                              "Heuristic guarantee with certified sides present"))

    # Aggregate conformance (13.11-13.14): when the claim cites the same
    # aggregate rule the baseline inference used, the claimed interval must
    # equal the rule's certified interval. Tighter bounds from a *different*
    # registered rule are not rejected here (13.18).
    if inference is not None and claim.bound_rule in AGGREGATE_RULES:
        root = query.get("root")
        root_node = next((x for x in query.get("nodes", []) if x.get("id") == root), None)
        inferred_root = inference.get(root)
        if (
            root_node is not None
            and root_node.get("op") == "aggregate"
            and inferred_root is not None
            and inferred_root.bound_rule == claim.bound_rule
        ):
            exp_L, exp_U, exp_intervals, exp_empty, _ = _aggregate_bounds(inference[root_node["input"]], root_node)
            exp_iv = sorted(json.dumps(dict(iv), sort_keys=True) for iv in exp_intervals)
            cl_iv = sorted(json.dumps(dict(iv), sort_keys=True) for iv in claim.intervals)
            if exp_L is not None and (
                claim.lower is None
                or claim.upper is None
                or claim.lower.tuples != exp_L.tuples
                or claim.upper.tuples != exp_U.tuples
                or set(claim.may_be_empty_groups) != set(exp_empty)
                or cl_iv != exp_iv
            ):
                diags.append(diag("QV5-12", "aggregate_bound_nonconformance", "root_bound",
                                  "Aggregate bound does not conform to the registered rule's certified interval"))

    # Upper-bound derivation provenance (12.6).
    if claim.upper is not None and claim.guarantee in {"bounded", "exact", "upper_bound"}:
        ud = claim.provenance.upper_derivation
        if ud is None or not ud.rule_id:
            diags.append(diag("QV8-06", "missing_upper_derivation", "root_bound.provenance",
                              "Bounded result upper object has no transfer rule or source-bound provenance"))

    # QV8-05: every lower-bound tuple carries the requested supported
    # membership provenance (12.4-12.5). A requested mode above `tuple`
    # requires a per-tuple entry in that mode for every lower tuple; the
    # minimal `tuple`/`none` modes impose no per-tuple obligation.
    mode = claim.provenance.lower_membership_mode
    if mode in POSITIVE_MODES and claim.lower is not None:
        have = {tuple(lm.tuple_) for lm in claim.provenance.lower_memberships
                if lm.mode == mode}
        for t in sorted(claim.lower.tuples, key=_tuple_key):
            if t not in have:
                diags.append(diag("QV8-05", "missing_membership_provenance",
                                  f"root_bound.provenance:{_tuple_key(t)}",
                                  f"Lower-bound tuple carries no {mode} membership "
                                  "provenance as requested (12.5)"))

    # Provenance honesty (12.7): upper-only tuples carry no positive
    # why-provenance asserting exact membership.
    if claim.lower is not None:
        L = claim.lower.tuples
        for lm in claim.provenance.lower_memberships:
            if lm.mode in POSITIVE_MODES and tuple(lm.tuple_) not in L:
                in_U = claim.upper is not None and tuple(lm.tuple_) in claim.upper.tuples
                if in_U:
                    diags.append(diag("QV8-07", "upper_only_why_provenance",
                                      f"root_bound.provenance:{_tuple_key(tuple(lm.tuple_))}",
                                      "Tuple in U\\L carries ordinary why-provenance asserting exact membership"))
                    diags.append(diag("QINV-14", "bound_provenance_honesty",
                                      f"root_bound.provenance:{_tuple_key(tuple(lm.tuple_))}",
                                      "Bound provenance conflates upper-bound enclosure with exact membership"))

    # Stale assurance (13.3): stale dependencies evaluate effectively as unknown.
    stale = set(query.get("stale_dependencies", []))
    if stale & set(claim.assurance.depends_on) and claim.assurance.status != "unknown":
        diags.append(diag("QV5-10", "stale_assurance", "root_bound.assurance",
                          "Stale assurance dependency must evaluate effectively as unknown"))

    # Claim-based semantic rules (QV3/QV4/QV5-06/QINV-06): the claim
    # commits to more than the plan supports.
    diags.extend(claim_semantic_diagnostics(query, claim, inference))

    # Logical disclosure and leakage separation (32): the record's
    # disclosure declarations and the claim's provenance obey the
    # selected policy (QV8-08, QV9-03/04/05/08).
    diags.extend(disclosure_diagnostics(query, claim, record))

    return diags


# ---------------------------------------------------------------------------
# Golden matching (inference vs claim, with 13.18 tighter-bound acceptance)

def _rel_ge(a: Relation | None, b: Relation | None) -> bool:
    """a ⊇ b (a is at least as large a lower bound as b)."""
    if b is None:
        return True
    if a is None:
        return False
    return b.tuples <= a.tuples


def _rel_le(a: Relation | None, b: Relation | None) -> bool:
    """a ⊆ b (a is at least as small an upper bound as b)."""
    if a is None:
        return True
    if b is None:
        return False
    return a.tuples <= b.tuples


def match_core(inferred: CertifiedBound, claimed: CertifiedBound) -> bool:
    """True when the claim equals the inferred bound, or is a registered
    tighter bound (13.18: the validator MUST NOT reject tighter bounds)."""
    ci, cc = inferred.core(), claimed.core()
    if ci == cc:
        return True
    if ci["may_be_empty_groups"] != cc["may_be_empty_groups"]:
        return False
    if not claimed.bound_rule or claimed.bound_rule not in BOUND_RULES:
        return False
    # A registered tighter bound may refine the sides (and thereby the
    # guarantee kind, e.g. bounded -> exact); the guarantee label itself is
    # not a matching criterion (13.18, 13.2).
    return _rel_ge(claimed.lower, inferred.lower) and _rel_le(claimed.upper, inferred.upper)
