import com.s23log.probe.core.*

/** Authored stage fixtures; executing this runner does not run a camera or codec. */
fun main() {
    val revision = "a".repeat(40)
    fun row(s: LiveStage, outcome: DevelopmentOutcome) = LiveStageResult(s, outcome, "Authored model observation", revision,
        if(outcome == DevelopmentOutcome.NOT_RUN) null else s.wire+"-observation",
        if(outcome == DevelopmentOutcome.NOT_RUN) null else "b".repeat(64),
        if(outcome == DevelopmentOutcome.NOT_RUN) emptyList() else listOf(DevelopmentCheck("observed",outcome,"Authored fixture")))
    val software = LiveStage.values().map { row(it, if(it in setOf(LiveStage.SOURCE_PIXELS,LiveStage.PHYSICAL)) DevelopmentOutcome.NOT_RUN else DevelopmentOutcome.PASSED) }
    fun classify(rows:List<LiveStageResult> = software, closed:Boolean=true, requested:Boolean=true,
                 kind:LiveAttemptKind=LiveAttemptKind.CAMERA, errors:List<String> = emptyList()) =
        LiveClassifier.classify(rows,revision,kind,closed,requested,errors)
    var count=0
    fun expect(ok:Boolean, why:String) { check(ok){why};count++ }
    val good=classify()
    expect(good.recordingSucceeded && good.publishedOutput && good.outputDecoded,"Complete software fixture")
    expect(!good.physicalCameraCertified && !good.pixelSourceComparison,"Live output cannot qualify sensor/source pixels")
    expect(!classify(closed=false).recordingSucceeded,"Incomplete checkpoint")
    for(s in listOf(LiveStage.PROFILE,LiveStage.GPU,LiveStage.BACKEND,LiveStage.CONFIGURED,LiveStage.RAW,LiveStage.ENCODED,LiveStage.DECODED,LiveStage.PUBLICATION,LiveStage.CLEANUP)) {
        for(o in listOf(DevelopmentOutcome.FAILED,DevelopmentOutcome.UNAVAILABLE,DevelopmentOutcome.BLOCKED,DevelopmentOutcome.NOT_RUN,DevelopmentOutcome.INCONCLUSIVE)) {
            val bad=classify(software.map{if(it.stage==s)row(s,o) else it})
            expect(!bad.recordingSucceeded,"${s.wire}/$o must block success")
        }
    }
    val backend=software.map { if(it.stage in setOf(LiveStage.GPU,LiveStage.BACKEND)) it else row(it.stage,DevelopmentOutcome.NOT_RUN) }
    expect(classify(backend,requested=false,kind=LiveAttemptKind.BACKEND).backendQualified,"Narrower codec result retained")
    expect(!classify(backend,requested=false,kind=LiveAttemptKind.BACKEND).cameraFramesObserved,"No implicit camera")
    expect(!classify(backend,requested=false,kind=LiveAttemptKind.BACKEND).recordingSucceeded,"Backend not live capture")
    val preview=software.map { if(it.stage in setOf(LiveStage.ENCODED,LiveStage.DECODED,LiveStage.PUBLICATION))row(it.stage,DevelopmentOutcome.NOT_RUN) else it }
    expect(classify(preview,requested=false).previewOnly,"Preview stop is not a recorded take")
    expect(!classify(preview,requested=false).publishedOutput,"Preview cannot publish movie")
    val rename=software.map { if(it.stage==LiveStage.PUBLICATION)row(it.stage,DevelopmentOutcome.FAILED) else it }
    expect(classify(rename).outputDecoded && !classify(rename).publishedOutput,"Decode survives failed publication")
    val broken=software.map { if(it.stage==LiveStage.GPU)it.copy(checks=listOf(DevelopmentCheck("raw",DevelopmentOutcome.FAILED,"Actual failure"))) else it }
    expect(!classify(broken).backendQualified && classify(broken).issues.isNotEmpty(),"Raw failure overrides green")
    expect(!classify(software+software.first()).recordingSucceeded,"Duplicate stages")
    expect(!classify(software.drop(1)).recordingSucceeded,"Missing stage")
    expect(!classify(software.map{it.copy(sourceRevision="c".repeat(40))}).recordingSucceeded,"Mixed revisions")
    expect(!classify(errors=listOf("RAW acquisition stalled")).recordingSucceeded,"Interrupted capture not success")
    for(s in listOf(LiveStage.PHYSICAL,LiveStage.SOURCE_PIXELS)) {
        val bad=classify(software.map{if(it.stage==s)row(s,DevelopmentOutcome.PASSED) else it})
        expect(bad.issues.isNotEmpty() && !bad.recordingSucceeded,"No independent $s protocol")
    }
    println("$count live classifier assertions passed; synthetic model only")
}
