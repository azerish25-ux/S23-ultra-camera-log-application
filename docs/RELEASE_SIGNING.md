# Release signing and update acceptance

Development CI builds an installable debug APK and an **unsigned** release APK. A successful release compile is not a production release. Debug keys are not a stable update policy: another build machine can sign with a different debug key, and Android will reject an update over an installed package signed by another key.

Production signing is opt-in and uses an existing owner-controlled Android keystore through these environment variables:

- `S23LOG_RELEASE_STORE_FILE`: path to the keystore, kept outside version control.
- `S23LOG_RELEASE_STORE_PASSWORD`: store password.
- `S23LOG_RELEASE_KEY_ALIAS`: existing signing alias.
- `S23LOG_RELEASE_KEY_PASSWORD`: alias password.

All four must be supplied together. Partial configuration fails rather than silently producing an unsigned artifact. No debug-key fallback exists. The production command is:

```
./gradlew -PrequireReleaseSigning=true :app:assembleRelease
```

That command fails if signing is absent. Passwords must not be put in committed Gradle properties, shell command arguments, source files or screenshots. Keystores/signing folders are ignored by Git as a last-line safeguard, not a substitute for private custody. This repository does not generate a production key, configure hosted secrets or upload a release.

CI exercises the missing, partial and invalid-property branches with `scripts/check_release_signing_config.sh`; it strips signing inputs from those subprocesses. This verifies fail-closed behavior, not an actual production-key signature or signed update.

Before distribution, verify the resulting APK with the SDK's `apksigner verify --verbose --print-certs`, retain the expected public certificate SHA-256 fingerprint in an owner-approved release record, and compare it against the previous installed release. Verify an in-place update with retained settings, capture index, MediaStore videos and app-private recovery material. Increment versionCode for published updates; changing the signing identity can require uninstalling and losing private app data. Export required captures/reports first, and never use uninstall as an automatic workaround.

Actual production-key custody and signed-update validation require the owner's signing material/decision. They are not claimed by unsigned CI or a debug APK. Store publication and licensing/distribution choices are separate from building this repository.
