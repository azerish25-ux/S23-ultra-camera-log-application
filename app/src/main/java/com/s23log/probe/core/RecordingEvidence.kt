package com.s23log.probe.core

/** Ordinary-recording stages reuse P003 outcomes but do not require fabricated RAW/profile gates. */
enum class RecordingStage(val wire: String) {
    ADVERTISED("advertised"), PREPARATION("preparation"), CONFIGURED("configured"),
    ENCODED("encoded_output"), AUDIO("audio_samples"), OUTPUT("output_validation"),
    FULL_DECODE("full_decode"), PUBLICATION("publication"), RETENTION("retention"), PHYSICAL("physical_qualification")
}
data class RecordingStageResult(val stage: RecordingStage, val outcome: DevelopmentOutcome, val reason: String,
    val sourceRevision: String, val evidenceRef: String?, val evidenceSha256: String?, val checks: List<DevelopmentCheck>)
data class RecordingClassification(val outputChecked: Boolean, val publishedOutput: Boolean,
    val recordingSucceeded: Boolean, val retainedForRecovery: Boolean, val fullDecodeVerified: Boolean,
    val physicalCameraCertified: Boolean, val outcomes: Map<RecordingStage, DevelopmentOutcome>, val issues: List<String>)
/** Pure classification of independently checked observations. Full decode and physical protocols
 * are deliberately outside this adapter. An output check can survive a failed capture/publication. */
object RecordingClassifier {
    fun classify(stages: List<RecordingStageResult>, revision: String, closed: Boolean,
        audioRequested: Boolean, captureErrors: List<String>): RecordingClassification {
        val issues = mutableListOf<String>()
        val outcomes = linkedMapOf<RecordingStage, DevelopmentOutcome>()
        val invalid = mutableSetOf<RecordingStage>()
        val severity = listOf(DevelopmentOutcome.FAILED, DevelopmentOutcome.BLOCKED,
            DevelopmentOutcome.UNAVAILABLE, DevelopmentOutcome.NOT_RUN, DevelopmentOutcome.INCONCLUSIVE)
        if (!revision.matches(Regex("[0-9a-f]{40}"))) issues += "Missing source revision"
        for (record in stages) {
            fun reject(reason: String) { issues += "${record.stage.wire}: $reason"; invalid += record.stage }
            if (record.stage in outcomes) reject("duplicate stage")
            if (record.sourceRevision != revision) reject("conflicting source revision")
            if (record.reason.isBlank()) reject("missing reason")
            if (record.outcome != DevelopmentOutcome.NOT_RUN &&
                (record.evidenceRef.isNullOrBlank() || record.evidenceSha256?.matches(Regex("[0-9a-f]{64}")) != true))
                reject("missing observation identity")
            if (record.checks.map { it.id }.toSet().size != record.checks.size ||
                record.checks.any { it.id.isBlank() || it.reason.isBlank() }) reject("invalid individual checks")
            val observed = severity.firstOrNull { level -> record.checks.any { it.outcome == level } }
                ?: if (record.checks.isEmpty()) DevelopmentOutcome.NOT_RUN else DevelopmentOutcome.PASSED
            if (observed != record.outcome) reject("summary contradicts individual outcomes")
            if (record.stage in setOf(RecordingStage.FULL_DECODE, RecordingStage.PHYSICAL) && observed != DevelopmentOutcome.NOT_RUN)
                reject("independent protocol not observed by ordinary recorder")
            outcomes[record.stage] = observed
        }
        fun passed(stage: RecordingStage) = stage !in invalid && outcomes[stage] == DevelopmentOutcome.PASSED
        val output = closed && passed(RecordingStage.OUTPUT)
        val published = output && passed(RecordingStage.PUBLICATION)
        val success = published && issues.isEmpty() && captureErrors.isEmpty() &&
            listOf(RecordingStage.PREPARATION, RecordingStage.CONFIGURED, RecordingStage.ENCODED).all(::passed) &&
            (!audioRequested || passed(RecordingStage.AUDIO))
        return RecordingClassification(output, published, success, closed && passed(RecordingStage.RETENTION),
            false, false, outcomes.toMap(), issues.toList())
    }
}
