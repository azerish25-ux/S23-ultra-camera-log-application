package com.s23log.probe.core

/** P003 vocabulary. Availability, execution and physical qualification are not a Boolean ladder. */
enum class DevelopmentOutcome(val wire: String) {
    PASSED("passed"), FAILED("failed"), BLOCKED("blocked"), UNAVAILABLE("unavailable"),
    NOT_RUN("not_run"), INCONCLUSIVE("inconclusive")
}
enum class DevelopmentStage(val wire: String) {
    ADVERTISED("advertised"), CONFIGURED("configured"), SOURCE("source_validation"),
    PROFILE("profile_validation"), CODEC("codec_qualification"), ENCODED("encoded_output"),
    DECODED("decoded_verification"), UNCHANGED("source_preservation"), PUBLICATION("publication"),
    PHYSICAL("physical_qualification")
}
data class DevelopmentCheck(val id: String, val outcome: DevelopmentOutcome, val reason: String)
data class DevelopmentStageResult(
    val stage: DevelopmentStage, val outcome: DevelopmentOutcome, val reason: String,
    val sourceRevision: String, val evidenceRef: String?, val evidenceSha256: String?,
    val checks: List<DevelopmentCheck>
)
data class DevelopmentClassification(
    val verifiedOutput: Boolean, val publishedOutput: Boolean, val physicalCameraCertified: Boolean,
    val outcomes: Map<DevelopmentStage, DevelopmentOutcome>, val issues: List<String>
)

/** Pure classifier used by the on-device attempt reporter. It neither runs experiments nor grants
 * physical certification. Later production adapters must supply their own independently checked
 * observations; a later stage never invents an earlier stage. */
object DevelopmentClassifier {
    val outputStages = listOf(DevelopmentStage.SOURCE, DevelopmentStage.PROFILE,
        DevelopmentStage.CODEC, DevelopmentStage.ENCODED, DevelopmentStage.DECODED, DevelopmentStage.UNCHANGED)
    private val severity = listOf(DevelopmentOutcome.FAILED, DevelopmentOutcome.BLOCKED,
        DevelopmentOutcome.UNAVAILABLE, DevelopmentOutcome.NOT_RUN, DevelopmentOutcome.INCONCLUSIVE)
    private fun digest(value: String?, length: Int) = value?.matches(Regex("[0-9a-f]{$length}")) == true

    fun classify(stages: List<DevelopmentStageResult>, expectedRevision: String, closed: Boolean): DevelopmentClassification {
        val issues = mutableListOf<String>()
        val outcomes = linkedMapOf<DevelopmentStage, DevelopmentOutcome>()
        val invalid = mutableSetOf<DevelopmentStage>()
        for (record in stages) {
            fun reject(reason: String) { issues += "${record.stage.wire}: $reason"; invalid += record.stage }
            if (record.stage in outcomes) reject("duplicate stage")
            if (!digest(expectedRevision, 40) || record.sourceRevision != expectedRevision) reject("missing or conflicting source revision")
            if (record.reason.isBlank()) reject("missing reason")
            if (record.outcome != DevelopmentOutcome.NOT_RUN &&
                (record.evidenceRef.isNullOrBlank() || !digest(record.evidenceSha256, 64))) reject("missing observation identity")
            if (record.checks.map { it.id }.toSet().size != record.checks.size ||
                record.checks.any { it.id.isBlank() || it.reason.isBlank() }) reject("invalid individual checks")
            val observed = severity.firstOrNull { level -> record.checks.any { it.outcome == level } }
                ?: if (record.checks.isEmpty()) DevelopmentOutcome.NOT_RUN else DevelopmentOutcome.PASSED
            if (observed != record.outcome) reject("summary contradicts individual outcomes")
            outcomes[record.stage] = observed
            if (record.stage == DevelopmentStage.PHYSICAL && observed == DevelopmentOutcome.PASSED)
                reject("physical certification requires an independent physical protocol, not this saved-RAW adapter")
        }
        val verified = closed && outputStages.all { it !in invalid && outcomes[it] == DevelopmentOutcome.PASSED }
        val published = verified && DevelopmentStage.PUBLICATION !in invalid && outcomes[DevelopmentStage.PUBLICATION] == DevelopmentOutcome.PASSED
        return DevelopmentClassification(verified, published, false, outcomes.toMap(), issues.toList())
    }
}
