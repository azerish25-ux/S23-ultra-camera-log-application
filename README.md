# S23Log — Phase 1 Camera Capability Probe

Native Android capability probe for the Samsung Galaxy S23 Ultra and other Camera2 devices.

This first milestone deliberately measures the hardware/API surface before attempting a custom log capture pipeline. It reports what the phone exposes to third-party Android apps, including:

- Camera IDs and logical/physical camera relationships
- Camera2 hardware levels and capabilities
- RAW_SENSOR / RAW10 / RAW12 / YUV / PRIVATE output sizes
- ISO and exposure ranges, CFA pattern, white/black levels
- Focal lengths, apertures, manual focus, stabilization and FPS ranges
- Android dynamic-range and color-space profiles
- HEVC encoders, Main10-class profiles, P010 input and 4K/8K support

The report is shown on-device, saved in app-private storage, and shareable as text.

## Requirements

- JDK 17+
- Android SDK API 36
- Android Build Tools 36.0.0
- Gradle 9.6

## Build

```bash
gradle :app:assembleDebug
```

For the prepared ChatGPT Linux environment, the same project can also be built fully offline:

```bash
GRADLE_USER_HOME=/root/.gradle gradle --offline :app:assembleDebug
```

The optional local Maven mirror under `/opt/android-offline-maven` is used only when it exists; normal developer machines resolve dependencies from Google Maven and Maven Central.

## Current milestone

Phase 1 is a capability-probe foundation. It does not yet record custom log video. The probe output from a physical Galaxy S23 Ultra is intended to drive the next milestone: live Camera2 preview, manual controls, lens selection, and the highest-quality 10-bit/RAW-derived capture path the device actually exposes.
