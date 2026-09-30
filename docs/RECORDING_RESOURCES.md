# Recording resource protection

Video recording now checks storage before allocating capture resources and samples storage and Android thermal status every two seconds while running. The capture screen shows a bitrate-based remaining-time estimate and the platform thermal category. These are live observations and estimates, not sustained-throughput or temperature certification.

## Storage budget

The policy retains a 64 MiB floor plus thirty seconds of configured video/audio bitrate as headroom. On Android 29+, it also budgets the currently staged file size for the transactional MediaStore publication copy. It uses the smaller available-byte observation from private and primary external app storage. On Android 26–28, the private same-filesystem move does not need a second full-file copy.

The remaining-time estimate accounts for both future staging growth and growing publication debt. It is conservative when the paths use separate filesystems. VBR bursts, competing writers and filesystem changes can still consume space: this is a checked threshold, not an operating-system reservation or a guarantee. Existing recovery/journal guarantees remain necessary.

Missing storage observations prevent startup or request a controlled stop. Crossing the reserve requests the normal bounded audio/video drain, verifies the completed media and attempts publication; nonempty failures retain their existing recovery path. The guard never deletes recorded footage to create space.

## Thermal policy

Android severe-or-higher thermal status prevents startup or requests the same controlled stop. Light/moderate levels remain visible while capture continues. A platform without thermal status is labelled unavailable, not cool or certified. No battery-temperature shortcut substitutes for Android's thermal status, and no physical S23 Ultra thermal pass is claimed.

Validation reports retain the last resource snapshot, minimum observed free bytes and any protection-stop reason. These observations do not imply that a five- or fifteen-minute real-device run passed.

## Orientation and lifecycle

The capture activity locks its current orientation through Starting, Recording and Finalizing, then restores its previous orientation request. Saved state prevents the lock from sticking after a forced activity recreation. This avoids ordinary sensor-driven rotations disrupting a take.

Leaving the activity or forcibly recreating/destroying it still finalizes recording under the existing foreground-only policy. Background recording is not implemented. Process death, power loss and physical device behavior remain separate acceptance tests.

## Checks

`RecordingResourcePolicyTest` covers storage boundaries, unknown observations, publication copy debt, audio/bitrate effects, remaining-time estimates, thermal levels and overflow. The real emulator camera test checks orientation lock/restoration and retained resource-budget evidence after recording. Existing start/stop, permission, recovery, identity, audio and colour tests remain required.

Physical low-storage/overheating behavior and sustained 4K/8K throughput still require an S23 Ultra with its exact firmware and mode configuration.

API contracts: [Android thermal status](https://developer.android.com/reference/android/os/PowerManager#getCurrentThermalStatus()). Storage capacity uses Android `StatFs.availableBytes`.
