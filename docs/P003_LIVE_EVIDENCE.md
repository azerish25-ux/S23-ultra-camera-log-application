# P003 — live attempts and cross-adapter acceptance

The [Master Directive](../MASTER_DIRECTIVE.md) governs this change. Active cases
are **TC-P003-01 through TC-P003-08**, scoped to the live adapter and cross-adapter
report boundaries. Source implementation, local execution, Android execution and
physical qualification are separate. **P004 is not closed by this change.**

## Publication correction

Previously `LiveLogSession` assigned its final `media` reference before checking
whether `partial.renameTo(destination)` succeeded. The failure handler retained
that reference, while the report and UI tested `media != null` to decide whether
to report a saved movie. Failed publication could therefore appear successful.

`LivePublication.publish` now returns a published reference only after a successful
move into a previously absent destination and a nonempty final file. The caller
binds `media` to that result. Failed rename or an existing destination retains the
partial file and an explicit error, without claiming publication or replacing the
earlier file. The test forces the original failure; it is a file-operation test,
not an imaging experiment. The no-overwrite guard is scoped to this single-owner,
UUID-named private-directory workflow, not a cross-process transactional filesystem
or arbitrary power-loss guarantee.

Decoded output, publication and auxiliary report/library updates have independent
results. A failed rename does not erase an actual decode result. Conversely, a
completed decode does not manufacture successful publication. Auxiliary report
failure does not delete a published movie or revoke its publication observation.

## Live attempt producer

`LiveLogSession.testBackend` and `prepare` create unique attempts before their work.
`LiveAttempt` observes the existing operations; it does not replace GPU, camera,
codec or profile implementations. Constructor-injected probe faults exist for
integration tests, not a hidden fallback or a user-selectable fake backend.

The two attempt kinds are deliberately distinct:

- **Backend test:** actual synthetic GPU comparison and encoder/decoder route
  qualification. It does not open a camera, bind a RAW profile or certify a sensor.
- **Camera session:** profile and route validation, actual configuration callback,
  matched/processed RAW frames, submitted/encoded frames, full structural decode,
  publication and application-owner cleanup acknowledgments. Preview without an
  accepted Record request remains preview-only, not a successful recorded take.

The outcome vocabulary remains `passed`, `failed`, `blocked`, `unavailable`,
`not_run` and `inconclusive`. Cancellation is blocked; no qualified backend is
unavailable; query uncertainty is inconclusive; unexpected errors are failures.
Earlier successful observations remain visible, while unreached stages are not run.

Each observation has its exact JSON payload, SHA-256, attempt and source revision.
Context binds the development device/build, source/profile declaration, explicit
crop/reduction, selected backend, requested cadence, focus and consent choices.
Profile input identity is not independent evidence of physical camera possession.

Reports are retained under:

```
files/exports/live-evidence/live-attempt-<uuid>.json
```

**Live attempt reports** on the existing live screen lists the latest 64 files
and supports sharing. Older files are not deleted. The existing backend/movie
sidecars retain the attempt ID and report filename. Checkpoints use the existing
serial diagnostics I/O owner, not per-frame disk writes or a new capture thread.
Exclusive attempt creation protects earlier files. Interrupted writes can leave
incomplete checkpoints; persistence errors are separate from footage operations.
This is not a durable/resumable rendering-job implementation.

## Numerical and scope boundaries

`live-existing-0.9-v1` records existing thresholds; it does not loosen them. GPU
Log RGB error remains at most 0.001 and packed P010 error at most two code values.
The positive and deliberately eight-bit-degraded ramps retain their actual decode
and measurements: mean at most 0.75, peak at most two, at least 600 distinguishable
levels, and colour-patch errors at most 12 codes. A negative-control `passed=false`
flag without failing measurements is rejected. Selected-size and cadence identity
must match the attempted mode.

Full live decoding retains the original relative sensor PTS list, microsecond
units, explicit timestamp domain, frame accounting and signal interpretation.
Normal live recording still **does not retain original RAW pixels**. Therefore:

| Adapter | Permitted report conclusion | Conclusion it cannot inherit |
| --- | --- | --- |
| Capability/ordinary | Advertised/configured/received samples and existing output checks | Full-file decode from a sample decode |
| Saved RAW | Its checked source/profile and every-frame pixel-comparison result | Evidence of an actual live camera session |
| Live backend | Synthetic GPU/codec qualification | Camera acquisition, sensor precision or dynamic range |
| Live camera | Matched source frames and full structural/PTS decode where actually observed | Retained-original-RAW pixel comparison or physical calibration |

