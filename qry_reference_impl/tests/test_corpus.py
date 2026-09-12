from pathlib import Path
import json
from qryref.validate import validate_case_dir
from qryref.validate_corpus import is_normative

ROOT = Path(__file__).resolve().parents[1]

def test_legacy_supplemental_cases():
    cases = sorted((ROOT / 'corpus' / 'supplemental').glob('QRY-*'))
    assert len(cases) == 69
    for case in cases:
        manifest = json.loads((case / 'manifest.json').read_text())
        expected = set(manifest.get('expected_diagnostics', []))
        got = {d.rule_id for d in validate_case_dir(case, manifest=manifest)}
        if expected:
            assert expected.issubset(got), (case.name, expected, got)
        else:
            assert not got, (case.name, got)

def test_corpus_structure():
    cases = sorted(p.name for p in (ROOT / 'corpus' / 'cases').iterdir() if p.is_dir())
    supp = sorted(p.name for p in (ROOT / 'corpus' / 'supplemental').iterdir() if p.is_dir())
    normative = [n for n in cases if is_normative(n)]
    # All 64 normative cases of the spec (36.1/36.2) are shipped as
    # green case directories (Phases 5-8 unblocked the last five).
    assert len(normative) == 64
    assert len(cases) - len(normative) == 3  # QPATH-044/045/046 (out-of-spec)
    assert len(supp) == 69  # legacy QRY-NNN
    manifest = json.loads((ROOT / 'corpus' / 'manifest.json').read_text())
    assert manifest['schema_version'] == 'qry.corpus.v0.3'
    assert manifest['normative']['cases'] == sorted(normative)
    assert len(manifest['normative']['blocked']) == 0
    assert (len(manifest['normative']['cases'])
            + len(manifest['normative']['blocked']) == 64)
    assert manifest['supplemental']['cases'] == sorted(
        [n for n in cases if not is_normative(n)] + supp)
