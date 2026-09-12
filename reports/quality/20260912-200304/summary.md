# Quality report

- Report directory: `reports/quality/20260912-200304`
- Created: `2026-09-12 20:03:05 +0000`

This report embeds the last 160 lines from each check log. Full logs live next to this file.


---

## Invocation: `fast`

- Timestamp: `2026-09-12 20:03:05 +0000`
- Process: `307447`
- Scope: `recursive`
- Coverage source: `src`

### Python targets

- `src`

### Test targets

- ``

### Check table

| Check | Result | Exit code | Log |
|---|---:|---:|---|
| `ruff` | PASSED | 0 | `200304-307447-01-ruff.log` |
| `ty` | PASSED | 0 | `200304-307447-02-ty.log` |

### Findings

### ruff: PASSED, exit 0

#### `200304-307447-01-ruff.log`

Last 160 lines:

    Command: uv run ruff check --fix src
    All checks passed!

### ty: PASSED, exit 0

#### `200304-307447-02-ty.log`

Last 160 lines:

    Command: uv run ty check src
    All checks passed!

### Invocation result

All checks passed in this invocation.
