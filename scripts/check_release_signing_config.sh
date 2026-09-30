#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
gradle_bin="${GRADLE_BIN:-./gradlew}"
log=$(mktemp)
trap 'rm -f "$log"' EXIT
clean=(env -u S23LOG_RELEASE_STORE_FILE -u S23LOG_RELEASE_STORE_PASSWORD -u S23LOG_RELEASE_KEY_ALIAS -u S23LOG_RELEASE_KEY_PASSWORD)
expect_failure() {
  local expected="$1"; shift
  if "$@" > "$log" 2>&1; then echo "Signing guard unexpectedly accepted an invalid configuration" >&2; exit 1; fi
  if ! grep -Fq "$expected" "$log"; then cat "$log" >&2; echo "Wrong signing-guard failure" >&2; exit 1; fi
}
expect_failure 'release-key configuration is absent' "${clean[@]}" "$gradle_bin" --no-daemon --offline -PrequireReleaseSigning=true help
expect_failure 'Release signing is partially configured' "${clean[@]}" S23LOG_RELEASE_STORE_FILE=/nonexistent/test-only-signing-input "$gradle_bin" --no-daemon --offline help
expect_failure 'requireReleaseSigning must be true or false' "${clean[@]}" "$gradle_bin" --no-daemon --offline -PrequireReleaseSigning=yes help
echo 'Release-signing guards passed: missing, partial and invalid configuration are rejected'
