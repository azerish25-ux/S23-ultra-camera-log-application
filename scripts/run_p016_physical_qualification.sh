#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/run_p016_physical_qualification.sh [--serial SERIAL] [--run-id ID] [--marker-ready]

Runs the opt-in P016 instrumentation on one attached Samsung Galaxy S23 Ultra,
pulls the exact evidence bundle, and performs independent FFmpeg/ffprobe host
validation. The marker page is docs/p016-marker.html.

--marker-ready skips the interactive marker prompt. Use it only after the marker
page is already open, full-screen, audible, and ready to start.
EOF
}

serial=""
run_id=""
marker_ready=false
while (($#)); do
  case "$1" in
    --serial)
      [[ $# -ge 2 ]] || { usage >&2; exit 64; }
      serial=$2; shift 2 ;;
    --run-id)
      [[ $# -ge 2 ]] || { usage >&2; exit 64; }
      run_id=$2; shift 2 ;;
    --marker-ready)
      marker_ready=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 64 ;;
  esac
done

for command in git adb python3 ffmpeg ffprobe timeout; do
  command -v "$command" >/dev/null || { echo "Required command is unavailable: $command" >&2; exit 69; }
done
[[ -x ./gradlew && -f app/build.gradle.kts ]] || {
  echo "Run this script from the repository root." >&2
  exit 69
}
[[ "$(git branch --show-current)" == "main" ]] || {
  echo "P016 must run from the existing main branch." >&2
  exit 65
}
[[ -z "$(git status --porcelain)" ]] || {
  echo "The working tree must be clean so the APK and evidence bind to one exact commit." >&2
  git status --short >&2
  exit 65
}
revision=$(git rev-parse HEAD)
[[ $revision =~ ^[0-9a-f]{40}$ ]] || { echo "Cannot resolve an exact source revision." >&2; exit 65; }

adb_cmd=(adb)
if [[ -n "$serial" ]]; then adb_cmd+=(-s "$serial"); fi
if [[ -z "$serial" ]]; then
  mapfile -t devices < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  [[ ${#devices[@]} -eq 1 ]] || {
    echo "Exactly one authorized Android device is required; found ${#devices[@]}. Use --serial when needed." >&2
    exit 69
  }
  serial=${devices[0]}
  adb_cmd=(adb -s "$serial")
fi
"${adb_cmd[@]}" get-state | grep -qx device || { echo "ADB device is not ready: $serial" >&2; exit 69; }
manufacturer=$("${adb_cmd[@]}" shell getprop ro.product.manufacturer | tr -d '\r')
model=$("${adb_cmd[@]}" shell getprop ro.product.model | tr -d '\r')
fingerprint=$("${adb_cmd[@]}" shell getprop ro.build.fingerprint | tr -d '\r')
[[ ${manufacturer,,} == samsung && $model =~ ^SM-S918[A-Za-z0-9-]*$ ]] || {
  echo "P016 requires a Samsung Galaxy S23 Ultra (SM-S918*); connected: $manufacturer $model" >&2
  exit 65
}
[[ -n "$fingerprint" ]] || { echo "Connected device has no build fingerprint." >&2; exit 65; }

if [[ -z "$run_id" ]]; then
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-${revision:0:12}"
fi
[[ $run_id =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$ ]] || { echo "Invalid --run-id." >&2; exit 64; }
host_root="evidence/p016/$run_id"
[[ ! -e "$host_root" ]] || { echo "Evidence destination already exists: $host_root" >&2; exit 65; }
mkdir -p "$host_root"

cleanup_failure() {
  status=$?
  if [[ $status -ne 0 ]]; then
    {
      echo "serial=$serial"
      echo "manufacturer=$manufacturer"
      echo "model=$model"
      echo "fingerprint=$fingerprint"
      echo "revision=$revision"
      echo "run_id=$run_id"
    } > "$host_root/failed-run-context.txt"
    timeout 20 "${adb_cmd[@]}" logcat -d > "$host_root/logcat-failure.txt" 2>/dev/null || true
  fi
  exit "$status"
}
trap cleanup_failure EXIT

printf 'P016 device: %s %s (%s)\n' "$manufacturer" "$model" "$serial"
printf 'P016 revision: %s\n' "$revision"
printf 'Building APKs bound to the exact revision...\n'
./gradlew --no-daemon -PsourceRevision="$revision" \
  :app:assembleDebug :app:assembleDebugAndroidTest

main_apk=app/build/outputs/apk/debug/app-debug.apk
test_apk=app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
[[ -s "$main_apk" && -s "$test_apk" ]] || { echo "Expected APK output is missing." >&2; exit 70; }
"${adb_cmd[@]}" install -r -t "$main_apk" >/dev/null
"${adb_cmd[@]}" install -r -t "$test_apk" >/dev/null
"${adb_cmd[@]}" shell input keyevent 82 >/dev/null || true

marker_path="$(pwd)/docs/p016-marker.html"
if ! $marker_ready; then
  cat <<EOF

Open this file on a SECOND display/device:
  file://$marker_path

Set that display's brightness and speaker volume high. Frame the entire marker
screen with the S23 Ultra. Press START on the marker page, then immediately
press Enter here. Do not move either device until the 75-second sequence ends.
EOF
  read -r
else
  echo "Marker readiness was asserted with --marker-ready."
fi

instrumentation_log="$host_root/instrumentation.txt"
set +e
timeout 300 "${adb_cmd[@]}" shell am instrument -w -r \
  -e class com.s23log.probe.P016PhysicalQualificationTest \
  -e p016Physical true \
  -e p016RunId "$run_id" \
  -e p016MarkerProtocol p016-flash-tone-v1 \
  -e p016MarkerReady true \
  com.s23log.probe.test/androidx.test.runner.AndroidJUnitRunner | tee "$instrumentation_log"
instrumentation_status=${PIPESTATUS[0]}
set -e
[[ $instrumentation_status -eq 0 ]] || {
  echo "Physical instrumentation failed with status $instrumentation_status." >&2
  exit "$instrumentation_status"
}
grep -Eq '^OK \(1 test\)' "$instrumentation_log" || {
  echo "Instrumentation did not report one completed physical test." >&2
  exit 1
}

remote_root="/sdcard/Android/data/com.s23log.probe/files/p016/$run_id"
"${adb_cmd[@]}" shell test -f "$remote_root/device-capture.json" || {
  echo "The phone did not publish the expected P016 bundle." >&2
  exit 1
}
"${adb_cmd[@]}" pull "$remote_root/." "$host_root" >/dev/null
for required in device-capture.json capture.mp4 recording-validation.json recording-attempt.json; do
  [[ -s "$host_root/$required" ]] || { echo "Missing pulled evidence: $required" >&2; exit 1; }
done
{
  echo "serial=$serial"
  echo "manufacturer=$manufacturer"
  echo "model=$model"
  echo "fingerprint=$fingerprint"
  echo "revision=$revision"
  echo "run_id=$run_id"
  echo "pulled_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$host_root/host-device-binding.txt"

set +e
python3 scripts/p016_physical_qualification.py "$host_root" \
  --expected-revision "$revision" \
  --output "$host_root/p016-qualification.json" | tee "$host_root/p016-qualification.stdout.json"
qualification_status=${PIPESTATUS[0]}
set -e

trap - EXIT
case "$qualification_status" in
  0)
    echo "P016 exact 60-second configuration slice qualified."
    echo "Evidence: $host_root/p016-qualification.json"
    exit 0 ;;
  2)
    echo "P016 footage was retained, but cadence has a warning; exact configuration qualification is withheld." >&2
    echo "Evidence: $host_root/p016-qualification.json" >&2
    exit 2 ;;
  *)
    echo "P016 physical qualification was withheld. Inspect $host_root." >&2
    exit "$qualification_status" ;;
esac
