#!/usr/bin/env bash
set -euo pipefail
SDK="${ANDROID_HOME:-${RUNNER_TEMP:-/tmp}/s23log-android-sdk}"
export ANDROID_HOME="$SDK" ANDROID_SDK_ROOT="$SDK"
TOOLS="$SDK/cmdline-tools/latest/bin"
if [[ ! -x "$TOOLS/sdkmanager" ]]; then
  stage=$(mktemp -d)
  trap 'rm -rf "$stage"' EXIT
  curl -fL --retry 3 https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip -o "$stage/tools.zip"
  echo "4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583  $stage/tools.zip" | sha256sum -c -
  unzip -q "$stage/tools.zip" -d "$stage/tools"
  mkdir -p "$SDK/cmdline-tools"
  mv "$stage/tools/cmdline-tools" "$SDK/cmdline-tools/latest"
fi
# yes exits with SIGPIPE after sdkmanager stops reading; only sdkmanager's exit code is decisive.
set +e
yes | "$TOOLS/sdkmanager" --sdk_root="$SDK" --licenses > /dev/null
license_status=${PIPESTATUS[1]}
set -e
[[ "$license_status" == 0 ]]
"$TOOLS/sdkmanager" --sdk_root="$SDK" 'platforms;android-36' 'build-tools;36.0.0' platform-tools
if [[ "${1:-}" == emulator ]]; then
  "$TOOLS/sdkmanager" --sdk_root="$SDK" emulator 'system-images;android-36;google_apis;x86_64'
fi
if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "ANDROID_HOME=$SDK" >> "$GITHUB_ENV"
  echo "ANDROID_SDK_ROOT=$SDK" >> "$GITHUB_ENV"
  printf '%s\n' "$TOOLS" "$SDK/platform-tools" "$SDK/emulator" >> "$GITHUB_PATH"
fi
