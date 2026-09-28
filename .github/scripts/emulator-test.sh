#!/usr/bin/env bash
set -euo pipefail
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
mkdir -p evidence/emulator
if ! command -v ffprobe >/dev/null; then sudo apt-get update -qq; sudo apt-get install -y ffmpeg; fi
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
emulator -avd s23log_ci -no-window -no-audio -no-boot-anim -no-snapshot -no-metrics -gpu swiftshader -accel "$accel" -camera-back emulated -camera-front emulated > evidence/emulator/emulator.log 2>&1 &
emulator_pid=$!
cleanup() {
  set +e
  adb logcat -d > evidence/emulator/logcat.txt
  adb shell screencap -p /sdcard/s23log-ci.png
  adb pull /sdcard/s23log-ci.png evidence/emulator/screen.png
  adb exec-out run-as com.s23log.probe tar -cf - files/exports shared_prefs > evidence/emulator/app-evidence.tar
  adb pull /sdcard/Movies/S23Log evidence/emulator/videos
  adb emu kill
  kill "$emulator_pid" 2>/dev/null
}
trap cleanup EXIT
booted=0
for _ in $(seq 1 180); do
  if [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; then booted=1; break; fi
  kill -0 "$emulator_pid" || { tail -100 evidence/emulator/emulator.log; exit 1; }
  sleep 3
done
[[ "$booted" == 1 ]] || { echo 'Emulator did not finish booting'; exit 1; }
adb shell input keyevent 82
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
./gradlew --no-daemon :app:connectedDebugAndroidTest
adb pull /sdcard/Movies/S23Log evidence/emulator/videos
python3 scripts/check_video.py evidence/emulator/videos --min-duration 1 > evidence/emulator/ffprobe.json
# Independently require a 60-second container, not only the in-app duration assertion.
python3 - <<'PY_CHECK'
import json
from pathlib import Path
clips = json.loads(Path("evidence/emulator/ffprobe.json").read_text())
assert len(clips) >= 12, "Expected ten cycles, one long recording, and one lifecycle recording"
assert max(clip["durationSeconds"] for clip in clips) >= 60, "No 60-second recording was produced"
PY_CHECK
adb shell am start -W -n com.s23log.probe/.MainActivity
sleep 3
adb exec-out screencap -p > evidence/emulator/camera-screen.png
