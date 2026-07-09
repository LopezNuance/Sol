from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

from .model import Artifact
from .refs import (
    OBJECT_RE,
    DIGEST_RE,
    NAMED_OUTPUT_RE,
    iter_refs,
    iter_strings,
    parse_ref,
    bare_id,
)

SUPPORTED_FEATURES = {
    "sol:feature/linear_execution",
    "sol:feature/internal_object_store",
    "sol:feature/machine_summary",
    "sol:feature/signatures",
    "sol:feature/external_evidence",
}

DEFAULT_LIFECYCLES = {"draft", "active", "superseded", "withdrawn"}
PROPOSAL_LIFECYCLES = {"pending_review", "accepted", "rejected", "amended", "superseded", "applied"}
STALENESS = {"current", "stale", "unknown"}
VERIFICATION = {"unverified", "verified", "failed_verification", "needs_reverification"}
RUN_STATUSES = {"success", "partial_success", "failure", "cancelled"}

CAPS_BY_AUTONOMY = {
    "read_only": {"read"},
    "propose_only": {"read", "create_branch", "write_cell", "write_record"},
    "review_required": {"read", "create_branch", "write_cell", "write_record", "execute", "review", "commit"},
    "autonomous_commit": {"read", "create_branch", "write_cell", "write_record", "execute", "commit", "apply_proposal"},
}

@dataclass(frozen=True)
class Diagnostic:
    rule_id: str
    category: str
    severity: str
    target: str
    message: str

    def key(self):
        return (self.rule_id, self.category, self.target, self.message)


