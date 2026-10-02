package com.s23log.probe.core

/** Live preparation/recording is not saved-RAW development and does not retain source pixels. */
enum class LiveAttemptKind(val wire: String) { BACKEND("backend_test"), CAMERA("camera_session") }
enum class LiveStage(val wire: String) {
    PROFILE("profile_validation"), GPU("gpu_reference"), BACKEND("codec_qualification"),
    CONFIGURED("configured"), RAW("matched_raw_frames"), ENCODED("encoded_output"),
    DECODED("full_decode"), PUBLICATION("publication"), CLEANUP("resource_cleanup"),
    SOURCE_PIXELS("source_pixel_comparison"), PHYSICAL("physical_qualification")
}
data class LiveStageResult(val stage: LiveStage, val outcome: DevelopmentOutcome, val reason: String,
    val sourceRevision: String, val evidenceRef: String?, val evidenceSha256: String?, val checks: List<DevelopmentCheck>)
data class LiveClassification(val backendQualified: Boolean, val cameraFramesObserved: Boolean,
    val outputDecoded: Boolean, val publishedOutput: Boolean, val recordingSucceeded: Boolean,
    val previewOnly: Boolean, val pixelSourceComparison: Boolean, val physicalCameraCertified: Boolean,
    val outcomes: Map<LiveStage, DevelopmentOutcome>, val issues: List<String>)

/** Classifies independently validated observations. No fixture or full decode can certify a sensor. */
object LiveClassifier {
    fun classify(stages: List<LiveStageResult>, revision: String, kind: LiveAttemptKind,
                 closed: Boolean, recordingRequested: Boolean, errors: List<String>): LiveClassification {
        val issues = mutableListOf<String>()
        val outcomes = linkedMapOf<LiveStage, DevelopmentOutcome>()
        val invalid = mutableSetOf<LiveStage>()
        val severity = listOf(DevelopmentOutcome.FAILED, DevelopmentOutcome.BLOCKED, DevelopmentOutcome.UNAVAILABLE,
            DevelopmentOutcome.NOT_RUN, DevelopmentOutcome.INCONCLUSIVE)
        val validRevision = revision.matches(Regex("[0-9a-f]{40}"))
        if (!validRevision) issues += "Missing exact source revision"
        if (kind == LiveAttemptKind.BACKEND && recordingRequested) issues += "Backend test cannot request camera recording"
        for (r in stages) {
            fun reject(why: String) { issues += "${r.stage.wire}: $why"; invalid += r.stage }
            if (r.stage in outcomes) reject("duplicate stage")
            if (!validRevision || r.sourceRevision != revision) reject("conflicting source revision")
            if (r.reason.isBlank()) reject("missing reason")
            if (r.outcome == DevelopmentOutcome.NOT_RUN) {
                if (r.evidenceRef != null || r.evidenceSha256 != null || r.checks.isNotEmpty()) reject("unrun stage has evidence")
            } else if (r.evidenceRef != r.stage.wire + "-observation" || r.evidenceSha256?.matches(Regex("[0-9a-f]{64}")) != true)
                reject("missing observation identity")
            if (r.checks.map { it.id }.toSet().size != r.checks.size || r.checks.any { it.id.isBlank() || it.reason.isBlank() })
                reject("invalid checks")
            val observed = severity.firstOrNull { level -> r.checks.any { it.outcome == level } }
                ?: if (r.checks.isEmpty()) DevelopmentOutcome.NOT_RUN else DevelopmentOutcome.PASSED
            if (observed != r.outcome) reject("summary contradicts individual checks")
            if (r.stage in setOf(LiveStage.SOURCE_PIXELS, LiveStage.PHYSICAL) && observed != DevelopmentOutcome.NOT_RUN)
                reject("independent source/physical protocol not provided")
            if (kind == LiveAttemptKind.BACKEND && r.stage !in setOf(LiveStage.GPU, LiveStage.BACKEND) && observed != DevelopmentOutcome.NOT_RUN)
                reject("backend-only test cannot provide camera evidence")
            outcomes[r.stage] = observed
        }
        for (stage in LiveStage.values()) if (stage !in outcomes) { invalid += stage; issues += "${stage.wire}: missing stage" }
        fun passed(stage: LiveStage) = stage !in invalid && outcomes[stage] == DevelopmentOutcome.PASSED
        val backend = closed && passed(LiveStage.GPU) && passed(LiveStage.BACKEND)
        val camera = closed && kind == LiveAttemptKind.CAMERA && passed(LiveStage.PROFILE) && passed(LiveStage.CONFIGURED) && passed(LiveStage.RAW)
        val decoded = closed && kind == LiveAttemptKind.CAMERA && recordingRequested && passed(LiveStage.DECODED)
        val published = decoded && passed(LiveStage.PUBLICATION)
        val success = published && backend && camera && passed(LiveStage.ENCODED) && passed(LiveStage.CLEANUP) && errors.isEmpty() && issues.isEmpty()
        return LiveClassification(backend, camera, decoded, published, success, camera && !recordingRequested,
            false, false, outcomes.toMap(), issues.toList())
    }
}
