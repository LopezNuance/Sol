#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/quality.sh
#   scripts/quality.sh fast
#   scripts/quality.sh test coverage security deps dead
#   scripts/quality.sh ci
#   scripts/quality.sh --top-only fast
#   scripts/quality.sh --recursive ci
#
# Default behavior is recursive/project-wide.
# Use --top-only to restrict source-file checks to top-level *.py files.

SCOPE="${QUALITY_SCOPE:-recursive}"
MODES=()

usage() {
  cat <<'EOF'
Usage:
  scripts/quality.sh [--top-only|--recursive] [mode ...]

Modes:
  fast       Ruff autofix + ty
  test       pytest
  coverage   coverage run + coverage report
  security   bandit + pip-audit
  deps       deptry
  dead       vulture
  prepush    ruff check + ty + pytest
  ci         ruff check + ty + coverage + bandit + deptry + pip-audit
  all        everything, including vulture

Scope:
  --recursive  Recursive/project-wide behavior. This is the default.
  --top-only   Only top-level *.py files for source-file checks.

Environment:
  QUALITY_SCOPE=top|recursive
  QUALITY_REPORT_DIR=reports/quality/custom-run
  QUALITY_SUMMARY_LINES=160
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --top-only)
      SCOPE="top"
      shift
      ;;
    --recursive)
      SCOPE="recursive"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      MODES+=("$1")
      shift
      ;;
  esac
done

if [ "${#MODES[@]}" -eq 0 ]; then
  MODES=(fast)
fi

case "$SCOPE" in
  top|recursive)
    ;;
  *)
    echo "Unknown scope: $SCOPE"
    echo "Use --top-only, --recursive, or QUALITY_SCOPE=top|recursive."
    exit 1
    ;;
esac

STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_ROOT="reports/quality"
REPORT_DIR="${QUALITY_REPORT_DIR:-$REPORT_ROOT/$STAMP}"
LATEST_DIR="$REPORT_ROOT/latest"
SUMMARY_LINES="${QUALITY_SUMMARY_LINES:-160}"
FAILURES=0

CHECK_NAMES=()
CHECK_RESULTS=()
CHECK_EXITCODES=()
CHECK_LOGS=()

mkdir -p "$REPORT_DIR"
mkdir -p "$REPORT_ROOT"

INVOCATION_ID="$(date +%H%M%S)-$$"
CHECK_COUNTER=0
NEXT_LOG_FILE=""

discover_python_targets() {
  if [ "$SCOPE" = "top" ]; then
    find . \
      -maxdepth 1 \
      -type f \
      -name '*.py' \
      -printf '%P\n' \
      | sort
    return 0
  fi

  local targets=()

  local candidate
  for candidate in src tests test app apps lib scripts; do
    if [ -d "$candidate" ] && find "$candidate" -type f -name '*.py' -print -quit | grep -q .; then
      targets+=("$candidate")
    fi
  done

  while IFS= read -r file; do
    targets+=("$file")
  done < <(
    find . \
      -maxdepth 1 \
      -type f \
      -name '*.py' \
      -printf '%P\n' \
      | sort
  )

  if [ "${#targets[@]}" -eq 0 ]; then
    while IFS= read -r dir; do
      targets+=("$dir")
    done < <(
      find . \
        -mindepth 2 \
        -type f \
        -name '*.py' \
        -not -path './.git/*' \
        -not -path './.venv/*' \
        -not -path './venv/*' \
        -not -path './env/*' \
        -not -path './.tox/*' \
        -not -path './.nox/*' \
        -not -path './build/*' \
        -not -path './dist/*' \
        -not -path './reports/*' \
        -not -path './htmlcov/*' \
        -not -path './node_modules/*' \
        -printf '%h\n' \
        | sed 's#^\./##' \
        | awk -F/ '{print $1}' \
        | sort -u
    )
  fi

  printf '%s\n' "${targets[@]}"
}

discover_test_targets() {
  if [ "$SCOPE" = "top" ]; then
    find . \
      -maxdepth 1 \
      -type f \
      \( -name 'test_*.py' -o -name '*_test.py' \) \
      -printf '%P\n' \
      | sort
    return 0
  fi

  local targets=()

  if [ -d tests ]; then
    targets+=("tests")
  fi

  if [ -d test ]; then
    targets+=("test")
  fi

  while IFS= read -r file; do
    targets+=("$file")
  done < <(
    find . \
      -maxdepth 1 \
      -type f \
      \( -name 'test_*.py' -o -name '*_test.py' \) \
      -printf '%P\n' \
      | sort
  )

  printf '%s\n' "${targets[@]}"
}

discover_coverage_source() {
  if [ "$SCOPE" = "top" ]; then
    echo "."
    return 0
  fi

  if [ -d src ] && find src -type f -name '*.py' -print -quit | grep -q .; then
    echo "src"
  else
    echo "."
  fi
}

