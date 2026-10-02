import com.s23log.probe.core.*

/** Authored synthetic evidence; this program never exercises a phone or a codec. */
fun main() {
    var checks = 0
    fun expect(value: Boolean) { checks++; check(value) { "Evidence assertion $checks failed" } }
    val revision = "a".repeat(40)
    fun stage(s: DevelopmentStage, outcome: DevelopmentOutcome = DevelopmentOutcome.PASSED) =
        DevelopmentStageResult(s, outcome, "Synthetic check", revision, "receipt-${s.wire}", "b".repeat(64),
            listOf(DevelopmentCheck("observed", outcome, "Independent fixture verdict")))
    val required = DevelopmentClassifier.outputStages
    val passing = required.map { stage(it) }
    expect(DevelopmentClassifier.classify(passing, revision, true).verifiedOutput)
    expect(!DevelopmentClassifier.classify(passing, revision, true).physicalCameraCertified)
    expect(!DevelopmentClassifier.classify(passing, revision, false).verifiedOutput)
    val advertised = listOf(stage(DevelopmentStage.ADVERTISED), stage(DevelopmentStage.CONFIGURED))
    expect(!DevelopmentClassifier.classify(advertised, revision, true).verifiedOutput)
    expect(!DevelopmentClassifier.classify(advertised, revision, true).physicalCameraCertified)
    for (outcome in DevelopmentOutcome.values().filter { it != DevelopmentOutcome.PASSED }) {
        val input = passing.map { if (it.stage == DevelopmentStage.CODEC) stage(it.stage, outcome) else it }
        expect(!DevelopmentClassifier.classify(input, revision, true).verifiedOutput)
        expect(DevelopmentClassifier.classify(input, revision, true).outcomes[DevelopmentStage.SOURCE] == DevelopmentOutcome.PASSED)
    }
    val hiddenFailure = passing.map { if (it.stage == DevelopmentStage.DECODED)
        it.copy(checks = listOf(DevelopmentCheck("pixels", DevelopmentOutcome.FAILED, "Mismatch"))) else it }
    expect(!DevelopmentClassifier.classify(hiddenFailure, revision, true).verifiedOutput)
    expect(DevelopmentClassifier.classify(hiddenFailure, revision, true).issues.isNotEmpty())
    for (bad in listOf("", "local-unversioned", "c".repeat(40))) {
        expect(!DevelopmentClassifier.classify(passing, bad, true).verifiedOutput)
    }
    expect(!DevelopmentClassifier.classify(passing + passing.first(), revision, true).verifiedOutput)
    expect(!DevelopmentClassifier.classify(passing.map { it.copy(evidenceSha256 = "") }, revision, true).verifiedOutput)
    expect(!DevelopmentClassifier.classify(passing.map { it.copy(checks = emptyList()) }, revision, true).verifiedOutput)
    val claimed = DevelopmentClassifier.classify(passing + stage(DevelopmentStage.PHYSICAL), revision, true)
    expect(!claimed.physicalCameraCertified)
    expect(claimed.issues.any { "physical" in it })
    expect(DevelopmentClassifier.classify(passing.filter { it.stage != DevelopmentStage.PUBLICATION }, revision, true).verifiedOutput)
    expect(!DevelopmentClassifier.classify(passing.filter { it.stage != DevelopmentStage.PUBLICATION }, revision, true).publishedOutput)
    println("$checks evidence checks passed; synthetic host model only; physicalCameraCertified=false")
}
