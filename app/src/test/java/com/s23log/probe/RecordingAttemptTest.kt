package com.s23log.probe

import com.s23log.probe.core.*
import com.s23log.probe.diagnostics.RecordingAttempt
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.After
import org.junit.Test
import java.io.File
import java.nio.file.Files

/** Actual producer and existing finalizer; numerical facts are authored fixtures, not camera evidence. */
class RecordingAttemptTest {
    private val root = Files.createTempDirectory("recording-evidence-test").toFile()
    private val revision = "a".repeat(40)
    @After fun clean() { root.deleteRecursively() }
    private fun context(channels: Int = 0) = JSONObject().put("device", JSONObject().put("appCommit", revision).put("fingerprint", "host-fixture"))
        .put("requested", JSONObject().put("logicalCamera", "0").put("physicalCamera", JSONObject.NULL))
        .put("selectedMode", JSONObject().put("key", "fixture").put("width", 1920).put("height", 1080).put("fps", 30)
            .put("bitrate", 8_000_000).put("mime", "video/avc").put("dynamicRange", "SDR").put("encoder", "fixture-codec"))
        .put("audioChannels", channels).put("audioMode", listOf("OFF", "MONO", "STEREO")[channels])
    private fun identity() = JSONObject().put("algorithm", "SHA-256").put("sha256", "b".repeat(64)).put("byteCount", 3000)
    private fun verification(channels: Int = 0) = JSONObject().put("mime", "video/avc").put("width", 1920).put("height", 1080)
        .put("requestedFps", 30).put("samples", 31).put("encodedBytes", 3000).put("sampleSpanUs", 1_000_000)
        .put("audioRequested", channels > 0).put("audioTrackCount", if (channels > 0) 1 else 0)
        .put("firstSyncFrameDecoded", true).put("mediaIdentity", identity()).put("nominalFpsIsNotSustainedRateProof", true)
        .put("cadenceWarningPreservesFootage", true).put("cadenceToleranceFraction", .03).put("cadenceMinimumSpanUs", 2_000_000)
        .also { if (channels > 0) it.put("firstAudioPcmDecoded", true).put("audio", JSONObject().put("mime", "audio/mp4a-latm")
            .put("profile", "AAC-LC").put("sampleRate", 48000).put("channels", channels).put("samples", 47)) }
    private fun output(channels: Int = 0) = JSONObject().put("verification", verification(channels)).put("durationUnit", "us")
        .put("durationDomain", "muxed_video_presentation_timestamp_span").put("decodeScope", "all_packets_and_sample_decode_not_full_decode")
    private fun attempt(channels: Int = 0) = RecordingAttempt(root, revision, context(channels), { f, data -> f.writeText(data) }).also { it.start() }
    private fun base(a: RecordingAttempt, channels: Int = 0) {
        a.observe(RecordingStage.PREPARATION, DevelopmentOutcome.PASSED, "prepared", JSONObject().put("encoder", "fixture-codec")
            .put("surfaceInputCreated", true).put("encoderStarted", true).put("audioChannels", channels))
        a.observe(RecordingStage.CONFIGURED, DevelopmentOutcome.PASSED, "configured", JSONObject().put("cameraSessionCallback", true).put("repeatingRequestSubmitted", true))
        a.observe(RecordingStage.ENCODED, DevelopmentOutcome.PASSED, "written", JSONObject().put("receivedSamples", 31).put("writtenSamples", 31)
            .put("sampleSpanUs", 1_000_000).put("durationUnit", "us").put("durationDomain", "muxed_video_presentation_timestamp_span"))
    }
    private fun publish(a: RecordingAttempt) = a.observe(RecordingStage.PUBLICATION, DevelopmentOutcome.PASSED, "published",
        JSONObject().put("uri", "content://fixture/output").put("mediaIdentity", identity()))
    private fun verdict(a: RecordingAttempt) = a.snapshot().getJSONObject("classification")
    private fun stage(a: RecordingAttempt, name: String): JSONObject {
        val rows = a.snapshot().getJSONArray("stages")
        return (0 until rows.length()).map(rows::getJSONObject).first { it.getString("stage") == name }
    }
    @Test fun successfulOutputRetainsExactObservationBytesAndLimitedDecodeScope() {
        val a = attempt(); base(a); a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "checked", output()); publish(a); a.close()
        assertTrue(verdict(a).getBoolean("recordingSucceeded")); assertFalse(verdict(a).getBoolean("fullDecodeVerified"))
        assertFalse(verdict(a).getBoolean("physicalCameraCertified")); assertEquals(a.id, JSONObject(a.file.readText()).getString("attemptId"))
        val r = stage(a, "output_validation"); val raw = a.snapshot().getJSONObject("observations").getString(r.getString("evidenceRef"))
        assertEquals(r.getString("evidenceSha256"), com.s23log.probe.develop.DevelopmentAttempt.hash(raw))
    }
    @Test fun configuredAdvertisementWithoutFramesIsNotARecording() {
        val a = attempt(); a.observe(RecordingStage.CONFIGURED, DevelopmentOutcome.PASSED, "configured",
            JSONObject().put("cameraSessionCallback", true).put("repeatingRequestSubmitted", true)); a.close()
        assertEquals("passed", stage(a, "configured").getString("outcome")); assertFalse(verdict(a).getBoolean("recordingSucceeded"))
    }
    @Test fun failedSetupRemainsFailedWithoutFabricatedSession() {
        val a = attempt(); a.observe(RecordingStage.PREPARATION, DevelopmentOutcome.FAILED, "Codec creation failed"); a.close(listOf("Codec creation failed"))
        assertEquals("failed", stage(a, "preparation").getString("outcome")); assertEquals("not_run", stage(a, "configured").getString("outcome"))
    }
    @Test fun absentAudioCannotBecomeAVideoOnlySuccess() {
        val a = attempt(2); base(a, 2); a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "checked", output(2)); publish(a); a.close()
        assertTrue(verdict(a).getBoolean("outputChecked")); assertFalse(verdict(a).getBoolean("recordingSucceeded"))
    }
    @Test fun failedVerificationPreservesBytesThroughExistingFinalizer() {
        val media = File(root, "source.mp4").apply { writeText("nonempty recovery fixture") }
        val a = attempt(); base(a)
        val result = VideoFinalizer.finish<JSONObject, String>(31, null,
            verify = { a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.FAILED, "Decode failed"); error("Decode failed") },
            publish = { error("Must not publish") }, retain = { reason ->
                a.observe(RecordingStage.RETENTION, DevelopmentOutcome.PASSED, reason, JSONObject().put("uri", "content://fixture/recovery").put("byteCount", media.length())); "retained"
            }, discardEmpty = { error("Must not delete nonempty media") }, saveReport = {})
        a.close(result.errors); assertEquals(VideoDisposition.RECOVERABLE, result.disposition)
        assertTrue(verdict(a).getBoolean("retainedForRecovery")); assertEquals("nonempty recovery fixture", media.readText())
    }
    @Test fun publicationFailureRetainsNarrowerOutputCheck() {
        val a = attempt(); base(a); a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "checked", output())
        a.observe(RecordingStage.PUBLICATION, DevelopmentOutcome.FAILED, "Provider failed")
        a.observe(RecordingStage.RETENTION, DevelopmentOutcome.PASSED, "Retained privately", JSONObject().put("uri", "content://fixture/recovery").put("byteCount", 3000))
        a.close(listOf("Publication failed")); assertTrue(verdict(a).getBoolean("outputChecked")); assertTrue(verdict(a).getBoolean("retainedForRecovery"))
        assertFalse(verdict(a).getBoolean("publishedOutput"))
    }
    @Test fun reportFailureCannotDeleteMediaOrUndoSuccessfulPublication() {
        val a = attempt(); base(a); a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "checked", output()); publish(a)
        a.noteReportError("Sidecar unavailable"); a.close(); assertTrue(verdict(a).getBoolean("recordingSucceeded"))
        assertEquals("Sidecar unavailable", a.snapshot().getJSONArray("reportErrors").getString(0))
    }
    @Test fun reportIdentityCollisionNeverOverwritesPreviousAttempt() {
        val first = attempt(); first.close(); val bytes = first.file.readBytes()
        val second = RecordingAttempt(root, revision, context(), { f, data -> f.writeText(data) }, id = first.id)
        second.start(); second.close(); assertNotNull(second.persistenceError); assertArrayEquals(bytes, first.file.readBytes())
    }
    @Test fun writerFailureIsSeparateFromProducerState() {
        val a = RecordingAttempt(root, revision, context(), { _, _ -> error("Disk fault") }); a.start(); base(a); a.close()
        assertEquals("Disk fault", a.persistenceError); assertTrue(a.snapshot().getBoolean("closed"))
        assertEquals("passed", stage(a, "configured").getString("outcome"))
    }
    @Test fun asynchronousWritesStayOffCallbackAndRetainFinalSnapshot() {
        val queue = mutableListOf<() -> Unit>()
        val a = RecordingAttempt(root, revision, context(), { f, data -> f.writeText(data) }, schedule = { queue += it })
        a.start(); base(a); a.close(); assertFalse(a.file.exists()); queue.forEach { it() }
        assertTrue(JSONObject(a.file.readText()).getBoolean("closed"))
    }
    @Test fun lateCallbacksCannotRewriteAClosedAttempt() {
        val a = attempt(); a.close(); val bytes = a.file.readBytes()
        a.observe(RecordingStage.CONFIGURED, DevelopmentOutcome.PASSED, "Late callback", JSONObject().put("cameraSessionCallback", true).put("repeatingRequestSubmitted", true))
        assertArrayEquals(bytes, a.file.readBytes())
    }
    @Test fun evidenceUnitsAndThresholdsAreCheckedByTheProducer() {
        val a = attempt(); base(a); val f = output(); f.getJSONObject("verification").put("cadenceToleranceFraction", .5)
        a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "Falsely green", f); a.close()
        assertEquals("failed", stage(a, "output_validation").getString("outcome")); assertFalse(verdict(a).getBoolean("outputChecked"))
    }
    @Test fun wrongCapabilityRouteCannotBeLabelledAdvertised() {
        val a = attempt(); val p = JSONObject().put("kind", "recording-mode-plan").put("evidence", "advertised_only")
            .put("generatedAt", "fixture").put("reportId", "fixture").put("device", context().getJSONObject("device"))
            .put("logicalCamera", "wrong").put("physicalCamera", JSONObject.NULL)
            .put("plan", JSONObject().put("candidates", org.json.JSONArray().put(context().getJSONObject("selectedMode"))))
        a.advertised(p); a.close(); assertEquals("failed", stage(a, "advertised").getString("outcome"))
    }
    @Test fun attemptsDoNotMutateTheirContextOrObservedInputs() {
        val source = context(); val a = RecordingAttempt(root, revision, source, { f, d -> f.writeText(d) });a.start()
        source.getJSONObject("selectedMode").put("width", 7680)
        assertEquals(1920, a.snapshot().getJSONObject("context").getJSONObject("selectedMode").getInt("width"))
    }
    @Test fun mismatchedPublishedBytesCannotInheritAnOutputCheck() {
        val a = attempt(); base(a); a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "checked", output())
        val wrong = output().getJSONObject("verification").getJSONObject("mediaIdentity").put("sha256", "f".repeat(64))
        a.observe(RecordingStage.PUBLICATION, DevelopmentOutcome.PASSED, "false identity", JSONObject().put("uri", "content://fixture/output").put("mediaIdentity", wrong))
        a.close(); assertTrue(verdict(a).getBoolean("outputChecked")); assertFalse(verdict(a).getBoolean("publishedOutput"))
        assertEquals("failed", stage(a, "publication").getString("outcome"))
    }
    @Test fun observationExceptionCannotChangeSuccessfulPublicationResult() {
        val a = attempt(); base(a); a.observe(RecordingStage.OUTPUT, DevelopmentOutcome.PASSED, "checked", output())
        val result = "content://fixture/retained-published-video".also { a.safely { error("Auxiliary observer failure") } }
        assertEquals("content://fixture/retained-published-video", result)
        a.close(); assertEquals("Auxiliary observer failure", a.persistenceError)
        assertTrue(a.snapshot().getJSONArray("reportErrors").getString(0).contains("Auxiliary observer failure"))
    }

}