readarray -t PYTHON_TARGETS < <(discover_python_targets)
readarray -t TEST_TARGETS < <(discover_test_targets)
COVERAGE_SOURCE="$(discover_coverage_source)"

record_result() {
  local name="$1"
  local result="$2"
  local exitcode="$3"
  local log_file="$4"

  CHECK_NAMES+=("$name")
  CHECK_RESULTS+=("$result")
  CHECK_EXITCODES+=("$exitcode")
  CHECK_LOGS+=("$log_file")
}

next_log_path() {
  local name="$1"

  CHECK_COUNTER=$((CHECK_COUNTER + 1))
  NEXT_LOG_FILE="$REPORT_DIR/$INVOCATION_ID-$(printf '%02d' "$CHECK_COUNTER")-$name.log"
}

run_check() {
  local name="$1"
  shift

  next_log_path "$name"

  local log_file="$NEXT_LOG_FILE"
  local exit_file="${log_file%.log}.exitcode"

  echo
  echo "==> $name"
  echo "Command: $*" | tee "$log_file"

  set +e
  "$@" 2>&1 | tee -a "$log_file"
  local status="${PIPESTATUS[0]}"
  set -e

  echo "$status" > "$exit_file"

  if [ "$status" -ne 0 ]; then
    echo "FAILED: $name exited with $status"
    FAILURES=$((FAILURES + 1))
    record_result "$name" "FAILED" "$status" "$log_file"
  else
    echo "PASSED: $name"
    record_result "$name" "PASSED" "$status" "$log_file"
  fi
}

skip_check() {
  local name="$1"
  local reason="$2"

  next_log_path "$name"

  local log_file="$NEXT_LOG_FILE"
  local exit_file="${log_file%.log}.exitcode"

  echo
  echo "==> $name"
  echo "SKIPPED: $reason" | tee "$log_file"
  echo "0" > "$exit_file"

  record_result "$name" "SKIPPED" "0" "$log_file"
}

run_python_target_check() {
  local name="$1"
  shift

  if [ "${#PYTHON_TARGETS[@]}" -eq 0 ]; then
    skip_check "$name" "No Python files found for scope: $SCOPE."
    return 0
  fi

  run_check "$name" "$@" "${PYTHON_TARGETS[@]}"
}

run_test_check() {
  local name="$1"
  shift

  if [ "${#TEST_TARGETS[@]}" -eq 0 ]; then
    skip_check "$name" "No test files or test directories found for scope: $SCOPE."
    return 0
  fi

  run_check "$name" "$@" "${TEST_TARGETS[@]}"
}

run_coverage_check() {
  if [ "${#TEST_TARGETS[@]}" -eq 0 ]; then
    skip_check coverage-run "No test files or test directories found for scope: $SCOPE."
    skip_check coverage-report "No test files or test directories found for scope: $SCOPE."
    return 0
  fi

  run_check coverage-run uv run coverage run --source="$COVERAGE_SOURCE" -m pytest "${TEST_TARGETS[@]}"

  if [ "$SCOPE" = "top" ] && [ "${#PYTHON_TARGETS[@]}" -gt 0 ]; then
    run_check coverage-report uv run coverage report "${PYTHON_TARGETS[@]}"
  else
    run_check coverage-report uv run coverage report
  fi
}

run_bandit_check() {
  if [ "${#PYTHON_TARGETS[@]}" -eq 0 ]; then
    skip_check bandit "No Python files found for scope: $SCOPE."
    return 0
  fi

  if [ "$SCOPE" = "top" ]; then
    run_check bandit uv run bandit -c pyproject.toml "${PYTHON_TARGETS[@]}"
  else
    run_check bandit uv run bandit -c pyproject.toml -r "${PYTHON_TARGETS[@]}"
  fi
}

run_deps_check() {
  if [ "$SCOPE" = "top" ]; then
    skip_check deptry "Skipped in --top-only scope because deptry is project/dependency-graph oriented."
  else
    run_check deptry uv run deptry .
  fi
}

init_summary_if_needed() {
  local summary="$REPORT_DIR/summary.md"

  if [ ! -f "$summary" ]; then
    {
      echo "# Quality report"
      echo
      echo "- Report directory: \`$REPORT_DIR\`"
      echo "- Created: \`$(date '+%Y-%m-%d %H:%M:%S %z')\`"
      echo
      echo "This report embeds the last $SUMMARY_LINES lines from each check log. Full logs live next to this file."
      echo
    } > "$summary"
  fi
}

append_log_excerpt() {
  local log_file="$1"
  local log_base
  log_base="$(basename "$log_file")"

  echo
  echo "#### \`$log_base\`"
  echo

  if [ ! -s "$log_file" ]; then
    echo "Log file is empty."
    return 0
  fi

  echo "Last $SUMMARY_LINES lines:"
  echo
  tail -n "$SUMMARY_LINES" "$log_file" | sed 's/^/    /'
}

