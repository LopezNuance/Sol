"""Safe HTML/Markdown rendering of committed Sol artifact state.

RFC-SOL-0001 section 47: rendered views are derived products; a rendered
view MUST identify its source commit; rendering MUST NOT execute code by
default; HTML renderers SHOULD default to script-disabled output; rendered
views that include stale records, invalidated outputs, unverified claims,
or stale decisions MUST disclose that status (V5-02).

This module is a pure serializer of committed artifact state: it never
executes cell source, never follows external references, and emits no
scripts or event handlers in HTML output (INV-07).
"""

from __future__ import annotations

import html
from typing import Any

from .model import Artifact

CSS = """
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; color: #1a1a1a; line-height: 1.5; }
header { border-bottom: 2px solid #1a1a1a; margin-bottom: 1rem; padding-bottom: .5rem; }
.meta { color: #555; font-size: .9rem; }
section { margin-bottom: 1.5rem; }
h2 { font-size: 1.2rem; border-bottom: 1px solid #ccc; padding-bottom: .25rem; }
.cell { border: 1px solid #ddd; border-radius: 4px; padding: .75rem; margin-bottom: .75rem; }
.cell .type { font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; color: #555; }
.cell pre { background: #f6f6f6; padding: .5rem; overflow-x: auto; font-size: .85rem; }
.anchor { border-left: 4px solid #2a6; background: #f2fbf6; }
.disclosures { border: 1px solid #a60; background: #fff8ef; padding: .75rem; }
.disclosures li { margin-bottom: .25rem; }
table { border-collapse: collapse; font-size: .85rem; }
th, td { border: 1px solid #ccc; padding: .25rem .5rem; text-align: left; }
footer { margin-top: 2rem; border-top: 1px solid #ccc; padding-top: .5rem; color: #555; font-size: .85rem; }
"""


def _staleish(rec: dict[str, Any]) -> bool:
    st = rec.get("status", {}) if isinstance(rec.get("status"), dict) else {}
    return (
        st.get("staleness") in {"stale", "unknown"}
        or st.get("verification") in {"needs_reverification", "failed_verification"}
    )


def _disclosures(a: Artifact) -> list[dict[str, str]]:
    """Deterministic disclosure list required by section 47 / V5-02."""
    out: list[dict[str, str]] = []
    if a.manifest.get("provenance_status") == "incomplete":
        src = a.manifest.get("imported_from", "unknown source")
        out.append({
            "kind": "provenance",
            "target": "manifest",
            "text": (
                f"Imported artifact ({src}): provenance is incomplete. Imported "
                "outputs are classified staleness=unknown, verification=unverified; "
                "no Sol run records exist for them."
            ),
        })
    for run in sorted(a.runs.values(), key=lambda r: r.get("run_id", "")):
        for b in run.get("output_bindings", []):
            if b.get("status") in {"stale", "invalidated"}:
                out.append({
                    "kind": "output",
                    "target": b.get("named_output", ""),
                    "text": f"Output {b.get('named_output')} is {b.get('status')} (run {run.get('run_id')}).",
                })
    for rec in sorted(a.records.values(), key=lambda r: r.get("record_id", "")):
        rid = rec.get("record_id", "")
        st = rec.get("status", {}) if isinstance(rec.get("status"), dict) else {}
        if _staleish(rec):
            out.append({
                "kind": "record",
                "target": f"record:{rid}",
                "text": f"Record {rid} is {st.get('staleness')}/{st.get('verification')}; dependent results require reverification.",
            })
        elif rec.get("record_type") == "sol:record/claim" and st.get("verification") == "unverified":
            out.append({
                "kind": "claim",
                "target": f"record:{rid}",
                "text": f"Claim {rid} is unverified.",
            })
    return out


def _cell_order(a: Artifact) -> list[str]:
    es = a.execution_structure or {}
    if es.get("type", "linear") == "linear":
        order = [ref.split(":", 1)[1] if ref.startswith("cell:") else ref for ref in es.get("cells", [])]
        known = [c for c in order if c in a.cells]
        extra = [c for c in sorted(a.cells) if c not in known]
        return known + extra
    return sorted(a.cells)


