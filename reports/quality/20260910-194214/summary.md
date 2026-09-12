# Quality report

- Report directory: `reports/quality/20260910-194214`
- Created: `2026-09-10 19:42:18 +0000`

This report embeds the last 160 lines from each check log. Full logs live next to this file.


---

## Invocation: `fast`

- Timestamp: `2026-09-10 19:42:18 +0000`
- Process: `274613`
- Scope: `recursive`
- Coverage source: `src`

### Python targets

- `src`

### Test targets

- ``

### Check table

| Check | Result | Exit code | Log |
|---|---:|---:|---|
| `ruff` | PASSED | 0 | `194214-274613-01-ruff.log` |
| `ty` | PASSED | 0 | `194214-274613-02-ty.log` |

### Findings

### ruff: PASSED, exit 0

#### `194214-274613-01-ruff.log`

Last 160 lines:

    Command: uv run ruff check --fix src
    All checks passed!

### ty: PASSED, exit 0

#### `194214-274613-02-ty.log`

Last 160 lines:

    Command: uv run ty check src
    All checks passed!

### Invocation result

All checks passed in this invocation.
