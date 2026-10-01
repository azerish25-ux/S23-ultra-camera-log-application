#!/usr/bin/env bash
set -euo pipefail
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export ANDROID_SERIAL=emulator-5554
mkdir -p evidence/emulator
{ echo "Host CPUs: $(nproc)"; free -m; if [[ -r /sys/fs/cgroup/cpu.max ]]; then cat /sys/fs/cgroup/cpu.max; fi; } > evidence/emulator/host-resources.txt
if ! command -v ffprobe >/dev/null || ! command -v ffmpeg >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y ffmpeg
fi
printf 'no\n' | avdmanager create avd --force --name s23log_ci --package 'system-images;android-36;google_apis;x86_64'
cat >> "$HOME/.android/avd/s23log_ci.avd/config.ini" <<'AVD'
hw.camera.back=emulated
hw.camera.front=emulated
hw.lcd.width=720
hw.lcd.height=1280
hw.lcd.density=240
hw.ramSize=3072
AVD
accel=off
if [[ -e /dev/kvm ]]; then sudo chmod 666 /dev/kvm; accel=on; fi
emulator -avd s23log_ci -port 5554 -no-window -no-audio -no-boot-anim -no-snapshot -no-metrics -gpu swiftshader -accel "$accel" -camera-back emulated -camera-front emulated > evidence/emulator/emulator.log 2>&1 &
emulator_pid=$!
vmstat_pid=""
if command -v vmstat >/dev/null; then vmstat -t 5 > evidence/emulator/host-vmstat.txt & vmstat_pid=$!; fi
cleanup() {
  local status=$?
  trap - EXIT
  set +e
  # Preserve the real test/validation exit status and never truncate good evidence.
  timeout 20 adb logcat -d > evidence/emulator/logcat.txt
  if [[ ! -s evidence/emulator/app-evidence.tar ]]; then
    timeout 30 adb exec-out run-as com.s23log.probe tar -cf - files/exports shared_prefs > evidence/emulator/app-evidence.partial.tar
  fi
  if [[ "$status" != 0 && ! -d evidence/emulator/videos ]]; then
    # Failed assertions still need the original MP4s for independent packet analysis.
    # Failure evidence is separate and cannot satisfy the normal acceptance checks.
    timeout 45 adb pull /sdcard/Movies/S23Log evidence/emulator/failed-videos
  fi
  timeout 10 adb emu kill
  kill "$emulator_pid" 2>/dev/null
  if [[ -n "$vmstat_pid" ]]; then kill "$vmstat_pid" 2>/dev/null; fi
  exit "$status"
}
trap cleanup EXIT
booted=0
for _ in $(seq 1 180); do
  if [[ "$(timeout 5 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then booted=1; break; fi
  kill -0 "$emulator_pid" || { tail -100 evidence/emulator/emulator.log; exit 1; }
  sleep 3
done
[[ "$booted" == 1 ]] || { echo 'Emulator did not finish booting'; exit 1; }
adb shell input keyevent 82
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
# AGP normally uninstalls both APKs after connected tests, deleting private reports.
# This is the exact BooleanOption name in the pinned AGP 9.4 toolchain.
# The real-denial test runs in its own process: revoking a granted runtime permission
# kills the app, and package-level appops writes are ignored for runtime ops on API 36.
./gradlew --no-daemon -Pandroid.injected.androidTest.leaveApksInstalledAfterRun=true \
  -Pandroid.testInstrumentationRunnerArguments.notClass=com.s23log.probe.AudioPermissionTest :app:connectedDebugAndroidTest
timeout 15 adb shell am force-stop com.s23log.probe
timeout 15 adb shell pm revoke com.s23log.probe android.permission.RECORD_AUDIO
timeout 15 adb shell pm clear-permission-flags com.s23log.probe android.permission.RECORD_AUDIO user-set user-fixed
timeout 240 adb shell am instrument -w -r -e class com.s23log.probe.AudioPermissionTest \
  com.s23log.probe.test/androidx.test.runner.AndroidJUnitRunner | tee evidence/emulator/permission-instrumentation.txt
grep -q '^OK (1 test)' evidence/emulator/permission-instrumentation.txt
timeout 15 adb shell pm path com.s23log.probe | grep '^package:'
timeout 30 adb exec-out run-as com.s23log.probe tar -cf - files/exports shared_prefs > evidence/emulator/app-evidence.tar
[[ -s evidence/emulator/app-evidence.tar ]] || { echo 'Device reports were not preserved'; exit 1; }
# Retry transport only; a complete copy must still pass all recording checks.
python3 scripts/pull_videos.py evidence/emulator/videos
python3 scripts/check_video.py evidence/emulator/videos --min-duration 1 > evidence/emulator/ffprobe.json
python3 scripts/check_evidence.py evidence/emulator/app-evidence.tar evidence/emulator/ffprobe.json --require-audio --require-identity > evidence/emulator/summary.json
python3 scripts/check_timing.py evidence/emulator/app-evidence.tar > evidence/emulator/timing-summary.json
python3 scripts/check_colour.py evidence/emulator/app-evidence.tar > evidence/emulator/colour-summary.json
python3 scripts/check_reference_luts.py evidence/emulator/app-evidence.tar > evidence/emulator/reference-luts-summary.json
timeout 30 adb shell am start -W -n com.s23log.probe/.MainActivity > evidence/emulator/activity-start.txt
# am may return success even when the requested component is absent.
grep -q 'Status: ok' evidence/emulator/activity-start.txt
sleep 3
timeout 20 adb exec-out screencap -p > evidence/emulator/camera-screen.png
python3 - <<'PY_CHECK'
from pathlib import Path
image = Path('evidence/emulator/camera-screen.png').read_bytes()
if not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image) < 100:
    raise SystemExit('Missing or invalid camera screenshot')
PY_CHECK
python3 scripts/check_raw_development.py evidence/emulator/app-evidence.tar > evidence/emulator/raw-development-summary.json
cat evidence/emulator/summary.json
