package com.s23log.probe.live

import com.s23log.probe.core.*
import com.s23log.probe.develop.DevelopmentAttempt
import com.s23log.probe.diagnostics.RecordingAttempt
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.util.UUID
import java.util.concurrent.CancellationException

/** A bounded observer of the existing live owners. It never operates on footage or opens a camera.
 * Writes are scheduled on a serial IO owner; crashes can leave incomplete checkpoints. */
class LiveAttempt(directory: File, val revision: String, val kind: LiveAttemptKind, context: JSONObject,
                  private val write: (File, String) -> Unit,
                  private val schedule: (() -> Unit) -> Unit = { it() },
                  val id: String = UUID.randomUUID().toString(),
                  private val onPersistenceFailure: (String) -> Unit = {}) {
    init { require(id.matches(Regex("[0-9a-f-]{36}"))) }
    val file = File(directory, "live-attempt-$id.json")
    private val context = JSONObject(context.toString())
    private val records = linkedMapOf<LiveStage, LiveStageResult>()
    private val observations = linkedMapOf<String, String>()
    private val errors = mutableListOf<String>()
    private val reportErrors = mutableListOf<String>()
    private val started = Instant.now().toString()
    private var ended: String? = null
    private var closed = false
    private var recordingRequested = false
    private var active: LiveStage? = null
    private var owned = false // Written only by the serial IO owner.
    @Volatile var persistenceError: String? = null; private set

    @Synchronized fun start() = checkpoint()
    @Synchronized fun bind(key: String, value: JSONObject) {
        check(!closed && !context.has(key)) { "Context already bound: $key" }
        context.put(key, JSONObject(value.toString()))
    }
    @Synchronized fun requestRecording() {
        if (closed || recordingRequested) return
        check(kind == LiveAttemptKind.CAMERA)
        recordingRequested = true; checkpoint()
    }
    @Synchronized fun has(stage: LiveStage) = stage in records
    @Synchronized fun begin(stage: LiveStage) {
        check(!closed && stage !in records)
        active = stage; checkpoint()
    }
    fun <T> step(stage: LiveStage, operation: (JSONObject) -> T): T {
        safe { begin(stage) }
        val facts = JSONObject()
        return try {
            val result = operation(facts)
            safe { observe(stage, DevelopmentOutcome.PASSED, "Operation returned; raw observations checked", facts) }
            result
        } catch (error: Exception) {
            safe { observe(stage, if (error is CancellationException) DevelopmentOutcome.BLOCKED else DevelopmentOutcome.FAILED,
                error.message ?: error.javaClass.simpleName, facts.put("exception", error.javaClass.simpleName)) }
            throw error
        }
    }
    @Synchronized fun failedActive(error: Exception) {
        active?.let { stage -> observe(stage, if(error is CancellationException) DevelopmentOutcome.BLOCKED else DevelopmentOutcome.FAILED,
            error.message ?: error.javaClass.simpleName, JSONObject().put("exception", error.javaClass.simpleName)) }
    }
    @Synchronized fun observe(stage: LiveStage, outcome: DevelopmentOutcome, reason: String, facts: JSONObject = JSONObject()) {
        if (closed || stage in records) return
        var actual = outcome; var detail = reason
        try {
            validateFacts(stage, outcome, facts, context, kind, id)
            if (outcome == DevelopmentOutcome.PASSED && stage == LiveStage.PUBLICATION) {
                val decoded = requireNotNull(records[LiveStage.DECODED])
                require(decoded.outcome == DevelopmentOutcome.PASSED)
                val old = JSONObject(requireNotNull(observations[decoded.evidenceRef])).getJSONObject("facts").getJSONObject("mediaIdentity")
                require(RecordingAttempt.same(old, facts.getJSONObject("mediaIdentity"))) { "Published media differs from decoded media" }
            }
        } catch (error: Exception) { actual = DevelopmentOutcome.FAILED; detail = "Evidence contract: ${error.message}" }
        val ref = stage.wire + "-observation"
        val payload = JSONObject().put("attemptId", id).put("sourceRevision", revision).put("stage", stage.wire)
            .put("facts", JSONObject(facts.toString())).toString()
        observations[ref] = payload
        records[stage] = LiveStageResult(stage, actual, detail, revision, ref, DevelopmentAttempt.hash(payload),
            listOf(DevelopmentCheck("observed-operation", actual, detail)))
        if (active == stage) active = null
        checkpoint()
    }
    @Synchronized fun noteReportError(message: String) { if (reportErrors.size < 16) reportErrors += message }
    @Synchronized fun close(failures: List<String> = emptyList()) {
        if (closed) return
        if (active != null && active !in records) observe(requireNotNull(active), DevelopmentOutcome.INCONCLUSIVE,
            "Attempt ended without a completed observation for this operation")
        errors += failures.filter(String::isNotBlank).distinct().take(16)
        active = null; closed = true; ended = Instant.now().toString(); checkpoint()
    }
    fun safe(block: () -> Unit) { try { block() } catch(e: Exception) { noteReportError("Observation: ${e.message}") } }

    @Synchronized fun snapshot(): JSONObject {
        val all = LiveStage.values().map { stage -> records[stage] ?: LiveStageResult(stage, DevelopmentOutcome.NOT_RUN,
            when (stage) {
                LiveStage.SOURCE_PIXELS -> "Live source pixels are not retained; no original-RAW picture comparison"
                LiveStage.PHYSICAL -> "No independent physical-device qualification protocol"
                else -> "No completed observation in this attempt"
            }, revision, null, null, emptyList()) }
        val verdict = LiveClassifier.classify(all, revision, kind, closed, recordingRequested, errors)
        return JSONObject().put("schemaVersion", 1).put("kind", "live-attempt-evidence").put("attemptKind", kind.wire)
            .put("attemptId", id).put("sourceRevision", revision).put("startedAt", started).put("endedAt", ended ?: JSONObject.NULL)
            .put("closed", closed).put("activeStage", active?.wire ?: JSONObject.NULL).put("recordingRequested", recordingRequested)
            .put("context", JSONObject(context.toString())).put("policy", policy())
            .put("stages", JSONArray(all.map { r -> JSONObject().put("stage",r.stage.wire).put("outcome",r.outcome.wire)
                .put("reason",r.reason).put("sourceRevision",r.sourceRevision).put("evidenceRef",r.evidenceRef ?: JSONObject.NULL)
                .put("evidenceSha256",r.evidenceSha256 ?: JSONObject.NULL).put("checks",JSONArray(r.checks.map { c ->
                    JSONObject().put("id",c.id).put("outcome",c.outcome.wire).put("reason",c.reason) })) }))
            .put("observations",JSONObject(observations as Map<*,*>)).put("errors",JSONArray(errors))
            .put("reportErrors",JSONArray(reportErrors)).put("persistenceError",persistenceError ?: JSONObject.NULL)
            .put("sourcePixelsStored",false).put("pixelSourceComparison",false).put("physicalCameraCertified",false)
            .put("classification",JSONObject().put("backendQualified",verdict.backendQualified)
                .put("cameraFramesObserved",verdict.cameraFramesObserved).put("outputDecoded",verdict.outputDecoded)
                .put("publishedOutput",verdict.publishedOutput).put("recordingSucceeded",verdict.recordingSucceeded)
                .put("previewOnly",verdict.previewOnly).put("pixelSourceComparison",false).put("physicalCameraCertified",false)
                .put("issues",JSONArray(verdict.issues)))
    }
    private fun checkpoint() {
        try {
            val payload = snapshot().toString(2)
            schedule {
                try {
                    val parent = requireNotNull(file.parentFile)
                    check(parent.isDirectory || parent.mkdirs())
                    if (!owned) { check(file.createNewFile()) { "Attempt already exists; refusing overwrite" }; owned = true }
                    write(file, payload)
                } catch(e: Exception) { persistenceFailed(e) }
            }
        } catch(e: Exception) { persistenceFailed(e) }
    }
    private fun persistenceFailed(error: Exception) {
        val message=error.message ?: error.javaClass.simpleName
        persistenceError=message
        runCatching { onPersistenceFailure(message) } // The UI callback cannot affect footage or the writer.
    }
    companion object {
        fun policy(): JSONObject = JSONObject().put("id","live-existing-0.9-v1")
            .put("gpuLogErrorLimit",.001).put("gpuP010ErrorLimit",2).put("gpuLogDomain","LogC3_RGB")
            .put("meanCodeErrorLimit",.75).put("peakCodeErrorLimit",2).put("minimumRampLevels",600).put("colourPatchErrorLimit",12)
            .put("codeUnit","code_value").put("codeDomain","decoded_P010")
            .put("durationUnit","us").put("durationDomain","relative_sensor_presentation_timestamps")
            .put("timestampToleranceUs",2).put("maximumFrames",18000)
            .put("cadenceToleranceFraction",.03).put("cadenceMinimumSpanNs",2_000_000_000L)
        private fun yes(j:JSONObject,key:String) { require(j.get(key) == true) { "Missing true $key" } }
        private fun no(j:JSONObject,key:String) { require(j.get(key) == false) { "Unexpected claim $key" } }
        private fun integer(j:JSONObject,key:String):Long {
            val n=j.get(key);require(n is Byte || n is Short || n is Int || n is Long) { "Expected integer $key" };return (n as Number).toLong()
        }
        private fun real(j:JSONObject,key:String):Double {
            val n=j.get(key);require(n is Number && n.toDouble().isFinite() && n.toDouble() >= 0) { "Invalid $key" };return n.toDouble()
        }
        private fun media(j:JSONObject) {
            require(j.getString("algorithm")=="SHA-256" && j.getString("sha256").matches(Regex("[0-9a-f]{64}")) && integer(j,"byteCount")>0)
        }
        private fun signal(j:JSONObject,w:Int,h:Int,count:Int,relative:Boolean) {
            yes(j,"fullDecodeVerified")
            require(integer(j,"width")==w.toLong() && integer(j,"height")==h.toLong() && integer(j,"decodedFrames")==count.toLong() && count>=2)
            require(j.getString("mime")=="video/hevc" && j.getString("decoder").isNotBlank())
            for((key,value) in mapOf("lumaBitDepth" to 10,"chromaBitDepth" to 10,"colorPrimariesCode" to 2,
                "transferCharacteristicsCode" to 2,"matrixCoefficientsCode" to 1,"colorRange" to 2,"colorTransfer" to 0))
                require(integer(j,key)==value.toLong()) { "Wrong signal $key" }
            require(j.getString("timestampContract")==if(relative)"relative_sensor_timestamps" else "CFR")
        }
        private fun ramp(j:JSONObject,w:Int,h:Int,count:Int,degraded:Boolean):Boolean {
            signal(j,w,h,count,false);require(j.get("deliberatelyDegraded")==degraded)
            val mean=real(j,"meanCodeError");val peak=real(j,"maximumCodeError");val levels=integer(j,"distinctRampLevels")
            val colour=integer(j,"colourPatchPeakCodeError");require(levels in 1..877 && colour>=0)
            val passed=mean<=.75 && peak<=2 && levels>=600 && colour<=12
            require(j.get("passed")==passed) { "Ramp summary contradicts measurements" };return passed
        }
        /** Consumers also validate unavailable backend raw facts: changing qualified to unavailable
         * must not conceal a selected route or contradict retained positive evidence. */
        fun validateFacts(stage:LiveStage,outcome:DevelopmentOutcome,f:JSONObject,c:JSONObject,kind:LiveAttemptKind,id:String) {
            if(stage==LiveStage.BACKEND && f.has("report") && outcome in setOf(DevelopmentOutcome.PASSED,DevelopmentOutcome.UNAVAILABLE,DevelopmentOutcome.INCONCLUSIVE)) {
                val r=f.getJSONObject("report");val request=c.getJSONObject("requested")
                val w=integer(request,"width").toInt();val h=integer(request,"height").toInt()
                require(integer(r,"width")==w.toLong() && integer(r,"height")==h.toLong() && integer(r,"fps")==integer(request,"fps"))
                require(r.getString("kind")=="live-log-backend-probe");yes(r,"syntheticInputs");no(r,"sensorPrecisionMeasured");no(r,"hlgTransferRequested")
                val routes=r.getJSONArray("routes");val accepted=(0 until routes.length()).map(routes::getJSONObject).filter{it.optString("status")=="qualified"}
                if(outcome==DevelopmentOutcome.PASSED) {
                    require(r.getString("status")=="qualified" && accepted.size==1)
                    val a=accepted.single();require(a.getString("codec")==r.getString("selectedCodec") && a.getString("input")==r.getString("selectedInput"))
                    require(a.getString("input") in setOf("P010_IMAGE","RGB10_SURFACE") && a.getString("codec").isNotBlank())
                    require(ramp(a.getJSONObject("positive"),1024,128,4,false))
                    require(!ramp(a.getJSONObject("eightBitNegative"),1024,128,4,true))
                    require(ramp(a.getJSONObject("selectedSize"),w,h,2,false))
                    for(name in listOf("positive","eightBitNegative","selectedSize"))
                        require(real(a.getJSONObject(name),"measuredFps")==integer(request,"fps").toDouble()) { "Qualification cadence differs from selected request" }
                } else {
                    require(r.getString("status")==if(outcome==DevelopmentOutcome.UNAVAILABLE)"unavailable" else "query_failed")
                    require(accepted.isEmpty() && r.isNull("selectedCodec") && r.isNull("selectedInput"))
                }
            }
            if(outcome!=DevelopmentOutcome.PASSED) return
            val request=c.getJSONObject("requested")
            if(kind==LiveAttemptKind.BACKEND) require(stage in setOf(LiveStage.GPU,LiveStage.BACKEND))
            when(stage) {
                LiveStage.PROFILE -> {
                    require(kind==LiveAttemptKind.CAMERA)
                    val p=JSONObject(c.getString("profilePayload"));require(DevelopmentAttempt.hash(c.getString("profilePayload"))==c.getString("profileSha256"))
                    val source=f.getJSONObject("sourceBinding");require(RecordingAttempt.same(source,p.getJSONObject("source")) && RecordingAttempt.same(source,c.getJSONObject("sourceBinding")))
                    require(source.getString("fingerprint")==c.getJSONObject("device").getString("fingerprint"))
                    val calibration=p.getJSONObject("calibration");require(calibration.getString("status") in setOf("measured","provisional"))
                    require(calibration.getString("evidence").isNotBlank() && calibration.getString("illuminant").isNotBlank())
                    require(calibration.getString("status")!="provisional" || request.get("allowProvisional")==true)
                    yes(f,"routeAndLayoutMatched");yes(f,"requestedControlsApplicable");no(f,"calibrationIndependentlyVerified")
                }
                LiveStage.GPU -> {
                    val r=f.getJSONObject("report");require(r.getString("status")=="passed" && integer(r,"bayerReductionCases")==12L)
                    yes(r,"synthetic");no(r,"sensorPrecisionMeasured")
                    require(real(r,"maximumLogRgbError")<=.001 && integer(r,"maximumP010CodeError") in 0..2)
                }
                LiveStage.BACKEND -> require(f.has("report"))
                LiveStage.CONFIGURED -> { yes(f,"cameraSessionCallback");yes(f,"repeatingRequestSubmitted");require(RecordingAttempt.same(f.getJSONObject("sourceBinding"),c.getJSONObject("sourceBinding"))) }
                LiveStage.RAW -> {
                    require(integer(f,"processedFrames")>0 && integer(f,"matchedFrames")>=integer(f,"processedFrames") && integer(f,"imagesReceived")>=integer(f,"matchedFrames"))
                    yes(f,"exactSensorTimestampPairing");yes(f,"profileExposureAndFocusChecked");no(f,"sourcePixelsStored")
                }
                LiveStage.ENCODED -> {
                    val r=f.getJSONObject("encoding");require(integer(r,"encodedFrames")>=2 && integer(r,"encodedFrames")==integer(f,"framesSubmitted"))
                    val selected=c.getJSONObject("selectedBackend");require(r.getString("codec")==selected.getString("codec") && r.getString("input")==selected.getString("input"))
                    no(r,"hlgTransferUsed");yes(r,"pictureNalsUnchangedByMetadataRewrite");require(r.getString("timestampMapping")=="sensor_delta_ns_divided_by_1000" && r.getString("audio")=="none")
                }
                LiveStage.DECODED -> {
                    val pts=f.getJSONArray("sensorPresentationTimesUs");require(pts.length() in 2..18000)
                    var previous=-1L
                    for(i in 0 until pts.length()) { val v=pts.get(i);require(v is Int || v is Long);val n=(v as Number).toLong();require(n>previous && (i!=0 || n==0L));previous=n }
                    require(f.getString("durationUnit")=="us" && f.getString("durationDomain")=="relative_sensor_presentation_timestamps" && integer(f,"timestampSpanUs")==previous)
                    signal(f.getJSONObject("verification"),integer(request,"width").toInt(),integer(request,"height").toInt(),pts.length(),true)
                    no(f.getJSONObject("verification"),"pixelSourceComparison");no(f.getJSONObject("verification"),"physicalCameraCertified")
                    require(f.getString("partialName")=="live-$id.partial.mp4");media(f.getJSONObject("mediaIdentity"))
                }
                LiveStage.PUBLICATION -> { yes(f,"renameSucceeded");require(f.getString("publishedName")=="live-$id.mp4");media(f.getJSONObject("mediaIdentity")) }
                LiveStage.CLEANUP -> {
                    require(f.getString("scope")=="application_owner_close_acknowledgments")
                    for(key in listOf("cameraCloseAcknowledged","previewCleanupConfirmed","gpuCloseReturned","eglCloseReturned","encoderCloseReturned"))yes(f,key)
                }
                LiveStage.SOURCE_PIXELS,LiveStage.PHYSICAL -> error("Independent source/physical protocol not provided")
            }
        }
    }
}
