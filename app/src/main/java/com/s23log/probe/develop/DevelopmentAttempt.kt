package com.s23log.probe.develop

import com.s23log.probe.core.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.CancellationException

/** An expected unavailable backend, distinct from cancellation and unexpected code/IO failures. */
class DevelopmentUnavailable(message: String, val details: JSONObject = JSONObject()) : IllegalStateException(message)

/** P003 saved-RAW observer. One worker owns an attempt. It never modifies media, profiles or sources.
 * Checkpoints are best-effort: a report failure must not discard useful footage. A crash leaves a
 * closed=false record, not an invented success. This is evidence retention, not a resumable job. */
class DevelopmentAttempt(
    directory: File, val sourceRevision: String, context: JSONObject,
    private val write: (File, String) -> Unit,
    val id: String = UUID.randomUUID().toString()
) {
    init { require(id.matches(Regex("[0-9a-f-]{36}"))) }
    val file = File(directory, "attempt-$id.json")
    private val scope = JSONObject(context.toString())
    private val records = linkedMapOf<DevelopmentStage, DevelopmentStageResult>()
    private val observations = linkedMapOf<String, String>()
    private val failures = mutableListOf<String>()
    private var owned = false
    private var closed = false
    private var active: DevelopmentStage? = null
    private val startedAt = java.time.Instant.now().toString()
    private var endedAt: String? = null
    val persistenceError: String? get() = failures.lastOrNull()
    val retainedReport: File? get() = file.takeIf { owned && it.isFile && it.length() > 0 }

    fun start() { checkpoint() }
    fun context(key: String, value: Any?) {
        check(!closed && !scope.has(key)) { "Attempt context is already bound: $key" }
        scope.put(key, when (value) {
            is JSONObject -> JSONObject(value.toString())
            is JSONArray -> JSONArray(value.toString())
            else -> value ?: JSONObject.NULL
        })
    }

    fun <T> step(stage: DevelopmentStage, operation: (JSONObject) -> T): T {
        check(!closed && active == null && stage !in records && stage !in listOf(DevelopmentStage.ADVERTISED, DevelopmentStage.CONFIGURED, DevelopmentStage.PHYSICAL))
        active = stage
        checkpoint()
        val facts = JSONObject()
        try {
            val value = operation(facts)
            validateObservation(stage, facts, scope)
            record(stage, DevelopmentOutcome.PASSED, "Observed and checked by the saved-RAW producer", facts)
            return value
        } catch (error: Exception) {
            val outcome = when (error) {
                is CancellationException -> DevelopmentOutcome.BLOCKED
                is DevelopmentUnavailable -> DevelopmentOutcome.UNAVAILABLE
                else -> DevelopmentOutcome.FAILED
            }
            facts.put("exception", error.javaClass.simpleName).put("reason", error.message ?: error.javaClass.simpleName)
            if (error is DevelopmentUnavailable) facts.put("unavailableDetails", JSONObject(error.details.toString()))
            record(stage, outcome, error.message ?: error.javaClass.simpleName, facts)
            throw error
        } finally { active = null; checkpoint() }
    }

    private fun record(stage: DevelopmentStage, outcome: DevelopmentOutcome, reason: String, facts: JSONObject) {
        val ref = "${stage.wire}-observation"
        val payload = facts.toString() // Store exact bytes as a string, independent of JSON key ordering on import.
        observations[ref] = payload
        records[stage] = DevelopmentStageResult(stage, outcome, reason, sourceRevision, ref, hash(payload),
            listOf(DevelopmentCheck("producer-contract", outcome, reason)))
    }

    fun finish() { check(active == null); closed = true; endedAt = java.time.Instant.now().toString(); checkpoint() }

    fun snapshot(): JSONObject {
        val all = DevelopmentStage.values().map { stage -> records[stage] ?: DevelopmentStageResult(
            stage, DevelopmentOutcome.NOT_RUN, when (stage) {
                DevelopmentStage.ADVERTISED, DevelopmentStage.CONFIGURED -> "Saved source development does not observe a camera session"
                DevelopmentStage.PHYSICAL -> "No independent physical phone qualification in this attempt"
                else -> if (active == stage) "Operation in progress; no completed result" else "Operation not reached"
            }, sourceRevision, null, null, emptyList()) }
        val result = DevelopmentClassifier.classify(all, sourceRevision, closed)
        val rows = JSONArray()
        all.forEach { r -> rows.put(JSONObject().put("stage", r.stage.wire).put("outcome", r.outcome.wire)
            .put("reason", r.reason).put("sourceRevision", r.sourceRevision).put("evidenceRef", r.evidenceRef ?: JSONObject.NULL)
            .put("evidenceSha256", r.evidenceSha256 ?: JSONObject.NULL).put("checks", JSONArray(r.checks.map {
                JSONObject().put("id", it.id).put("outcome", it.outcome.wire).put("reason", it.reason)
            }))) }
        return JSONObject().put("schemaVersion", 1).put("kind", "saved-raw-development-evidence").put("attemptId", id)
            .put("sourceRevision", sourceRevision).put("startedAt", startedAt).put("endedAt", endedAt ?: JSONObject.NULL)
            .put("closed", closed).put("activeStage", active?.wire ?: JSONObject.NULL).put("context", JSONObject(scope.toString()))
            .put("policy", policy()).put("stages", rows).put("observations", JSONObject(observations as Map<*, *>))
            .put("classification", JSONObject().put("verifiedOutput", result.verifiedOutput).put("publishedOutput", result.publishedOutput)
                .put("physicalCameraCertified", result.physicalCameraCertified).put("issues", JSONArray(result.issues)))
            .put("physicalCameraCertified", false).put("sourceOwnershipIndependentlyVerified", false)
            .put("sourceLineage", "saved_RAW_SENSOR_declaration_not_physical_attestation")
            .put("persistenceErrors", JSONArray(failures))
    }

    private fun checkpoint() {
        try {
            val parent = requireNotNull(file.parentFile)
            check(parent.isDirectory || parent.mkdirs()) { "Attempt report directory unavailable" }
            if (!owned) { check(file.createNewFile()) { "Attempt identity already exists; refusing overwrite" }; owned = true }
            write(file, snapshot().toString(2))
        } catch (error: Exception) {
            if (failures.size < 8) failures += error.message ?: error.javaClass.simpleName
        }
    }

    companion object {
        fun hash(text: String): String = MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        fun policy(): JSONObject = JSONObject().put("id", "saved-raw-existing-0.9-v1")
            .put("codeUnit", "code_value").put("codeDomain", "decoded_P010")
            .put("durationUnit", "ns").put("durationDomain", "source_sensor_timestamp_span")
            .put("positiveMeanLimit", .75).put("positivePeakLimit", 2.0).put("positiveMinimumLevels", 600)
            .put("frameMeanLimit", 4.0).put("framePeakLimit", 64)
        private fun number(j: JSONObject, key: String): Double = RawJson.number(j, key)
        private fun integer(j: JSONObject, key: String): Long = RawJson.integer(j, key)
        private fun yes(j: JSONObject, key: String) { require(j.get(key) == true) { "Missing true $key" } }
        private fun artifact(j: JSONObject) {
            require(j.getString("sha256").matches(Regex("[0-9a-f]{64}"))) { "Missing artifact hash" }
            require(integer(j, "byteCount") > 0 && j.getString("name").isNotBlank()) { "Empty artifact identity" }
        }
        private fun signal(j: JSONObject) {
            yes(j, "fullDecodeVerified")
            require(integer(j, "lumaBitDepth") == 10L && integer(j, "chromaBitDepth") == 10L)
            require(integer(j, "colorPrimariesCode") == 2L && integer(j, "transferCharacteristicsCode") == 2L && integer(j, "matrixCoefficientsCode") == 1L)
        }
        private fun ramp(j: JSONObject): Boolean {
            signal(j)
            require(integer(j, "decodedFrames") == 4L)
            val mean = number(j, "meanCodeError"); val peak = number(j, "maximumCodeError"); val levels = integer(j, "distinctRampLevels")
            require(mean >= 0 && peak >= 0 && levels in 1..877)
            return mean <= .75 && peak <= 2.0 && levels >= 600
        }

        /** Read raw producer facts independently of the stage's proposed passing label. */
        fun validateObservation(stage: DevelopmentStage, facts: JSONObject, context: JSONObject) {
            when (stage) {
                DevelopmentStage.SOURCE -> {
                    artifact(facts.getJSONObject("source")); require(integer(facts, "frames") >= 2)
                    require(integer(facts, "timestampSpanNs") > 0 && facts.getString("durationUnit") == "ns")
                    require(facts.getString("durationDomain") == "source_sensor_timestamp_span")
                    require(facts.getJSONObject("sourceBinding").getString("fingerprint").isNotBlank())
                    yes(facts, "allFrameChecksumsChecked")
                    require(facts.getJSONObject("source").getString("sha256") == context.getString("sourceSha256") && integer(facts,"frames") == integer(context,"expectedFrames"))
                    val binding=facts.getJSONObject("sourceBinding");val expected=context.getJSONObject("sourceBinding")
                    require(binding.length()==expected.length() && binding.keys().asSequence().all { binding.get(it)==expected.get(it) })
                }
                DevelopmentStage.PROFILE -> {
                    artifact(facts.getJSONObject("profile")); yes(facts, "sourceBindingChecked")
                    require(facts.getString("calibrationStatus") in listOf("synthetic", "provisional", "measured"))
                    require(integer(facts, "width") > 0 && integer(facts, "height") > 0)
                    require(facts.getJSONObject("profile").getString("sha256")==context.getString("profileSha256"))
                    require(integer(facts,"width")==integer(context,"width") && integer(facts,"height")==integer(context,"height"))
                }
                DevelopmentStage.CODEC -> {
                    require(facts.getString("codec").isNotBlank() && facts.getString("codec")==context.getString("codec"))
                    val q = facts.getJSONObject("qualification")
                    require(q.getString("status") == "qualified")
                    val positive = q.getJSONObject("positive"); val negative = q.getJSONObject("eightBitNegative")
                    require(ramp(positive) && positive.get("passed") == true) { "Invalid positive precision control" }
                    require(!ramp(negative) && negative.get("passed") == false) { "Eight-bit control was not independently rejected" }
                }
                DevelopmentStage.ENCODED -> {
                    require(integer(facts.getJSONObject("encoder"), "frames") == integer(context, "expectedFrames"))
                    require(integer(facts, "byteCount") > 0 && facts.getString("name").isNotBlank())
                    require(facts.getJSONObject("encoder").getString("name")==context.getString("codec"))
                }
                DevelopmentStage.DECODED -> {
                    val v = facts.getJSONObject("verification"); signal(v)
                    require(integer(v, "decodedFrames") == integer(context, "expectedFrames"))
                    require(integer(v, "width") == integer(context, "width") && integer(v, "height") == integer(context, "height"))
                    require(number(v, "maximumFrameMeanLumaCodeError") in 0.0..4.0 && number(v, "maximumFrameMeanChromaCodeError") in 0.0..4.0)
                    require(integer(v, "maximumCodeError") in 0..64 && number(v, "meanErrorLimitCodes") == 4.0 && integer(v, "peakErrorLimitCodes") == 64L)
                    artifact(v.getJSONObject("mediaIdentity"))
                    require(number(v,"measuredFps")==integer(context,"fps").toDouble())
                }
                DevelopmentStage.UNCHANGED -> {
                    require(facts.getString("sourceBefore") == facts.getString("sourceAfter") && facts.getString("profileBefore") == facts.getString("profileAfter"))
                    require(listOf("sourceBefore", "profileBefore").all { facts.getString(it).matches(Regex("[0-9a-f]{64}")) })
                    require(facts.getString("sourceBefore")==context.getString("sourceSha256") && facts.getString("profileBefore")==context.getString("profileSha256"))
                }
                DevelopmentStage.PUBLICATION -> { yes(facts, "renamedWithoutOverwrite"); require(facts.getString("name").isNotBlank()); require(integer(facts, "byteCount") > 0) }
                else -> error("Saved-RAW adapter cannot observe ${stage.wire}")
            }
        }
    }
}