def _binding_for(a: Artifact, named_ref: str) -> dict[str, Any] | None:
    for run in sorted(a.runs.values(), key=lambda r: r.get("run_id", "")):
        if run.get("status") not in {"success", "partial_success"}:
            continue
        for b in run.get("output_bindings", []):
            if b.get("named_output") == named_ref and b.get("status", "valid") == "valid":
                return b
    return None


def _record_fields(rec: dict[str, Any]) -> list[tuple[str, str]]:
    """Type-specific display fields (deterministic order)."""
    rid = rec.get("record_id", "")
    rtype = rec.get("record_type", "")
    st = rec.get("status", {}) if isinstance(rec.get("status"), dict) else {}
    rows: list[tuple[str, str]] = [
        ("record_id", rid),
        ("type", rtype),
        ("summary", rec.get("summary", "")),
        ("status", f"{st.get('lifecycle')} / {st.get('staleness')} / {st.get('verification')}"),
    ]
    if rtype == "sol:record/claim":
        rows += [
            ("statement", rec.get("statement", "")),
            ("claim_type", rec.get("claim_type", "")),
            ("supporting_evidence", ", ".join(rec.get("supporting_evidence", []))),
            ("confidence", str(rec.get("confidence", ""))),
        ]
    elif rtype == "sol:record/evidence":
        rows += [
            ("evidence_type", rec.get("evidence_type", "")),
            ("source_ref", rec.get("source_ref", "")),
            ("source_object", rec.get("source_object", "")),
            ("supports", ", ".join(rec.get("supports", []))),
        ]
        ext = rec.get("external_ref")
        if ext:
            rows.append(("external_ref", f"{ext.get('uri')} (availability: {ext.get('availability')})"))
    elif rtype == "sol:record/decision":
        rows += [
            ("decision_type", rec.get("decision_type", "")),
            ("candidates", ", ".join(rec.get("candidates", []))),
            ("selected", rec.get("selected", "")),
            ("decision_rule", rec.get("decision_rule", "")),
            ("made_by", rec.get("made_by", "")),
            ("based_on", ", ".join(rec.get("based_on", []))),
        ]
    elif rtype == "sol:record/verification":
        rows += [
            ("target", rec.get("target", "")),
            ("method", rec.get("method", "")),
            ("result", rec.get("result", "")),
            ("performed_by", rec.get("performed_by", "")),
        ]
    elif rtype == "sol:record/failure":
        rows += [
            ("run_id", rec.get("run_id", "")),
            ("failed_cell", rec.get("failed_cell", "")),
            ("error_type", rec.get("error_type", "")),
            ("message", rec.get("message", "")),
        ]
    elif rtype == "sol:record/proposal":
        rows += [
            ("base_commit", rec.get("base_commit", "")),
            ("rationale", rec.get("rationale", "")),
            ("predicted_invalidations", ", ".join(rec.get("predicted_invalidations", []))),
        ]
    elif rtype == "sol:record/review":
        rows += [
            ("proposal_id", rec.get("proposal_id", "")),
            ("review_status", rec.get("review_status", "")),
            ("reviewed_by", rec.get("reviewed_by", "")),
        ]
    elif rtype == "sol:record/task":
        rows += [
            ("task_type", rec.get("task_type", "")),
            ("instruction_ref", rec.get("instruction_ref", "")),
        ]
    return rows


