import com.s23log.probe.core.*
import com.s23log.probe.core.AvMuxCoordinator.Track
import java.nio.ByteBuffer

/** Offline checks of the same production policies; Gradle/JUnit and Android CI remain separate. */
fun main() {
    var count = 0
    fun test(name: String, block: () -> Unit) { block(); count++; println("PASS $name") }
    class Sink : AvMuxCoordinator.Sink<String> {
        var starts = 0; val writes = mutableListOf<Pair<Track, Long>>()
        override fun start(formats: Map<Track, String>) { starts++ }
        override fun write(track: Track, buffer: ByteBuffer, ptsUs: Long, flags: Int) { writes += track to ptsUs }
    }
    fun packet() = ByteBuffer.wrap(byteArrayOf(1,2,3))
    test("explicit video-only") { check(!AudioMode.OFF.enabled && AudioMode.fromStored("OFF") == AudioMode.OFF) }
    test("unknown preference does not mute") { check(AudioMode.fromStored(null).enabled) }
    test("exact 48 kHz clock for ten minutes") { val c=PcmClock(48000); c.observe(4800,2100000000); check(c.timestampUs(0)==2000000L); check(c.timestampUs(28800000)==602000000L) }
    test("drift does not rewrite timestamps") { val c=PcmClock(48000); c.observe(0,1000000000); c.observe(48000,2005000000); check(c.maxDriftUs==5000L && c.timestampUs(48000)==2000000L) }
    test("estimated clock stays unverified") { val c=PcmClock(48000); c.estimate(0,1000000000); c.observe(48000,2000000000); check(c.source.endsWith("unverified")) }
    test("stereo clipping and silence separated") { val levels=PcmLevels.measure(shortArrayOf(-32768,0),2,2); check(levels[0].clipped && levels[1].meter==0) }
    test("AAC mono and stereo headers") { check(AacLcConfig.matches(byteArrayOf(0x11,0x88.toByte()),48000,1)); check(AacLcConfig.matches(byteArrayOf(0x11,0x90.toByte()),48000,2)) }
    test("AAC wrong channels rejected") { check(!AacLcConfig.matches(byteArrayOf(0x11,0x90.toByte()),48000,1)) }
    test("common epoch keeps 20 ms track offset") {
        val sink=Sink(); val mux=AvMuxCoordinator(true,sink,{ _,_,_-> })
        mux.format(Track.VIDEO,"v"); mux.sample(Track.VIDEO,packet(),1000000,0); check(sink.starts==0)
        mux.format(Track.AUDIO,"a"); check(sink.starts==0); mux.sample(Track.AUDIO,packet(),1020000,0)
        check(sink.writes.map { it.second }==listOf(0L,20000L))
    }
    test("missing audio is recovery not success") { val sink=Sink(); val mux=AvMuxCoordinator(true,sink,{ _,_,_-> }); mux.format(Track.VIDEO,"v"); mux.sample(Track.VIDEO,packet(),1,0); check(mux.finish() && sink.writes.size==1) }
    test("startup queue bounded") { val mux=AvMuxCoordinator(true,Sink(),{ _,_,_-> },maxPendingBytes=3); mux.sample(Track.VIDEO,packet(),1,0); check(runCatching { mux.sample(Track.VIDEO,packet(),2,0) }.isFailure) }
    test("stopped gate cannot acknowledge late audio") { val g=AvStartGate(true); check(!g.written(Track.VIDEO)); g.stop(); check(!g.written(Track.AUDIO)) }
    test("unrelated clocks not faked") {
        val sink=Sink(); val mux=AvMuxCoordinator(true,sink,{ _,_,_-> }); mux.format(Track.VIDEO,"v"); mux.format(Track.AUDIO,"a")
        mux.sample(Track.VIDEO,packet(),1,0); check(runCatching { mux.sample(Track.AUDIO,packet(),9000000,0) }.isFailure)
        check(mux.finish() && sink.writes.all { it.first==Track.VIDEO })
    }
    println("$count audio policy checks passed")
}
