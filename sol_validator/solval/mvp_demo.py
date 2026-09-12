"""MVP demonstration driver (RFC-SOL-0001 sections 57/58, Phase 4).

Runs the Phase 4 demonstrations deterministically and records the evidence
under sol_validator/demos/:

  container/   .solnb pack, bounded reads (REQ-014.1/014.2/014.3), integrity
               (REQ-014.4), move test (acceptance criterion 5), direct
               .solnb validation.
  executor/    success run (from GOLD-01) and partial-success run (from
               GOLD-02) with paired failure record (criteria 12/13).
  render/      HTML + Markdown of GOLD-01 at commit_042 (criteria 10/14)
               and a stale-disclosure render of PATH-007 (criterion 20).
  import_demo/ .ipynb import with Q6 classification (criterion 15).

Every produced artifact is validated; the driver fails if any demonstration
artifact carries a diagnostic. Output is deterministic (fixed demo
timestamps; no wall-clock values).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from .container import SolnbContainer, pack
from .executor import Kernel, execute
from .import_ipynb import import_ipynb
from .render import render_html, render_markdown
from .validate import validate_path

HERE = Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus"
DEMOS = HERE / "demos"

METRICS = b"checkpoint,loss,eos_rate\nM0,3.42,0.71\nM200,2.98,0.43\n"
PLOT = b"fake-png-eos-plot"


def _kernel() -> Kernel:
    k = Kernel()
    k.register_source("metrics = compute_metrics(results)", lambda: {"metrics_table": METRICS})
    k.register_cell("cell_015", lambda: {"eos_plot": PLOT})
    return k


def _validate(path: Path) -> list[str]:
    return [d.rule_id for d in validate_path(path)]


def demo_container() -> dict:
    out = DEMOS / "container"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    src = CORPUS / "GOLD-01" / "artifact.sol.d"
    solnb = out / "gold01.solnb"
    pack(src, solnb)

    bounded = {}
    with SolnbContainer(solnb) as c:
        bounded["REQ-014.1_manifest"] = c.bounded_read_bytes(["manifest.json"])
        bounded["REQ-014.2_skeleton"] = c.bounded_read_bytes(["manifest.json", "execution_structure.json"])
        digest = c.object_digests()[0]
        bounded["REQ-014.3_object"] = c.bounded_read_bytes([f"objects/sha256/{digest}"])
        bounded["REQ-014.4_integrity_problems"] = c.verify()
        bounded["objects"] = len(c.object_digests())
        bounded["media_type"] = "application/vnd.sol.notebook"

    # Move test (acceptance criterion 5): copy the container to another
    # directory, unpack, and validate -- required outputs travel with it.
    moved = out / "moved"
    moved.mkdir()
    shutil.copy(solnb, moved / "gold01.solnb")
    from .container import unpack

    unpacked = unpack(moved / "gold01.solnb", moved / "artifact.sol.d")
    result = {
        "container": str(solnb.relative_to(HERE)),
        "container_bytes": solnb.stat().st_size,
        "bounded_reads": bounded,
        "moved_and_unpacked_valid": not _validate(unpacked),
        "direct_solnb_validation": _validate(solnb),
    }
    return result


def demo_executor() -> dict:
    out = DEMOS / "executor"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    k = _kernel()
    success = execute(CORPUS / "GOLD-01" / "artifact.sol.d", k, out / "success" / "artifact.sol.d", confirm=True)
    partial = execute(CORPUS / "GOLD-02" / "artifact.sol.d", k, out / "partial" / "artifact.sol.d", confirm=True)
    return {
        "success": {
            "artifact": str((out / "success" / "artifact.sol.d").relative_to(HERE)),
            "run_id": success.run_id,
            "status": success.status,
            "cells_executed": success.cells_executed,
            "bindings": success.output_bindings,
            "commit_id": success.commit_id,
            "validates": not success.diagnostics,
        },
        "partial": {
            "artifact": str((out / "partial" / "artifact.sol.d").relative_to(HERE)),
            "run_id": partial.run_id,
            "status": partial.status,
            "cells_executed": partial.cells_executed,
            "bindings": partial.output_bindings,
            "failure_record": {
                "record_id": partial.failure_record["record_id"],
                "run_id": partial.failure_record["run_id"],
                "failed_cell": partial.failure_record["failed_cell"],
                "error_type": partial.failure_record["error_type"],
            },
            "commit_id": partial.commit_id,
            "validates": not partial.diagnostics,
        },
    }


def demo_render() -> dict:
    out = DEMOS / "render"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    from .model import Artifact

    gold = Artifact.load(CORPUS / "GOLD-01" / "artifact.sol.d")
    (out / "gold01_commit_042.html").write_text(render_html(gold, source_commit="commit_042"), encoding="utf-8")
    (out / "gold01_commit_042.md").write_text(render_markdown(gold, source_commit="commit_042"), encoding="utf-8")

    # Stale-disclosure render (criterion 20): PATH-007 carries a stale claim
    # that the committed render includes without disclosure; the renderer
    # must visibly disclose it.
    stale = Artifact.load(CORPUS / "PATH-007" / "artifact.sol.d")
    stale_html = render_html(stale, source_commit="commit_042")
    (out / "stale_disclosure.html").write_text(stale_html, encoding="utf-8")
    disclosed = "Disclosures" in stale_html and "needs_reverification" in stale_html
    no_scripts = "<script" not in stale_html.lower() and "<script" not in (out / "gold01_commit_042.html").read_text().lower()
    return {
        "gold01_html": str((out / "gold01_commit_042.html").relative_to(HERE)),
        "gold01_markdown": str((out / "gold01_commit_042.md").relative_to(HERE)),
        "stale_disclosure_html": str((out / "stale_disclosure.html").relative_to(HERE)),
        "stale_disclosed": disclosed,
        "no_script_tags": no_scripts,
        "source_commit_identified": "commit_042" in (out / "gold01_commit_042.html").read_text(),
    }


def demo_import() -> dict:
    res = import_ipynb(DEMOS / "import_demo" / "sample.ipynb", DEMOS / "import_demo" / "imported" / "artifact.sol.d")
    res["artifact"] = str(Path(res["artifact"]).relative_to(HERE))
    return res


def main(argv: list[str] | None = None) -> int:
    if DEMOS.exists():
        shutil.rmtree(DEMOS)
    DEMOS.mkdir(parents=True)

    # The demo notebook is a stable input shipped in demo_inputs/ (outside
    # the wiped demos/ evidence directory).
    (DEMOS / "import_demo").mkdir(parents=True)
    shutil.copy(HERE / "demo_inputs" / "sample.ipynb", DEMOS / "import_demo" / "sample.ipynb")

    report: dict = {
        "generated_by": "solval.mvp_demo (RFC-SOL-0001 Phase 4 MVP demonstration)",
        "spec": "RFC-SOL-0001 v0.1.0-draft (frozen)",
        "deterministic": True,
    }
    report["container"] = demo_container()
    report["executor"] = demo_executor()
    report["render"] = demo_render()
    report["import"] = demo_import()

    # Every demonstration artifact must validate cleanly.
    checks = {
        "container.moved_unpacked": report["container"]["moved_and_unpacked_valid"],
        "container.direct_solnb": report["container"]["direct_solnb_validation"] == [],
        "container.integrity": report["container"]["bounded_reads"]["REQ-014.4_integrity_problems"] == [],
        "executor.success_validates": report["executor"]["success"]["validates"],
        "executor.partial_validates": report["executor"]["partial"]["validates"],
        "executor.partial_status": report["executor"]["partial"]["status"] == "partial_success",
        "executor.partial_failure_same_run": report["executor"]["partial"]["failure_record"]["run_id"] == f"run:{report['executor']['partial']['run_id']}",
        "render.stale_disclosed": report["render"]["stale_disclosed"],
        "render.no_script_tags": report["render"]["no_script_tags"],
        "render.source_commit_identified": report["render"]["source_commit_identified"],
        "import.validates": report["import"]["diagnostics"] == [],
        "import.provenance_incomplete": report["import"]["provenance_status"] == "incomplete",
    }
    report["checks"] = checks
    (DEMOS / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    ok = all(checks.values())
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"\n{sum(checks.values())}/{len(checks)} demonstration checks passed; evidence in {DEMOS.relative_to(HERE.parent)}/")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