def render_html(a: Artifact, source_commit: str | None = None) -> str:
    """Script-disabled HTML render of committed state (section 47)."""
    commit = source_commit or a.manifest.get("current_commit") or ""
    title = a.manifest.get("title", a.manifest.get("artifact_id", "Sol artifact"))
    esc = html.escape
    p: list[str] = []
    p.append("<!DOCTYPE html>")
    p.append('<html lang="en"><head><meta charset="utf-8">')
    p.append(f"<title>{esc(str(title))} — Sol artifact</title>")
    p.append(f"<style>{CSS}</style></head><body>")
    p.append("<header>")
    p.append(f"<h1>{esc(str(title))}</h1>")
    p.append(
        f'<p class="meta">Sol artifact <code>{esc(str(a.manifest.get("artifact_id", "")))}</code> '
        f'· sol_version {esc(str(a.manifest.get("sol_version", "")))} '
        f'· source commit: <code>{esc(str(commit))}</code></p>'
    )
    p.append("</header>")

    disc = _disclosures(a)
    if disc:
        p.append('<section id="disclosures" class="disclosures"><h2>Disclosures</h2><ul>')
        for d in disc:
            p.append(f"<li><strong>[{esc(d['kind'])}]</strong> {esc(d['text'])}</li>")
        p.append("</ul></section>")

    # Cells, in committed execution order.
    p.append('<section id="cells"><h2>Cells</h2>')
    for cid in _cell_order(a):
        cell = a.cells[cid]
        ctype = cell.get("cell_type", "")
        p.append(f'<div class="cell {esc(ctype.split("/")[-1])}">')
        p.append(f'<p class="type">{esc(ctype)} · {esc(cid)}</p>')
        if cell.get("title"):
            p.append(f"<h3>{esc(str(cell['title']))}</h3>")
        p.append(f"<p>{esc(str(cell.get('summary', '')))}</p>")
        if ctype == "sol:cell/anchor":
            ref = cell.get("anchors_record", "")
            rec = a.record(ref)
            p.append(
                f'<div class="anchor"><p><strong>Anchor:</strong> places '
                f'<code>{esc(ref)}</code> into the narrative. '
                f"{esc(str(rec.get('summary', ''))) if rec else ''}</p></div>"
            )
        elif ctype == "sol:cell/gate":
            p.append(f"<p>Gate on decision <code>{esc(str(cell.get('decision_ref', '')))}</code></p>")
        elif ctype == "sol:cell/display":
            dref = cell.get("display_ref", "")
            b = _binding_for(a, dref) if dref else None
            if b:
                p.append(f"<p>Displays <code>{esc(dref)}</code> → <code>{esc(b.get('object_ref', ''))}</code></p>")
            else:
                p.append(f"<p>Displays <code>{esc(dref)}</code> (no valid binding)</p>")
        if isinstance(cell.get("source"), str) and cell.get("source"):
            lang = cell.get("language", "")
            p.append(f'<pre><code>{esc(cell["source"])}</code></pre>')
        if cell.get("produces"):
            names = ", ".join(f"{x.get('name')} ({x.get('mime_type')})" for x in cell["produces"])
            p.append(f"<p>Output contract: {esc(names)}</p>")
        p.append("</div>")
    p.append("</section>")

    # Semantic records.
    p.append('<section id="records"><h2>Semantic records</h2>')
    for rec in sorted(a.records.values(), key=lambda r: r.get("record_id", "")):
        p.append("<div class='cell'>")
        p.append("<table>")
        for k, v in _record_fields(rec):
            p.append(f"<tr><th>{esc(k)}</th><td>{esc(str(v))}</td></tr>")
        p.append("</table></div>")
    p.append("</section>")

    # Runs.
    p.append('<section id="runs"><h2>Runs</h2>')
    for run in sorted(a.runs.values(), key=lambda r: r.get("run_id", "")):
        p.append("<div class='cell'>")
        p.append("<table>")
        rows = [
            ("run_id", run.get("run_id", "")),
            ("status", run.get("status", "")),
            ("source_commit", run.get("source_commit", "")),
            ("result_commit", run.get("result_commit") or "(none)"),
            ("actor", run.get("actor_id", "")),
            ("environment", run.get("environment_id", "")),
            ("cells_executed", ", ".join(run.get("cells_executed", []))),
        ]
        for b in run.get("output_bindings", []):
            rows.append(("binding", f"{b.get('named_output')} → {b.get('object_ref')} ({b.get('status', 'valid')})"))
        for k, v in rows:
            p.append(f"<tr><th>{esc(k)}</th><td>{esc(str(v))}</td></tr>")
        p.append("</table></div>")
    p.append("</section>")

    p.append("<footer>")
    p.append(
        f"<p>Rendered view derived from commit <code>{esc(str(commit))}</code>. "
        "This view is a derived product (RFC section 47); the artifact is the "
        "source of truth (INV-01). Rendered without code execution (INV-07).</p>"
    )
    p.append("</footer></body></html>")
    return "\n".join(p)


