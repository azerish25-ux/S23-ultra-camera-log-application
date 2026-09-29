import com.s23log.probe.core.*
import java.nio.ByteBuffer
import java.util.concurrent.atomic.AtomicInteger

/** Standalone execution of production reader/handoff policies; not a replacement for Android CI. */
fun main() {
    var checks = 0
    fun test(label: String, body: () -> Unit) { body(); checks++; println("PASS $label") }
    fun await(body: () -> Boolean) {
        val end = System.nanoTime() + 2_000_000_000
        while (!body() && System.nanoTime() < end) Thread.sleep(2)
        check(body())
    }
    class Input(val total: Int) : MicrophoneReader.Source {
        var position = 0; val closed = AtomicInteger(); val starts = AtomicInteger()
        override fun start() { starts.incrementAndGet() }
        override fun read(samples: ShortArray, count: Int): Int {
            val n = minOf(1024, count, total - position)
            repeat(n) { samples[it] = (position + it).toShort() }; position += n; return n
        }
        override fun timestamp(): MicrophoneReader.Stamp? = null
        override fun inspect() = Unit
        override fun close() { closed.incrementAndGet() }
    }
    test("consumer pause does not stop acquisition; native owner closes") {
        val input = Input(8193); val pipe = PcmHandoff(1); val c = PcmClock(48000, true)
        val reader = MicrophoneReader(1, 9600, input, pipe, c, {})
        try {
            reader.start(); await { pipe.describe()["acceptedFrames"] == 8193L }
            check(pipe.describe()["consumedFrames"] == 0L)
            reader.requestStop(); await { reader.done }; check(reader.failure == null)
            var consumed = 0; var padding = 0
            while (pipe.ready()) { val b = requireNotNull(pipe.drain(ByteBuffer.allocate(2048))); consumed += b.frames; padding += b.paddingFrames }
            check(consumed == 8193 && padding == 1023 && input.closed.get() == 1)
        } finally { reader.cancel(); await { reader.done } }
    }
    test("saturation fails with retained queue and explicit unread accounting") {
        val input = Input(4096); val pipe = PcmHandoff(1, 2048)
        val reader = MicrophoneReader(1, 9600, input, pipe, PcmClock(48000), {})
        reader.start(); await { reader.done }
        check(reader.failure != null && pipe.describe()["overflowCount"] == 1)
        check(pipe.describe()["acceptedFrames"] == 2048L && reader.framesRead == 3072L)
    }
    test("cancel before launch never opens input") {
        val input = Input(50); val r = MicrophoneReader(1, 9600, input, PcmHandoff(1), PcmClock(48000), {})
        r.cancel(); await { r.done }; check(input.starts.get() == 0 && input.closed.get() == 1)
    }
    test("qualified startup is not first-timestamp optimism") {
        val c = PcmClock(48000, true); c.observe(0,1000000000); check(!c.anchored)
        c.observe(2400,1050000000); c.observe(4800,1100000000)
        check(c.quality() == "stable_nominal_clock" && c.frameAt(1100000000) == 4800L)
    }
    test("high-frequency native timestamps qualify without shortening the 100 ms window") {
        for (step in listOf(1, 2, 5, 10, 16, 20, 50)) {
            val c = PcmClock(48000, true)
            for (ms in 0..250 step step) {
                c.observe(48L * ms, 1_000_000_000L + ms * 1_000_000L)
                check(c.anchored == (ms >= 100))
            }
            check(c.quality() == "stable_nominal_clock" && c.anchorNs == 1_000_000_000L)
        }
    }
    test("a changed startup origin requires a fresh stable interval") {
        val c = PcmClock(48000, true)
        for (ms in 0..59) c.observe(48L * ms, 1_000_000_000L + ms * 1_000_000L)
        for (ms in 60..159) {
            c.observe(48L * ms, 1_005_000_000L + ms * 1_000_000L)
            check(!c.anchored)
        }
        c.observe(7680, 1_165_000_000L)
        check(c.anchored && c.anchorNs == 1_005_000_000L)
    }
    test("timestamp jump and smooth rate deviation remain distinct") {
        val c = PcmClock(48000); c.observe(0,1000000000)
        for (s in 1L..60) c.observe(48000*s,1000000000+1001000000*s)
        check(c.quality() == "clock_rate_deviation" && c.timestampUs(48000*60L) == 61000000L)
        c.observe(48000*61L,62_150_000_000); check(c.quality() == "timestamp_discontinuity_suspected")
    }
    println("$checks acquisition/timing scenarios passed")
}
