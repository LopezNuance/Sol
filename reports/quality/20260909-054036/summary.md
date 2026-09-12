# Quality report

- Report directory: `reports/quality/20260909-054036`
- Created: `2026-09-09 05:40:36 +0000`

This report embeds the last 160 lines from each check log. Full logs live next to this file.


---

## Invocation: `fast`

- Timestamp: `2026-09-09 05:40:37 +0000`
- Process: `3513`
- Scope: `recursive`
- Coverage source: `src`

### Python targets

- `src`

### Test targets

- ``

### Check table

| Check | Result | Exit code | Log |
|---|---:|---:|---|
| `ruff` | PASSED | 0 | `054036-3513-01-ruff.log` |
| `ty` | PASSED | 0 | `054036-3513-02-ty.log` |

### Findings

### ruff: PASSED, exit 0

#### `054036-3513-01-ruff.log`

Last 160 lines:

    Command: uv run ruff check --fix src
    All checks passed!

### ty: PASSED, exit 0

#### `054036-3513-02-ty.log`

Last 160 lines:

    Command: uv run ty check src
    All checks passed!

### Invocation result

All checks passed in this invocation.