append_summary() {
  local summary="$REPORT_DIR/summary.md"
  init_summary_if_needed

  {
    echo
    echo "---"
    echo
    echo "## Invocation: \`${MODES[*]}\`"
    echo
    echo "- Timestamp: \`$(date '+%Y-%m-%d %H:%M:%S %z')\`"
    echo "- Process: \`$$\`"
    echo "- Scope: \`$SCOPE\`"
    echo "- Coverage source: \`$COVERAGE_SOURCE\`"
    echo
    echo "### Python targets"
    echo

    if [ "${#PYTHON_TARGETS[@]}" -eq 0 ]; then
      echo "No Python targets discovered."
    else
      local target
      for target in "${PYTHON_TARGETS[@]}"; do
        echo "- \`$target\`"
      done
    fi

    echo
    echo "### Test targets"
    echo

    if [ "${#TEST_TARGETS[@]}" -eq 0 ]; then
      echo "No test targets discovered."
    else
      local target
      for target in "${TEST_TARGETS[@]}"; do
        echo "- \`$target\`"
      done
    fi

    echo
    echo "### Check table"
    echo
    echo "| Check | Result | Exit code | Log |"
    echo "|---|---:|---:|---|"

    local i
    for i in "${!CHECK_NAMES[@]}"; do
      local name="${CHECK_NAMES[$i]}"
      local result="${CHECK_RESULTS[$i]}"
      local exitcode="${CHECK_EXITCODES[$i]}"
      local log_file="${CHECK_LOGS[$i]}"
      local log_base
      log_base="$(basename "$log_file")"

      echo "| \`$name\` | $result | $exitcode | \`$log_base\` |"
    done

    echo
    echo "### Findings"

    for i in "${!CHECK_NAMES[@]}"; do
      local name="${CHECK_NAMES[$i]}"
      local result="${CHECK_RESULTS[$i]}"
      local exitcode="${CHECK_EXITCODES[$i]}"
      local log_file="${CHECK_LOGS[$i]}"

      echo
      echo "### $name: $result, exit $exitcode"
      append_log_excerpt "$log_file"
    done

    echo
    echo "### Invocation result"
    echo

    if [ "$FAILURES" -ne 0 ]; then
      echo "$FAILURES check(s) failed in this invocation."
    else
      echo "All checks passed in this invocation."
    fi
  } >> "$summary"
}

finish_reports() {
  append_summary

  if [ "$(dirname "$REPORT_DIR")" = "$REPORT_ROOT" ]; then
    rm -f "$LATEST_DIR"
    ln -s "$(basename "$REPORT_DIR")" "$LATEST_DIR" 2>/dev/null || true
  else
    rm -f "$LATEST_DIR"
    ln -s "$PWD/$REPORT_DIR" "$LATEST_DIR" 2>/dev/null || true
  fi

  echo
  echo "Reports saved to: $REPORT_DIR"
  echo "Summary report: $REPORT_DIR/summary.md"
  echo "Latest reports symlink: $LATEST_DIR"
}

run_mode() {
  local mode="$1"

  case "$mode" in
    fast)
      run_python_target_check ruff uv run ruff check --fix
      run_python_target_check ty uv run ty check
      ;;

    test)
      run_test_check pytest uv run pytest
      ;;

    coverage)
      run_coverage_check
      ;;

    security)
      run_bandit_check
      run_check pip-audit uv run pip-audit
      ;;

    deps)
      run_deps_check
      ;;

    dead)
      run_python_target_check vulture uv run vulture
      ;;

    prepush)
      run_python_target_check ruff uv run ruff check
      run_python_target_check ty uv run ty check
      run_test_check pytest uv run pytest
      ;;

    ci)
      run_python_target_check ruff uv run ruff check
      run_python_target_check ty uv run ty check
      run_coverage_check
      run_bandit_check
      run_deps_check
      run_check pip-audit uv run pip-audit
      ;;

    all)
      run_python_target_check ruff uv run ruff check --fix
      run_python_target_check ty uv run ty check
      run_coverage_check
      run_bandit_check
      run_deps_check
      run_check pip-audit uv run pip-audit
      run_python_target_check vulture uv run vulture
      ;;

    *)
      echo "Unknown mode: $mode"
      echo "Usage: scripts/quality.sh [--top-only|--recursive] [fast|test|coverage|security|deps|dead|prepush|ci|all] [...]"
      FAILURES=$((FAILURES + 1))
      ;;
  esac
}

for mode in "${MODES[@]}"; do
  run_mode "$mode"
done

finish_reports

if [ "$FAILURES" -ne 0 ]; then
  echo
  echo "$FAILURES check(s) failed."
  exit 1
fi

echo
echo "All checks passed."
