# P018 — capture state reducer

Active phase: **P018**. Entry gate: **P017**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for the capture-state reducer. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Pure reducer, event log format, and race replay tests.

Machine-readable fixture:
[P018_IMPLEMENT_THE_CAPTURE_STATE_REDUCER.json](P018_IMPLEMENT_THE_CAPTURE_STATE_REDUCER.json)
(`schemaVersion` 1, `phase` `P018`, `logId`
`s23-capture-reducer-record-stop-race`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

`scripts/gates/p018_implement_the_capture_state_reducer.py` is Python 3
standard library only. It does not open a camera, a socket, or a device file.

## Method

The reducer uses eight states, in order: `opening`, `preview`, `configuring`,
`starting`, `recording`, `stopping`, `finalizing`, and `failure`. Every
asynchronous event carries a positive integer `generation` and an `owner`.
A callback whose generation or owner is not current is stale: it does not
change recording, the attached surface, the timer, or the indicator. It may
release only resources still tagged with that stale generation.

`recording`, `timerRunning`, and `indicatorActive` become true together only
when a `first_sample_ack` arrives in `starting` before Stop. A
`first_video_sample` is not that acknowledgement. Neither a sample nor an
`audio_format` callback starts the timer.

## Fixture

Record followed immediately by Stop, with a delayed first video sample and a
delayed audio format callback.

The fixture log is nine events on generation `1`, owner `session-a`, take
`take-1`:

1. `camera_opened`
2. `configure`
3. `configured`
4. `record` — enters `starting`; recording stays false
5. `stop` — enters `stopping` before any sample is acknowledged
6. `first_video_sample` (`delayed` true)
7. `audio_format` (`delayed` true)
8. `finalize`
9. `finalized`

## Oracle

The state never returns from `stopping` to `recording`. The retained output
for this race is:

| Field | Value |
| --- | --- |
| `takeId` | `take-1` |
| `status` | `stopped_before_first_sample` |
| `recordingEntered` | false |
| `lateFirstVideoSample` | true |
| `lateAudioFormat` | true |
| `returnedToRecording` | false |

`assess` returns `caseId` `P018`, decision `terminal_accurate`, and
`preservedResults` that still list the take and every event identity.
`terminal_accurate` is a host-fixture label. It is not `qualified` and not
`allowed`.

## Event log

Each applied or ignored event is appended in order. Fields, in order: `seq`,
`type`, `generation`, `owner`, `delayed`, `stale`, `applied`.

## Deliberate mutation

Allow any first-frame callback to set `recording=true`.

`replay(..., mutant=True)` and `assess(..., mutant=True)` implement that
control only so the test can see it fail. The default reducer does not. A
mutant replay is decision `rejected` with claim `first-frame-sets-recording`.
The take id and the event identities stay in `preservedResults`. A test walks
the production reducer across the delayed first video sample and fails if
`recording` becomes true or the state leaves `stopping`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p018*.py' -v
```

The phase test loads the fixture, checks the record/stop race, checks that
the timer waits for first-sample acknowledgement, checks a stale generation
release, and checks that the mutant is rejected. Case modules
`scripts/gates/p018_tc01.py` through `p018_tc08.py` are separate host
evaluators. Their results are not device measurements.

## Non-claims

- This fixture is not a live S23 probe. No physical Galaxy S23 was opened.
  No sensor, lens, firmware, session, or on-device recording is qualified.
- A passing host command does not certify fixed cadence, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, cinema-camera equivalence, endurance,
  or thermal behavior.
- `terminal_accurate`, `stale_ignored`, `withheld`, `observation_recorded`,
  `terminal`, `recovered`, `monitoring_reduced`, `enqueued`, `stopped`,
  `draft_separated`, `clean_unchanged`, and `idempotent` are software labels
  for this host fixture. None of them means `qualified` or `allowed` for a
  physical capture.
- **TC-P018-01 through TC-P018-08 are separate modules.** This note does not
  treat their host decisions as physical qualification. The phase assessor
  does not execute those modules.
- No Android or Kotlin sources were changed.