class Validator:
    def __init__(self, artifact: Artifact, profile: str = "default"):
        self.a = artifact
        self.profile = profile
        self.diags: List[Diagnostic] = []
        self._diag_keys: Set[tuple] = set()

    def diag(self, rule_id: str, category: str, target: str, message: str, severity: str = "error"):
        d = Diagnostic(rule_id, category, severity, target, message)
        if d.key() not in self._diag_keys:
            self._diag_keys.add(d.key())
            self.diags.append(d)

    def run(self) -> List[Diagnostic]:
        self.v0()
        self.v1()
        self.v2()
        self.v3()
        self.v4()
        self.v5()
        self.diags.sort(key=lambda d: (d.rule_id, d.category, d.target, d.message))
        return self.diags

    # ---------- helpers ----------
    def all_payloads(self) -> List[Any]:
        return [
            self.a.manifest,
            self.a.execution_structure,
            list(self.a.cells.values()),
            list(self.a.records.values()),
            list(self.a.actors.values()),
            list(self.a.runs.values()),
            list(self.a.commits.values()),
            list(self.a.renders.values()),
        ]

    def object_exists(self, digest: str) -> bool:
        return self.a.object_path(digest).exists()

    def object_hash_valid(self, digest: str) -> bool:
        p = self.a.object_path(digest)
        if not p.exists() or not p.is_file():
            return False
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        return h == digest

    def get_run_binding(self, named_ref: str) -> Dict[str, Any] | None:
        # Current prototype resolves to any success/partial_success run binding unless it is marked stale/invalidated.
        for run in self.a.runs.values():
            if run.get("status") not in {"success", "partial_success"}:
                continue
            for b in run.get("output_bindings", []):
                if b.get("named_output") == named_ref and b.get("status", "valid") == "valid":
                    return b
        return None

    def execution_order(self) -> List[str]:
        es = self.a.execution_structure or {}
        if es.get("type", "linear") == "linear":
            return [bare_id(x, "cell") for x in es.get("cells", [])]
        return []

    def ref_exists(self, kind: str, ident: str | tuple[str, str]) -> bool:
        if kind == "cell":
            return ident in self.a.cells
        if kind == "record":
            return ident in self.a.records
        if kind == "run":
            return ident in self.a.runs
        if kind == "commit":
            return ident in self.a.commits
        if kind == "render":
            return ident in self.a.renders
        if kind == "branch":
            return True  # Branch objects are not fully modeled in prototype.
        if kind == "named_output":
            cid, name = ident  # type: ignore[misc]
            return self.get_run_binding(f"cell:{cid}#{name}") is not None
        if kind == "object":
            return self.object_exists(ident)  # type: ignore[arg-type]
        if kind == "digest":
            return True
        if kind == "sol_uri":
            return True
        return False

    def record_status(self, rec: Dict[str, Any]) -> Dict[str, str]:
        return rec.get("status", {}) if isinstance(rec.get("status", {}), dict) else {}

    def record_staleish(self, rec: Dict[str, Any] | None) -> bool:
        if not rec:
            return True
        st = self.record_status(rec)
        return st.get("staleness") in {"stale", "unknown"} or st.get("verification") in {"needs_reverification", "failed_verification"}

    def all_object_refs(self) -> List[str]:
        refs = []
        for payload in self.all_payloads():
            for ref in iter_refs(payload):
                if ref.startswith("object:"):
                    refs.append(ref)
        return refs

    # ---------- V0 ----------
    def v0(self):
        if not self.a.manifest:
            self.diag("V0-01", "schema", "manifest", "manifest.json missing or empty")
            return
        if not self.a.manifest.get("sol_version"):
            self.diag("V0-01", "schema", "manifest.sol_version", "sol_version missing")
        if not self.a.manifest.get("artifact_id"):
            self.diag("V0-02", "schema", "manifest.artifact_id", "artifact_id missing")
        for feat in self.a.manifest.get("required_features", []):
            if feat not in SUPPORTED_FEATURES:
                self.diag("V0-03", "unsupported", f"manifest.required_features:{feat}", f"unsupported required feature {feat}")
        for rec in self.a.records.values():
            self.check_status_vocab(rec)
        for payload in self.all_payloads():
            for ref in iter_refs(payload):
                parsed = parse_ref(ref)
                if parsed is None:
                    self.diag("V0-05", "invalid_reference", ref, "reference does not parse under Sol grammar")
                    # If it looks like an object/digest, also emit V0-06.
                    if ref.startswith("object:") or ref.startswith("digest:"):
                        self.diag("V0-06", "invalid_reference", ref, "object/digest reference malformed")
                    continue
                kind, ident = parsed
                if kind == "object":
                    digest = ident  # type: ignore[assignment]
                    if not self.object_exists(digest):
                        self.diag("V0-06", "missing_object", ref, "object reference does not resolve inside artifact")
                elif kind == "digest":
                    # parse_ref already validated.
                    pass
        # object store hash verification
        obj_root = self.a.root / "objects" / "sha256"
        if obj_root.exists():
            for p in sorted(x for x in obj_root.rglob("*") if x.is_file()):
                digest = p.name
                if not OBJECT_RE.match(f"object:sha256:{digest}"):
                    self.diag("V0-06", "invalid_reference", f"object:sha256:{digest}", "stored object file name is not a sha256 digest")

    def check_status_vocab(self, rec: Dict[str, Any]):
        rid = rec.get("record_id", "<unknown>")
        st = self.record_status(rec)
        rtype = rec.get("record_type", "")
        lifecycle = st.get("lifecycle")
        if lifecycle:
            allowed = PROPOSAL_LIFECYCLES if rtype == "sol:record/proposal" else DEFAULT_LIFECYCLES
            if lifecycle not in allowed:
                self.diag("V0-04", "illegal_status_transition", f"record:{rid}.status.lifecycle", f"unknown lifecycle {lifecycle}")
        stale = st.get("staleness")
        if stale and stale not in STALENESS:
            self.diag("V0-04", "illegal_status_transition", f"record:{rid}.status.staleness", f"unknown staleness {stale}")
        ver = st.get("verification")
        if ver and ver not in VERIFICATION:
            self.diag("V0-04", "illegal_status_transition", f"record:{rid}.status.verification", f"unknown verification {ver}")

    # ---------- V1 ----------
    def v1(self):
        self.check_commit_ancestry_and_authors()
        for cell in self.a.cells.values():
            ctype = cell.get("cell_type")
            cid = cell.get("cell_id", "<unknown>")
            if ctype == "sol:cell/anchor":
                ref = cell.get("anchors_record")
                if not ref or not parse_ref(ref) or parse_ref(ref)[0] != "record":
                    self.diag("V1-03", "invalid_reference", f"cell:{cid}", "anchor cell must reference exactly one record")
                elif not self.ref_exists("record", parse_ref(ref)[1]):
                    self.diag("V1-03", "invalid_reference", f"cell:{cid}", "anchor references missing record")
                if any(k in cell for k in ["statement", "canonical_content", "content"]):
                    self.diag("V1-03", "schema", f"cell:{cid}", "anchor duplicates canonical record content")
            if ctype == "sol:cell/gate":
                ref = cell.get("decision_ref")
                parsed = parse_ref(ref) if isinstance(ref, str) else None
                if not parsed or parsed[0] != "record" or not self.ref_exists("record", parsed[1]):
                    self.diag("V1-04", "invalid_reference", f"cell:{cid}", "gate cell must reference existing decision record")
                else:
                    rec = self.a.records.get(parsed[1])  # type: ignore[index]
                    if rec and rec.get("record_type") != "sol:record/decision":
                        self.diag("V1-04", "invalid_reference", f"cell:{cid}", "gate cell references non-decision record")
        # References existence checks for named outputs and object hash verification.
        for payload in self.all_payloads():
            for ref in iter_refs(payload):
                parsed = parse_ref(ref)
                if parsed and parsed[0] == "named_output":
                    if not self.ref_exists("named_output", parsed[1]):
                        self.diag("V1-05", "invalid_reference", ref, "named-output reference does not resolve through a valid run binding")
        for obj_ref in self.all_object_refs():
            m = OBJECT_RE.match(obj_ref)
            if m:
                digest = m.group(1)
                if not self.object_exists(digest):
                    self.diag("V1-06", "missing_object", obj_ref, "reachable object is absent")
                elif not self.object_hash_valid(digest):
                    self.diag("V1-07", "corrupt_object", obj_ref, "object bytes do not match digest")

    def check_commit_ancestry_and_authors(self):
        # Author resolution
        for c in self.a.commits.values():
            cid = c.get("commit_id", "<unknown>")
            author = c.get("author")
            if not author or author not in self.a.actors:
                self.diag("V1-02", "invalid_actor", f"commit:{cid}", "commit author does not resolve to actor record")
        # Acyclic ancestry
        visiting: Set[str] = set()
        visited: Set[str] = set()
        def dfs(cid: str):
            if cid in visiting:
                self.diag("V1-01", "commit_cycle", f"commit:{cid}", "commit ancestry contains cycle")
                return
            if cid in visited:
                return
            visiting.add(cid)
            commit = self.a.commits.get(cid)
            if commit:
                for pref in commit.get("parents", []):
                    pid = bare_id(pref, "commit")
                    if pid not in self.a.commits:
                        self.diag("V1-01", "invalid_reference", f"commit:{cid}", f"parent {pref} missing")
                    else:
                        dfs(pid)
            visiting.remove(cid)
            visited.add(cid)
        for cid in self.a.commits:
            dfs(cid)

    # ---------- V2 ----------
    def v2(self):
        order = self.execution_order()
        idx = {c: i for i, c in enumerate(order)}
        for run in self.a.runs.values():
            rid = run.get("run_id", "<unknown>")
            status = run.get("status")
            if status == "partial_uncommitted":
                self.diag("V2-04", "schema", f"run:{rid}", "partial_uncommitted must not appear in history")
            if status not in RUN_STATUSES:
                continue
            cells = [bare_id(x, "cell") for x in run.get("cells_executed", [])]
            if order and cells != order[:len(cells)]:
                self.diag("V2-01", "execution_order", f"run:{rid}", "run cells_executed do not follow linear execution structure")
            if status == "partial_success":
                # Must have failure record same run.
                if not any(r.get("record_type") == "sol:record/failure" and r.get("run_id") == f"run:{rid}" for r in self.a.records.values()):
                    self.diag("V2-03", "invalid_partial_success", f"run:{rid}", "partial_success run lacks paired failure record")
                executed_set = set(f"cell:{c}" for c in cells)
                for b in run.get("output_bindings", []):
                    named = b.get("named_output", "")
                    m = NAMED_OUTPUT_RE.match(named)
                    if m and f"cell:{m.group(1)}" not in executed_set:
                        self.diag("V2-03", "invalid_partial_success", f"run:{rid}", "partial_success binds output from unexecuted cell")
        # Declared dependencies consistent with execution order.
        for cell in self.a.cells.values():
            cid = cell.get("cell_id", "")
            for dep in cell.get("depends_on", []):
                dep_id = bare_id(dep, "cell")
                if cid in idx and dep_id in idx and idx[dep_id] >= idx[cid]:
                    self.diag("V2-02", "invalid_dependency", f"cell:{cid}", f"depends_on later/non-ancestor cell {dep}")
        self.check_staleness_propagation()
        self.check_dependency_hints()

    def stale_refs(self) -> Set[str]:
        stale: Set[str] = set()
        for run in self.a.runs.values():
            for b in run.get("output_bindings", []):
                if b.get("status") in {"invalidated", "stale"}:
                    if b.get("named_output"):
                        stale.add(b["named_output"])
                    if b.get("object_ref"):
                        stale.add(b["object_ref"])
        for rec in self.a.records.values():
            rid = rec.get("record_id")
            if self.record_staleish(rec):
                stale.add(f"record:{rid}")
        return stale

    def check_staleness_propagation(self):
        stale = self.stale_refs()
        # Direct record dependencies.
        for rec in self.a.records.values():
            rid = rec.get("record_id", "<unknown>")
            st = self.record_status(rec)
            deps = rec.get("depends_on", []) + rec.get("supporting_evidence", []) + rec.get("based_on", [])
            if any(d in stale for d in deps):
                if st.get("staleness") != "stale" and st.get("verification") not in {"needs_reverification", "failed_verification"}:
                    self.diag("V2-05", "stale_record", f"record:{rid}", "record depends on stale/invalidated dependency but status was not updated")
        # Aggregate evidence: claims.
        for claim in [r for r in self.a.records.values() if r.get("record_type") == "sol:record/claim"]:
            cid = claim.get("record_id", "<unknown>")
            supports = claim.get("supporting_evidence", [])
            evidence_records = [self.a.record(s) for s in supports]
            if not evidence_records:
                continue
            stale_count = sum(1 for e in evidence_records if self.record_staleish(e))
            st = self.record_status(claim)
            if stale_count == len(evidence_records):
                if st.get("staleness") != "stale" or st.get("verification") != "needs_reverification":
                    self.diag("V2-05", "stale_record", f"record:{cid}", "all supporting evidence stale/unavailable but claim not stale/needs_reverification")
            elif stale_count > 0:
                if st.get("verification") != "needs_reverification":
                    self.diag("V2-05", "stale_record", f"record:{cid}", "partial supporting evidence stale but claim not marked needs_reverification")

    def check_dependency_hints(self):
        for run in self.a.runs.values():
            for hint in run.get("dependency_hints", []):
                cid = bare_id(hint.get("cell_id", ""), "cell")
                cell = self.a.cells.get(cid)
                declared = set(cell.get("depends_on", [])) if cell else set()
                for undeclared in hint.get("undeclared_reads", []):
                    if undeclared not in declared:
                        self.diag("V2-06", "undeclared_dependency", f"cell:{cid}", f"trusted hint reports undeclared read {undeclared}")

    # ---------- V3 ----------
    def v3(self):
        self.check_verified_records()
        self.check_status_transitions()
        self.check_reproducibility()
        self.check_verification_concordance()
        self.check_proposal_application()
        self.check_decisions_and_claims()
        self.check_external_evidence()

    def check_verified_records(self):
        passed_targets = set()
        for rec in self.a.records.values():
            if rec.get("record_type") == "sol:record/verification" and rec.get("result") == "passed" and self.record_status(rec).get("staleness", "current") == "current":
                target = rec.get("target")
                if target:
                    passed_targets.add(target)
        for rec in self.a.records.values():
            rid = rec.get("record_id", "<unknown>")
            if self.record_status(rec).get("verification") == "verified":
                if f"record:{rid}" not in passed_targets:
                    self.diag("V3-01", "unverified_claim", f"record:{rid}", "verification:verified without passed verification record")

    def check_status_transitions(self):
        # Explicit illegal transition markers.
        for rec in self.a.records.values():
            rid = rec.get("record_id", "<unknown>")
            tr = rec.get("status_transition")
            if tr:
                frm = tr.get("from")
                to = tr.get("to")
                via = tr.get("via")
                if frm == "stale" and to == "current" and via not in {"successful_rerun", "passed_verification"}:
                    self.diag("V3-02", "illegal_status_transition", f"record:{rid}", "stale->current transition without rerun or verification")
        # Failed verification should update target.
        for ver in self.a.records.values():
            if ver.get("record_type") == "sol:record/verification" and ver.get("result") == "failed":
                target = ver.get("target")
                if target and (trec := self.a.record(target)):
                    if self.record_status(trec).get("verification") == "verified":
                        self.diag("V3-02", "illegal_status_transition", target, "failed verification exists but target remains verified")

    def check_reproducibility(self):
        status = self.a.manifest.get("reproducibility_status")
        if status == "reproducible":
            ok = any(r.get("record_type") == "sol:record/verification" and r.get("method") == "sol:verify/reexecution" and r.get("result") == "passed" for r in self.a.records.values())
            if not ok:
                self.diag("V3-03", "broken_provenance", "manifest.reproducibility_status", "reproducibility asserted without passed reexecution verification")

    def check_verification_concordance(self):
        deterministic = self.a.manifest.get("execution", {}).get("deterministic")
        for rec in self.a.records.values():
            if rec.get("record_type") == "sol:record/verification" and rec.get("method") == "sol:verify/reexecution":
                if not rec.get("concordance"):
                    self.diag("V3-04", "broken_provenance", f"record:{rec.get('record_id')}", "reexecution verification missing concordance model")
                elif deterministic is True and rec["concordance"].get("type") not in {"exact", "tolerance"}:
                    self.diag("V3-04", "broken_provenance", f"record:{rec.get('record_id')}", "concordance inconsistent with deterministic manifest")

    def check_proposal_application(self):
        for commit in self.a.commits.values():
            cid = commit.get("commit_id", "<unknown>")
            changes = commit.get("changes", [])
            apply_ops = [c for c in changes if c.get("op") == "apply_proposal"]
            for op in apply_ops:
                pref = op.get("proposal")
                prop = self.a.record(pref) if pref else None
                if not prop:
                    self.diag("V3-05", "invalid_proposal_application", f"commit:{cid}", "apply_proposal references missing proposal")
                    continue
                applied = commit.get("applied_proposals", [])
                app = next((a for a in applied if a.get("proposal") == pref), None)
                if not app or not app.get("accepted_by"):
                    self.diag("V3-05", "invalid_proposal_application", f"commit:{cid}", "applied proposal lacks accepting review linkage")
                else:
                    for rref in app.get("accepted_by", []):
                        if not self.a.record(rref):
                            self.diag("V3-05", "invalid_proposal_application", f"commit:{cid}", "accepting review missing")
                # Constituent proposal ops must be present.
                for pchg in prop.get("changes", []):
                    if not any(self._op_matches(pchg, c) for c in changes if c.get("op") != "apply_proposal"):
                        self.diag("V3-05", "invalid_proposal_application", f"commit:{cid}", "commit changes do not match proposal changeset")

    def _op_matches(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        keys = ["op", "target", "path", "value_ref", "cell_id"]
        return all(a.get(k) == b.get(k) for k in keys if k in a or k in b)

    def check_decisions_and_claims(self):
        for rec in self.a.records.values():
            if rec.get("record_type") == "sol:record/decision":
                rid = rec.get("record_id")
                for field in ["candidates", "selected", "decision_rule", "made_by", "based_on"]:
                    if not rec.get(field):
                        self.diag("V3-06", "schema", f"record:{rid}", f"decision missing {field}")
                for ref in rec.get("based_on", []):
                    if not self.a.record(ref):
                        self.diag("V3-07", "invalid_reference", f"record:{rid}", f"decision based_on missing record {ref}")

    def check_external_evidence(self):
        for rec in self.a.records.values():
            if rec.get("record_type") == "sol:record/evidence" and rec.get("external_ref"):
                rid = rec.get("record_id")
                if "availability" not in rec["external_ref"]:
                    self.diag("V3-08", "broken_provenance", f"record:{rid}", "external evidence missing availability")
        # unavailable evidence aggregate check
        for claim in [r for r in self.a.records.values() if r.get("record_type") == "sol:record/claim"]:
            supports = [self.a.record(s) for s in claim.get("supporting_evidence", [])]
            if not supports:
                continue
            def unavailable(e):
                return bool(e and e.get("external_ref", {}).get("availability") == "unavailable") or self.record_staleish(e)
            if all(unavailable(e) for e in supports):
                st = self.record_status(claim)
                if st.get("staleness") != "stale" or st.get("verification") != "needs_reverification":
                    self.diag("V3-08", "stale_record", f"record:{claim.get('record_id')}", "unavailable evidence did not propagate to dependent claim")

    # ---------- V4 ----------
    def actor_caps(self, actor_id: str) -> Set[str]:
        actor = self.a.actors.get(actor_id, {})
        explicit = set(actor.get("capabilities", []))
        if explicit:
            return explicit
        level = actor.get("autonomy_level")
        return set(CAPS_BY_AUTONOMY.get(level, {"read"}))

    def v4(self):
        auth = self.a.manifest.get("authorization", {})
        protected = {b.get("branch"): b for b in auth.get("protected_branches", [])}
        for commit in self.a.commits.values():
            cid = commit.get("commit_id", "<unknown>")
            author = commit.get("author")
            caps = self.actor_caps(author) if author else set()
            branch = commit.get("branch")
            if branch in protected:
                pb = protected[branch]
                allowed = set(pb.get("allowed_committers", []))
                req = set(pb.get("required_capabilities", []))
                if author not in allowed and not req.issubset(caps):
                    self.diag("V4-01", "unauthorized_action", f"commit:{cid}", "commit violates protected branch policy")
            # capability sufficiency for basic operations
            for ch in commit.get("changes", []):
                op = ch.get("op")
                needed = None
                if op == "modify_cell":
                    needed = "write_cell"
                elif op == "update_record_status":
                    needed = "write_record"
                elif op == "apply_proposal":
                    needed = "apply_proposal"
                elif op == "bind_output":
                    needed = "execute"
                if needed and needed not in caps:
                    self.diag("V4-03", "unauthorized_action", f"commit:{cid}", f"actor lacks capability {needed} for op {op}")
            if commit.get("changes") and "commit" not in caps:
                self.diag("V4-03", "unauthorized_action", f"commit:{cid}", "actor lacks commit capability")
        # self-review applications
        policy = self.a.manifest.get("authorization", {})
        permit_self = bool(policy.get("permit_self_application", False))
        for commit in self.a.commits.values():
            cid = commit.get("commit_id", "<unknown>")
            for app in commit.get("applied_proposals", []):
                prop = self.a.record(app.get("proposal", ""))
                if not prop:
                    continue
                proposer = prop.get("created_by")
                reviewers = []
                for rref in app.get("accepted_by", []):
                    rr = self.a.record(rref)
                    if rr:
                        reviewers.append(rr.get("reviewed_by"))
                if reviewers and set(reviewers) == {proposer} and not permit_self:
                    self.diag("V4-02", "unauthorized_action", f"commit:{cid}", "actor is sole accepting reviewer of its own proposal")

    # ---------- V5 ----------
    def v5(self):
        for render in self.a.renders.values():
            rid = render.get("render_id", "<unknown>")
            if not render.get("source_commit"):
                self.diag("V5-01", "schema", f"render:{rid}", "render missing source_commit")
            includes = render.get("includes_records", [])
            disclosures = set(render.get("stale_disclosures", []))
            for rref in includes:
                rec = self.a.record(rref)
                if rec and self.record_staleish(rec) and rref not in disclosures:
                    self.diag("V5-02", "dishonest_render", f"render:{rid}", f"render includes stale/unverified record {rref} without disclosure")
        # Machine summary comparison.
        summary_path = self.a.root / "renders" / "machine_summary.json"
        if summary_path.exists():
            try:
                on_disk = json.loads(summary_path.read_text(encoding="utf-8"))
                gen = generate_machine_summary(self.a)
                if canonical(on_disk) != canonical(gen):
                    self.diag("V5-03", "dishonest_render", "render:machine_summary", "machine summary diverges from artifact state")
            except Exception as e:
                self.diag("V5-03", "dishonest_render", "render:machine_summary", f"machine summary unreadable: {e}")


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_machine_summary(a: Artifact) -> Dict[str, Any]:
    def short_status(rec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "record_id": rec.get("record_id"),
            "record_type": rec.get("record_type"),
            "summary": rec.get("summary"),
            "status": rec.get("status", {}),
        }
    return {
        "render_id": "machine_summary",
        "target": "machine_summary",
        "source_commit": a.manifest.get("current_commit") or max(a.commits.keys(), default=None),
        "artifact_id": a.manifest.get("artifact_id"),
        "sol_version": a.manifest.get("sol_version"),
        "execution_structure": a.execution_structure,
        "cells": [
            {"cell_id": c.get("cell_id"), "cell_type": c.get("cell_type"), "summary": c.get("summary")}
            for c in sorted(a.cells.values(), key=lambda x: x.get("cell_id", ""))
        ],
        "actors": sorted(a.actors.keys()),
        "records": [short_status(r) for r in sorted(a.records.values(), key=lambda x: x.get("record_id", ""))],
        "runs": [
            {"run_id": r.get("run_id"), "status": r.get("status"), "source_commit": r.get("source_commit"), "result_commit": r.get("result_commit")}
            for r in sorted(a.runs.values(), key=lambda x: x.get("run_id", ""))
        ],
    }


def validate_path(path: str | Path, profile: str = "default") -> List[Diagnostic]:
    art = Artifact.load(path)
    return Validator(art, profile=profile).run()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate an exploded Sol artifact")
    p.add_argument("artifact", help="Path to artifact.sol.d")
    p.add_argument("--profile", default="default", choices=["default", "strict"])
    p.add_argument("--json", action="store_true", help="emit JSON diagnostics")
    args = p.parse_args(argv)
    diags = validate_path(args.artifact, profile=args.profile)
    payload = [asdict(d) for d in diags]
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if not diags:
            print("valid")
        else:
            for d in diags:
                print(f"{d.rule_id}\t{d.severity}\t{d.category}\t{d.target}\t{d.message}")
    return 1 if any(d.severity == "error" for d in diags) else 0

if __name__ == "__main__":
    raise SystemExit(main())