`pixelSourceComparison` and `physicalCameraCertified` remain false for this live
adapter. A decoded movie does not establish native 4K/8K, endurance, sensor dynamic
range, colour calibration or cinema-camera equivalence. Existing output limits,
video-only behaviour, RAW queues, stop conditions and numerical policies remain.

`scripts/check_live_evidence.py` independently recomputes hashes, raw outcomes,
measurement policy, frame/timestamp/configuration consistency and publication
identity. It also pairs original sidecars with attempt records. Integration mode
requires named default-backend, injected-fault, rejected-profile and publication
controls; a synthetic report cannot silently stand in for an unrun default worker.
`scripts/check_p003_evidence.py` runs the separate consumers and rejects duplicated
attempt identities, mixed revisions or scope leakage between adapter families.
A passed report-consistency result is not a physical-device acceptance badge.

## Prior CI failure preserved and repaired

Android run **37009381292**, job **110845658342**, at
`826ad1ed5de00efd36393aefa5ecee7b470edc00` passed all 58 connected instrumentation
cases, but later failed the original successful-video evidence check. Its deliberate
no-frame cancellation test had placed a rejected recording sidecar into the
successful-capture corpus.

The test now moves that exact sidecar into `exports/recording-controls` after
checking its rejected state, zero frames and matching attempt ID. Its bytes are
preserved. The independent recording consumer requires the negative control and
still rejects a false success. **`scripts/check_evidence.py` is unchanged.** A new
host regression proves it still rejects that rejected sidecar in the positive
corpus. Replaying the original artifact with only that member relocated passes
both gates for 25 recordings and 28 attempts; this is replay, not new Android work.
The original rejected payload is retained in
[evidence/P003-recording-rejected-control.json](evidence/P003-recording-rejected-control.json).

## Verification and reproduction

```sh
python3 scripts/verify_master_directive.py
python3 scripts/verify_research_contract.py --expected-head "$(git rev-parse HEAD)"
python3 scripts/verify_repository_continuity.py --expected-head "$(git rev-parse HEAD)"
python3 -m unittest discover -s scripts/tests -p 'test_live_evidence.py' -v
python3 -m unittest discover -s scripts/tests -v
python3 -m unittest discover -s docs/master-directive/reference -p test_reference.py -v
kotlinc app/src/main/java/com/s23log/probe/core/DevelopmentEvidence.kt \
  app/src/main/java/com/s23log/probe/core/LiveEvidence.kt scripts/live_evidence_smoke.kt \
  -include-runtime -d /tmp/live-evidence.jar
java -jar /tmp/live-evidence.jar
kotlinc app/src/main/java/com/s23log/probe/core/LivePublication.kt \
  scripts/live_publication_smoke.kt -include-runtime -d /tmp/live-publication.jar
java -jar /tmp/live-publication.jar
```

The pure live classifier runner has 61 assertions; the publication runner has
eight. There are 47 live/cross-adapter Python methods, plus the separate regression
for the original success corpus. Three deliberate consumer defects are detected
by assertions and restored; original failing and passing logs are retained.

`LiveAttemptTest` adds 17 JVM/JUnit methods. Four new Android test methods exercise
the default live-backend worker, cancellation/IO faults, synthetic/stale-profile
rejection before camera access, and real private-file rename/collision handling.
The existing native-screen test checks the new export button. These are authored
checks, not executed Android evidence until a pinned Android CI run confirms them.
Local API type-checking with generated/AndroidX/JUnit signature stubs is compile-only;
it is neither execution of those tests nor a Gradle APK build.

The existing emulator script continues its independent video/audio/colour/RAW
checks and now also executes the live and cross-adapter consumers. Missing reports,
controls or adapter families fail the integration gate. All actual outcomes and
unavailable routes must be retained in the final evidence, not filtered into green.

## Retained local execution record

[Local host verification](evidence/P003-live-host-verification.json) names the
source commit, actual results, prior failed CI/replay and separate native gates.
Its checksummed archive retains the original failed-publication assertion,
consumer mutants, individual authored receipt cases, green logs and compile-only
signature inputs. The current host suite executed **249 tests**, including the
47 live/cross-adapter tests and the positive-corpus regression; all passed.
These counts do not include the unexecuted new Android/JUnit tests.

## Remaining acceptance

This implements the selected live/reporting changes and cross-adapter checks.
New exact-commit Android build/JVM/emulator execution and real exported-report
validation remain separate acceptance requirements. Physical S23 camera operation
and calibration are not available in this host environment. Inspect and repair
any runtime failure before closing P003; only then proceed to P004's formal baseline.
