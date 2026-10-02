package com.s23log.probe.diagnostics

import com.s23log.probe.core.*
import com.s23log.probe.develop.DevelopmentAttempt
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.util.UUID

/** An observer, not a camera/codec/storage owner. Production schedules checkpoints on a serial IO
 * executor; no per-frame file IO is added to capture callbacks. A crash leaves an incomplete report. */
class RecordingAttempt(
    directory: File, val sourceRevision: String, context: JSONObject,
    private val write: (File, String) -> Unit,
    private val schedule: (() -> Unit) -> Unit = { it() },
    private val onPersistenceFailure: (String) -> Unit = {},
    val id: String = UUID.randomUUID().toString()
) {
    init { require(id.matches(Regex("[0-9a-f-]{36}"))) }
    val file = File(directory, "recording-attempt-$id.json")
    private val context = JSONObject(context.toString())
    private val records = linkedMapOf<RecordingStage, RecordingStageResult>()
    private val observations = linkedMapOf<String, String>()
    private val captureErrors = mutableListOf<String>()
    private val reportErrors = mutableListOf<String>()
    private val startedAt = Instant.now().toString()
    private var endedAt: String? = null
    private var closed = false
    // Only the serial writer touches owned. It never claims or overwrites a pre-existing report.
    private var owned = false
    @Volatile var persistenceError: String? = null; private set

    @Synchronized fun start() = checkpoint()

    @Synchronized fun observe(stage: RecordingStage, outcome: DevelopmentOutcome, reason: String, facts: JSONObject = JSONObject()) {
        if (closed || stage in records) return // Late callbacks cannot resurrect or rewrite a completed stage.
        var actual = outcome
        var detail = reason
        if (outcome == DevelopmentOutcome.PASSED) try {
            validateFacts(stage, facts, context)
            if (stage == RecordingStage.PUBLICATION) {
                val checked = requireNotNull(records[RecordingStage.OUTPUT]) { "No checked output" }
                require(checked.outcome == DevelopmentOutcome.PASSED) { "No checked output to publish" }
                val raw = JSONObject(requireNotNull(observations[checked.evidenceRef]))
                require(same(raw.getJSONObject("facts").getJSONObject("verification").getJSONObject("mediaIdentity"),
                    facts.getJSONObject("mediaIdentity"))) { "Published media differs from checked output" }
            }
        }
        catch (error: Exception) { actual = DevelopmentOutcome.FAILED; detail = "Evidence contract: ${error.message}" }
        val ref = "${stage.wire}-observation"
        val payload = JSONObject().put("attemptId", id).put("sourceRevision", sourceRevision)
            .put("stage", stage.wire).put("facts", JSONObject(facts.toString())).toString()
        observations[ref] = payload
        records[stage] = RecordingStageResult(stage, actual, detail, sourceRevision, ref, DevelopmentAttempt.hash(payload),
            listOf(DevelopmentCheck("observed-operation", actual, detail)))
        checkpoint()
    }

    /** Reports a checked planner subset; a missing snapshot never manufactures advertised evidence. */
    @Synchronized fun advertised(plan: JSONObject?) {
        if (plan != null) observe(RecordingStage.ADVERTISED, DevelopmentOutcome.PASSED,
            "Retained selected candidate from CameraCatalog.plan; advertisement only", JSONObject().put("plan", plan))
    }

    @Synchronized fun noteReportError(message: String) { if (!closed && reportErrors.size < 8) reportErrors += message }
    @Synchronized fun close(errors: List<String> = emptyList()) {
        if (closed) return
        captureErrors += errors.filter { it.isNotBlank() }.take(16)
        closed = true; endedAt = Instant.now().toString(); checkpoint()
    }

    @Synchronized fun snapshot(): JSONObject {
        val all = RecordingStage.values().map { stage -> records[stage] ?: RecordingStageResult(stage,
            DevelopmentOutcome.NOT_RUN, when (stage) {
                RecordingStage.FULL_DECODE -> "The existing on-device verifier decodes samples, not every video/audio frame"
                RecordingStage.PHYSICAL -> "No independent physical-device qualification protocol"
                RecordingStage.AUDIO -> if (context.optInt("audioChannels") == 0) "Explicit video-only request" else "No completed audio observation"
                else -> "No completed observation for this stage"
            }, sourceRevision, null, null, emptyList()) }
        val verdict = RecordingClassifier.classify(all, sourceRevision, closed, context.optInt("audioChannels") > 0, captureErrors)
        return JSONObject().put("schemaVersion", 1).put("kind", "ordinary-recording-evidence").put("attemptId", id)
            .put("sourceRevision", sourceRevision).put("startedAt", startedAt).put("endedAt", endedAt ?: JSONObject.NULL)
            .put("closed", closed).put("context", JSONObject(context.toString())).put("policy", policy())
            .put("stages", JSONArray(all.map { r -> JSONObject().put("stage", r.stage.wire).put("outcome", r.outcome.wire)
                .put("reason", r.reason).put("sourceRevision", r.sourceRevision).put("evidenceRef", r.evidenceRef ?: JSONObject.NULL)
                .put("evidenceSha256", r.evidenceSha256 ?: JSONObject.NULL).put("checks", JSONArray(r.checks.map { c ->
                    JSONObject().put("id", c.id).put("outcome", c.outcome.wire).put("reason", c.reason) })) }))
            .put("observations", JSONObject(observations as Map<*, *>)).put("captureErrors", JSONArray(captureErrors))
            .put("reportErrors", JSONArray(reportErrors)).put("persistenceError", persistenceError ?: JSONObject.NULL)
            .put("classification", JSONObject().put("outputChecked", verdict.outputChecked).put("publishedOutput", verdict.publishedOutput)
                .put("recordingSucceeded", verdict.recordingSucceeded).put("retainedForRecovery", verdict.retainedForRecovery)
                .put("fullDecodeVerified", false).put("physicalCameraCertified", false).put("issues", JSONArray(verdict.issues)))
            .put("physicalCameraCertified", false).put("customLog", false)
    }

    /** Reporting must not alter a successful camera or media operation. */
    fun safely(observation: () -> Unit) {
        try { observation() } catch (error: Exception) {
            noteReportError("Observation failed: ${error.javaClass.simpleName}: ${error.message}")
            persistenceFailure(error)
        }
    }

    private fun checkpoint() {
        try {
            val payload = snapshot().toString(2)
            schedule {
            try {
                val parent = requireNotNull(file.parentFile)
                check(parent.isDirectory || parent.mkdirs()) { "Recording-attempt directory unavailable" }
                if (!owned) { check(file.createNewFile()) { "Attempt already exists; refusing overwrite" }; owned = true }
                write(file, payload)
            } catch (error: Exception) { persistenceFailure(error) }
            }
        } catch (error: Exception) { persistenceFailure(error) }
    }
    private fun persistenceFailure(error: Exception) {
        val first = persistenceError == null
        persistenceError = error.message ?: error.javaClass.simpleName
        if (first) runCatching { onPersistenceFailure(requireNotNull(persistenceError)) }
    }

    companion object {
        fun policy(): JSONObject = JSONObject().put("id", "ordinary-recording-existing-0.9-v1")
            .put("durationUnit", "us").put("durationDomain", "muxed_video_presentation_timestamp_span")
            .put("decodeScope", "all_packets_and_sample_decode_not_full_decode")
            .put("cadenceToleranceFraction", .03).put("cadenceMinimumSpanUs", 2_000_000)
            .put("cadenceWarningPreservesFootage", true)
        fun same(a: Any?, b: Any?): Boolean = when {
            a is JSONObject && b is JSONObject -> a.keys().asSequence().toSet() == b.keys().asSequence().toSet() &&
                a.keys().asSequence().all { same(a.get(it), b.get(it)) }
            a is JSONArray && b is JSONArray -> a.length() == b.length() && (0 until a.length()).all { same(a.get(it), b.get(it)) }
            a is Number && b is Number -> a.toString().toBigDecimal().compareTo(b.toString().toBigDecimal()) == 0
            else -> a == b
        }
        private fun integer(j: JSONObject, key: String): Long {
            val value = j.get(key)
            require(value is Byte || value is Short || value is Int || value is Long) { "Expected integer $key" }
            return (value as Number).toLong()
        }
        private fun yes(j: JSONObject, key: String) { require(j.get(key) == true) { "Missing true $key" } }
        private fun identity(j: JSONObject) {
            require(j.getString("algorithm") == "SHA-256" && j.getString("sha256").matches(Regex("[0-9a-f]{64}")))
            require(integer(j, "byteCount") > 0) { "Empty media identity" }
        }
        fun validateFacts(stage: RecordingStage, facts: JSONObject, context: JSONObject) {
            val mode = context.getJSONObject("selectedMode")
            val channels = integer(context, "audioChannels").toInt()
            when (stage) {
                RecordingStage.ADVERTISED -> {
                    val p = facts.getJSONObject("plan")
                    require(p.getString("kind") == "recording-mode-plan" && p.getString("evidence") == "advertised_only")
                    require(p.getString("generatedAt").isNotBlank() && p.getString("reportId").isNotBlank())
                    require(same(p.getJSONObject("device"), context.getJSONObject("device"))) { "Capability device/revision mismatch" }
                    val requested = context.getJSONObject("requested")
                    require(same(p.get("logicalCamera"), requested.opt("logicalCamera")) &&
                        same(p.get("physicalCamera"), requested.opt("physicalCamera"))) { "Capability camera route mismatch" }
                    val candidates = p.getJSONObject("plan").getJSONArray("candidates")
                    require(candidates.length() == 1 && same(candidates.getJSONObject(0), mode)) { "Capability mode mismatch" }
                }
                RecordingStage.PREPARATION -> {
                    yes(facts, "surfaceInputCreated"); yes(facts, "encoderStarted")
                    require(facts.getString("encoder") == mode.getString("encoder"))
                    require(integer(facts, "audioChannels") == channels.toLong())
                }
                RecordingStage.CONFIGURED -> { yes(facts, "cameraSessionCallback"); yes(facts, "repeatingRequestSubmitted") }
                RecordingStage.ENCODED -> {
                    val written = integer(facts, "writtenSamples")
                    require(written > 0 && integer(facts, "receivedSamples") >= written)
                    require(integer(facts, "sampleSpanUs") >= 0 && facts.getString("durationUnit") == "us" &&
                        facts.getString("durationDomain") == "muxed_video_presentation_timestamp_span")
                }
                RecordingStage.AUDIO -> {
                    require(channels in 1..2 && integer(facts, "channels") == channels.toLong())
                    require(integer(facts, "writtenSamples") > 0 && integer(facts, "sampleRate") == 48_000L)
                }
                RecordingStage.OUTPUT -> {
                    val v = facts.getJSONObject("verification")
                    require(v.getString("mime") == mode.getString("mime") && integer(v, "width") == integer(mode, "width") &&
                        integer(v, "height") == integer(mode, "height") && integer(v, "requestedFps") == integer(mode, "fps"))
                    require(integer(v, "samples") >= 2 && integer(v, "encodedBytes") > 0 && integer(v, "sampleSpanUs") > 0)
                    require(facts.getString("durationUnit") == "us" && facts.getString("durationDomain") == "muxed_video_presentation_timestamp_span")
                    yes(v, "firstSyncFrameDecoded"); identity(v.getJSONObject("mediaIdentity"))
                    require(v.get("audioRequested") == (channels > 0) && integer(v, "audioTrackCount") == if (channels > 0) 1L else 0L)
                    yes(v, "nominalFpsIsNotSustainedRateProof"); yes(v, "cadenceWarningPreservesFootage")
                    require(v.get("cadenceToleranceFraction") is Number && v.getDouble("cadenceToleranceFraction") == .03 &&
                        integer(v, "cadenceMinimumSpanUs") == 2_000_000L)
                    if (mode.getString("dynamicRange") == "HLG10") {
                        require(integer(v, "lumaBitDepth") == 10L && integer(v, "chromaBitDepth") == 10L)
                        require(integer(v, "colorStandard") == 6L && integer(v, "colorTransfer") == 7L && integer(v, "colorRange") == 2L)
                    }
                    if (channels > 0) {
                        yes(v, "firstAudioPcmDecoded")
                        val audio = v.getJSONObject("audio")
                        require(audio.getString("mime") == "audio/mp4a-latm" && audio.getString("profile") == "AAC-LC")
                        require(integer(audio, "channels") == channels.toLong() && integer(audio, "sampleRate") == 48_000L && integer(audio, "samples") >= 2)
                    }
                    require(facts.getString("decodeScope") == "all_packets_and_sample_decode_not_full_decode")
                }
                RecordingStage.PUBLICATION -> { require(facts.getString("uri").startsWith("content://")); identity(facts.getJSONObject("mediaIdentity")) }
                RecordingStage.RETENTION -> { require(facts.getString("uri").startsWith("content://") && integer(facts, "byteCount") > 0) }
                RecordingStage.FULL_DECODE, RecordingStage.PHYSICAL -> error("Independent protocol not provided by this adapter")
            }
        }
    }
}