def render_markdown(a: Artifact, source_commit: str | None = None) -> str:
    """Markdown render of committed state (section 47)."""
    commit = source_commit or a.manifest.get("current_commit") or ""
    title = a.manifest.get("title", a.manifest.get("artifact_id", "Sol artifact"))
    p: list[str] = []
    p.append(f"# {title}")
    p.append("")
    p.append(
        f"Sol artifact `{a.manifest.get('artifact_id', '')}` · sol_version "
        f"{a.manifest.get('sol_version', '')} · **source commit: `{commit}`**"
    )
    p.append("")

    disc = _disclosures(a)
    if disc:
        p.append("## Disclosures")
        p.append("")
        for d in disc:
            p.append(f"- **[{d['kind']}]** {d['text']}")
        p.append("")

    p.append("## Cells")
    p.append("")
    for cid in _cell_order(a):
        cell = a.cells[cid]
        p.append(f"### {cid} ({cell.get('cell_type', '')})")
        p.append("")
        if cell.get("title"):
            p.append(f"*{cell['title']}*")
            p.append("")
        p.append(cell.get("summary", ""))
        p.append("")
        if cell.get("cell_type") == "sol:cell/anchor":
            p.append(f"> Anchor: places `{cell.get('anchors_record', '')}` into the narrative.")
            p.append("")
        if isinstance(cell.get("source"), str) and cell.get("source"):
            p.append("```")
            p.append(cell["source"])
            p.append("```")
            p.append("")
        if cell.get("produces"):
            names = ", ".join(f"{x.get('name')} ({x.get('mime_type')})" for x in cell["produces"])
            p.append(f"Output contract: {names}")
            p.append("")

    p.append("## Semantic records")
    p.append("")
    for rec in sorted(a.records.values(), key=lambda r: r.get("record_id", "")):
        p.append(f"### {rec.get('record_id', '')} ({rec.get('record_type', '')})")
        p.append("")
        for k, v in _record_fields(rec):
            p.append(f"- **{k}**: {v}")
        p.append("")

    p.append("## Runs")
    p.append("")
    for run in sorted(a.runs.values(), key=lambda r: r.get("run_id", "")):
        p.append(f"### {run.get('run_id', '')} — {run.get('status', '')}")
        p.append("")
        p.append(f"- source_commit: `{run.get('source_commit', '')}` → result_commit: `{run.get('result_commit') or '(none)'}`")
        p.append(f"- actor: `{run.get('actor_id', '')}` · environment: `{run.get('environment_id', '')}`")
        p.append(f"- cells_executed: {', '.join(run.get('cells_executed', []))}")
        for b in run.get("output_bindings", []):
            p.append(f"- binding: `{b.get('named_output')}` → `{b.get('object_ref')}` ({b.get('status', 'valid')})")
        p.append("")

    p.append("---")
    p.append(
        f"Rendered view derived from commit `{commit}`. This view is a derived "
        "product (RFC section 47); the artifact is the source of truth (INV-01). "
        "Rendered without code execution (INV-07)."
    )
    return "\n".join(p)


def render(a: Artifact, target: str, source_commit: str | None = None) -> str:
    if target == "html":
        return render_html(a, source_commit=source_commit)
    if target == "markdown":
        return render_markdown(a, source_commit=source_commit)
    raise ValueError(f"unsupported render target {target!r} (MVP: html, markdown)")
