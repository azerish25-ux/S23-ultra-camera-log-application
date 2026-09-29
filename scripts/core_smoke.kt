import com.s23log.probe.core.*

/** Offline sanity checks using the actual pure policies; JUnit and device suites still run in CI. */
fun main() {
    var passed = 0
    fun test(name: String, block: () -> Unit) { block(); passed++; println("PASS $name") }
    test("8K target retained") { check(ModePlanning.eightK in ModePlanning.sizes(emptyList())) }
    test("all advertised dimensions retained") { check(VideoSize(4096,2160) in ModePlanning.sizes(listOf(VideoSize(4096,2160)))) }
    test("ordinary rates expanded") { check(ModePlanning.rates(emptyList()).containsAll(listOf(24,30,25,50,60))) }
    test("high-speed not silently mixed") { check(120 !in ModePlanning.rates(listOf(FpsRange(120,120)))) }
    test("HEVC SDR") { check("video/hevc" in ModePlanning.mimes(DynamicRange.SDR)) }
    test("HLG cannot use AVC") { check("video/avc" !in ModePlanning.mimes(DynamicRange.HLG10)) }
    test("fixed AE") { check(ModePlanning.timing(30,listOf(FpsRange(15,30),FpsRange(30,30)),false,null,null)?.control == RateControl.AE_FIXED) }
    test("variable AE is labelled") { check(ModePlanning.timing(30,listOf(FpsRange(15,30)),false,null,null)?.control == RateControl.AE_VARIABLE) }
    test("containing AE is not fixed 24") { check(ModePlanning.timing(24,listOf(FpsRange(15,30)),false,null,null) == null) }
    test("manual 24 independent from AE") { check(ModePlanning.timing(24,listOf(FpsRange(15,30)),true,100_000_000,1000)?.requiresManual == true) }
    test("unknown manual limits rejected") { check(ModePlanning.timing(24,emptyList(),true,null,1000) == null) }
    test("impossible manual interval rejected") { check(ModePlanning.timing(24,emptyList(),true,20_000_000,1000) == null) }
    val mode = RecordingMode(7680,4320,24,DynamicRange.SDR,"encoder","video/hevc",100_000_000,true,true,RatePlan(RateControl.MANUAL_SENSOR))
    test("manual intent alone cannot record") { check(!ModePlanning.recordingAllowed(EngineState.PREVIEW,mode,false)) }
    test("confirmed manual can record") { check(ModePlanning.recordingAllowed(EngineState.PREVIEW,mode,true)) }
    test("busy states cannot record") { EngineState.entries.filter { it != EngineState.PREVIEW }.forEach { check(!ModePlanning.recordingAllowed(it,mode,true)) } }
    test("config buffers do not acknowledge") { check(!RecordingStartGate().sampleWritten(10,true,0)) }
    test("first sample acknowledges only once") { val g=RecordingStartGate(); check(g.sampleWritten(10,false,0)); check(!g.sampleWritten(10,false,1)) }
    test("stop cannot resurrect") { val g=RecordingStartGate(); g.stop(); check(!g.sampleWritten(10,false,0)) }
    test("short clip not cadence proof") { check(FrameSummary(10,300_000,30.0,0,0).cadenceStatus(30)=="insufficient_duration") }
    test("slow cadence warned") { check(FrameSummary(300,10_000_000,28.83,0,0).cadenceStatus(30)=="warning") }
    test("good cadence accepted") { check(FrameSummary(301,10_000_000,30.0,0,0).cadenceStatus(30)=="within_tolerance") }
    test("reports stay advertised") { check(mode.describe()["evidence"] == "advertised_candidate" && mode.describe()["customLog"] == false) }
    println("$passed policy checks passed")
}
