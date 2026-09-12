# Quality report

- Report directory: `reports/quality/20260911-171048`
- Created: `2026-09-11 17:10:49 +0000`

This report embeds the last 160 lines from each check log. Full logs live next to this file.


---

## Invocation: `fast`

- Timestamp: `2026-09-11 17:10:49 +0000`
- Process: `7177`
- Scope: `recursive`
- Coverage source: `src`

### Python targets

- `src`

### Test targets

- ``

### Check table

| Check | Result | Exit code | Log |
|---|---:|---:|---|
| `ruff` | PASSED | 0 | `171048-7177-01-ruff.log` |
| `ty` | PASSED | 0 | `171048-7177-02-ty.log` |

### Findings

### ruff: PASSED, exit 0

#### `171048-7177-01-ruff.log`

Last 160 lines:

    Command: uv run ruff check --fix src
    All checks passed!

### ty: PASSED, exit 0

#### `171048-7177-02-ty.log`

Last 160 lines:

    Command: uv run ty check src
    All checks passed!

### Invocation result

All checks passed in this invocation.
