# Quality report

- Report directory: `reports/quality/20260911-171023`
- Created: `2026-09-11 17:10:26 +0000`

This report embeds the last 160 lines from each check log. Full logs live next to this file.


---

## Invocation: `fast`

- Timestamp: `2026-09-11 17:10:26 +0000`
- Process: `6825`
- Scope: `recursive`
- Coverage source: `src`

### Python targets

- `src`

### Test targets

- ``

### Check table

| Check | Result | Exit code | Log |
|---|---:|---:|---|
| `ruff` | PASSED | 0 | `171023-6825-01-ruff.log` |
| `ty` | PASSED | 0 | `171023-6825-02-ty.log` |

### Findings

### ruff: PASSED, exit 0

#### `171023-6825-01-ruff.log`

Last 160 lines:

    Command: uv run ruff check --fix src
    All checks passed!

### ty: PASSED, exit 0

#### `171023-6825-02-ty.log`

Last 160 lines:

    Command: uv run ty check src
    All checks passed!

### Invocation result

All checks passed in this invocation.
