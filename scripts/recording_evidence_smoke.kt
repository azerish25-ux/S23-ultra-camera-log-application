import com.s23log.probe.core.*

/** Host-only classifier assertions: no Android session or physical phone is simulated as real. */
fun main() {
    val revision = "a".repeat(40)
    var assertions = 0
    fun expect(value: Boolean) { assertions++; check(value) { "Assertion $assertions failed" } }
    fun row(stage: RecordingStage, outcome: DevelopmentOutcome = DevelopmentOutcome.PASSED) = RecordingStageResult(
        stage, outcome, "Authored host fixture", revision, stage.wire, "b".repeat(64),
        listOf(DevelopmentCheck("fixture", outcome, "Test observation")))
    val positive = listOf(RecordingStage.PREPARATION, RecordingStage.CONFIGURED, RecordingStage.ENCODED,
        RecordingStage.OUTPUT, RecordingStage.PUBLICATION).map(::row)
    val classifier = RecordingClassifier
    val good = classifier.classify(positive, revision, true, false, emptyList())
    expect(good.recordingSucceeded); expect(good.outputChecked); expect(good.publishedOutput)
    expect(!good.fullDecodeVerified); expect(!good.physicalCameraCertified); expect(!good.retainedForRecovery)
    for (stage in positive.map { it.stage }) {
        val bad = classifier.classify(positive.filter { it.stage != stage }, revision, true, false, emptyList())
        expect(!bad.recordingSucceeded)
    }
    val eightK = listOf(row(RecordingStage.ADVERTISED), row(RecordingStage.CONFIGURED))
    val partial = classifier.classify(eightK, revision, true, false, emptyList())
    expect(!partial.recordingSucceeded); expect(!partial.outputChecked); expect(!partial.physicalCameraCertified)
    val synthetic = classifier.classify(listOf(row(RecordingStage.OUTPUT)), revision, true, false, emptyList())
    expect(synthetic.outputChecked); expect(!synthetic.recordingSucceeded); expect(!synthetic.physicalCameraCertified)
    expect(!classifier.classify(positive, revision, false, false, emptyList()).recordingSucceeded)
    expect(!classifier.classify(positive, revision, true, true, emptyList()).recordingSucceeded)
    expect(classifier.classify(positive + row(RecordingStage.AUDIO), revision, true, true, emptyList()).recordingSucceeded)
    for (outcome in DevelopmentOutcome.values().filter { it != DevelopmentOutcome.PASSED }) {
        val bad = positive.filter { it.stage != RecordingStage.ENCODED } + row(RecordingStage.ENCODED, outcome)
        expect(!classifier.classify(bad, revision, true, false, emptyList()).recordingSucceeded)
    }
    expect(!classifier.classify(positive + row(RecordingStage.ENCODED), revision, true, false, emptyList()).recordingSucceeded)
    expect(!classifier.classify(positive, "c".repeat(40), true, false, emptyList()).recordingSucceeded)
    val contradiction = positive.map { if (it.stage == RecordingStage.OUTPUT) it.copy(checks = listOf(
        DevelopmentCheck("broken", DevelopmentOutcome.FAILED, "Raw failure"))) else it }
    expect(!classifier.classify(contradiction, revision, true, false, emptyList()).recordingSucceeded)
    val failed = classifier.classify(positive, revision, true, false, listOf("Audio/encoder error"))
    expect(failed.outputChecked); expect(!failed.recordingSucceeded)
    val retained = classifier.classify(positive.filter { it.stage != RecordingStage.PUBLICATION } +
        row(RecordingStage.RETENTION), revision, true, false, listOf("Publication failed"))
    expect(retained.outputChecked); expect(retained.retainedForRecovery); expect(!retained.publishedOutput)
    val physical = classifier.classify(positive + row(RecordingStage.PHYSICAL), revision, true, false, emptyList())
    expect(!physical.physicalCameraCertified); expect(physical.issues.isNotEmpty()); expect(!physical.recordingSucceeded)
    val full = classifier.classify(positive + row(RecordingStage.FULL_DECODE), revision, true, false, emptyList())
    expect(!full.fullDecodeVerified); expect(full.issues.isNotEmpty())
    val noIdentity = positive.map { it.copy(evidenceSha256 = null) }
    expect(!classifier.classify(noIdentity, revision, true, false, emptyList()).recordingSucceeded)
    println("$assertions recording classifier assertions passed; host-only evidence")
}
