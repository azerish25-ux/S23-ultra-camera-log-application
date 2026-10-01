package cinema.reference

import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread
import kotlin.math.abs

private var passed = 0
private var failed = 0
private fun test(name: String, body: () -> Unit) {
    try { body(); passed++; println("PASS $name") }
    catch (e: Throwable) { failed++; println("FAIL $name: ${e::class.simpleName}: ${e.message}") }
}
private inline fun <reified T: Throwable> expectFailure(body: () -> Unit) {
    try { body() } catch (e: Throwable) {
        check(e is T) { "Expected ${T::class.simpleName}, received ${e::class.simpleName}" }
        return
    }
    error("Expected ${T::class.simpleName}")
}
fun main() {
    test("lease exposes the owned value before release") {
        val lease = FrameLease("frame") {}; check(lease.get() == "frame"); lease.close()
    }
    test("lease refuses access after release") {
        val lease = FrameLease(7) {}; lease.close()
        expectFailure<IllegalStateException> { lease.get() }
    }
    test("lease callback executes once") {
        val calls = AtomicInteger(); val lease = FrameLease(3) { calls.incrementAndGet() }
        lease.close(); lease.close(); check(calls.get() == 1)
    }
    test("concurrent closes release exactly once") {
        val calls = AtomicInteger(); val lease = FrameLease(3) { calls.incrementAndGet() }
        val start = CountDownLatch(1)
        val errors = ConcurrentLinkedQueue<Throwable>()
        val workers = List(12) { thread(start = true) {
            try { check(start.await(5, TimeUnit.SECONDS)); lease.close() } catch (e:Throwable) { errors.add(e) }
        } }
        start.countDown(); workers.forEach { it.join(5000); check(!it.isAlive) }
        check(errors.isEmpty()) { "Worker failure: ${errors.peek()}" }; check(calls.get() == 1)
    }
    test("throwing release still leaves lease closed") {
        val lease = FrameLease(3) { throw IllegalStateException("release failed") }
        expectFailure<IllegalStateException> { lease.close() }
        expectFailure<IllegalStateException> { lease.get() }; lease.close()
    }
    test("pool rejects nonpositive capacity") {
        expectFailure<IllegalArgumentException> { LeasePool(0) }
    }
    test("pool refuses an excess lease") {
        val pool = LeasePool(1); val first = checkNotNull(pool.tryAcquire("a"))
        check(pool.tryAcquire("b") == null); first.close()
    }
    test("pool capacity returns on close") {
        val pool = LeasePool(1); checkNotNull(pool.tryAcquire("a")).close()
        checkNotNull(pool.tryAcquire("b")).close(); check(pool.inUse() == 0)
    }
    test("double close cannot underflow pool") {
        val pool = LeasePool(1); val lease = checkNotNull(pool.tryAcquire("a"))
        lease.close(); lease.close(); check(pool.inUse() == 0)
    }
    test("failing resource callback restores capacity") {
        val pool = LeasePool(1)
        val lease = checkNotNull(pool.tryAcquire("a") { throw IllegalStateException("fault") })
        expectFailure<IllegalStateException> { lease.close() }; check(pool.inUse() == 0)
    }
    test("concurrent pool admissions remain bounded") {
        val pool = LeasePool(3); val start = CountDownLatch(1); val acquired = CountDownLatch(20)
        val release = CountDownLatch(1); val accepted = AtomicInteger()
        val errors = ConcurrentLinkedQueue<Throwable>()
        val workers = List(20) { number -> thread {
            var lease:FrameLease<Int>? = null
            try {
                check(start.await(5, TimeUnit.SECONDS)); lease = pool.tryAcquire(number)
                if (lease != null) accepted.incrementAndGet()
            } catch (e:Throwable) { errors.add(e) }
            finally { acquired.countDown() }
            try { check(release.await(5, TimeUnit.SECONDS)); lease?.close() }
            catch (e:Throwable) { errors.add(e) }
        } }
        start.countDown()
        try {
            check(acquired.await(5, TimeUnit.SECONDS)); check(errors.isEmpty()) { "Worker failure: ${errors.peek()}" }
            check(accepted.get() == 3); check(pool.inUse() == 3)
        } finally {
            release.countDown(); workers.forEach { it.join(5000); check(!it.isAlive) }
        }
        check(errors.isEmpty()); check(pool.inUse() == 0)
    }
    test("rational timestamp starts at zero") { check(presentationUs(0, 24, 1) == 0L) }
    test("rational timestamp does not accumulate rounded intervals") {
        check(presentationUs(24000, 24000, 1001) == 1001000000L)
    }
    test("rational timestamp floors exact fraction") { check(presentationUs(1, 24, 1) == 41666L) }
    test("rational timestamp rejects invalid rates") {
        expectFailure<IllegalArgumentException> { presentationUs(1, 0, 1) }
        expectFailure<IllegalArgumentException> { presentationUs(-1, 24, 1) }
    }
    test("rational timestamp reports overflow") {
        expectFailure<ArithmeticException> { presentationUs(Long.MAX_VALUE, 24, 1001) }
    }
    test("RAW-derived label requires RAW origin") { validateLabel(Origin.RAW, "raw-derived") }
    test("SDR cannot be promoted by an output label") {
        expectFailure<IllegalArgumentException> { validateLabel(Origin.SDR, "raw-derived") }
    }
    test("HLG remains HDR-derived") { validateLabel(Origin.HLG, "hdr-derived") }
    test("HLG does not become proprietary Samsung Log") {
        expectFailure<IllegalArgumentException> { validateLabel(Origin.HLG, "native-samsung-log") }
    }
    test("graph rejects incompatible transfer contracts") {
        val a = Signal("AWG3", "LINEAR", 16); val b = Signal("AWG3", "LOGC3", 16)
        expectFailure<IllegalArgumentException> { requireCompatible(a, b) }
    }
    test("graph rejects a hidden precision change") {
        expectFailure<IllegalArgumentException> {
            requireCompatible(Signal("AWG3", "LINEAR", 16), Signal("AWG3", "LINEAR", 8))
        }
    }
    test("graph accepts identical declared signals") {
        val a = Signal("AWG3", "LINEAR", 16); requireCompatible(a, a)
    }
    test("manual readiness requires current matching generation") {
        check(!manualReady(ManualTarget(5, 10000000, 100), ManualResult(4, 10000000, 100, true)))
    }
    test("AE-off alone does not establish exposure match") {
        check(!manualReady(ManualTarget(5, 10000000, 100), ManualResult(5, 20000000, 100, true)))
    }
    test("missing manual metadata stays unready") {
        check(!manualReady(ManualTarget(5, 10000000, 100), ManualResult(5, null, 100, true)))
    }
    test("matching manual result establishes model readiness") {
        check(manualReady(ManualTarget(5, 10000000, 100), ManualResult(5, 10000000, 100, true)))
    }
    test("active auto exposure blocks manual readiness") {
        check(!manualReady(ManualTarget(5, 10000000, 100), ManualResult(5, 10000000, 100, false)))
    }
    test("focus plane has zero geometric blur") { check(abs(cocMm(50.0, 2.0, 2000.0, 2000.0)) < 1e-12) }
    test("infinity has finite signed geometric blur") {
        check(abs(cocMm(50.0, 2.0, 2000.0, Double.POSITIVE_INFINITY) - 0.6410256410256411) < 1e-12)
    }
    test("foreground and background blur retain opposite signs") {
        check(cocMm(50.0, 2.0, 2000.0, 1000.0) < 0)
        check(cocMm(50.0, 2.0, 2000.0, 4000.0) > 0)
    }
    test("optics rejects NaN and impossible focus geometry") {
        expectFailure<IllegalArgumentException> { cocMm(50.0, Double.NaN, 2000.0, 1000.0) }
        expectFailure<IllegalArgumentException> { cocMm(50.0, 2.0, 40.0, 1000.0) }
    }
    println("RESULT passed=$passed failed=$failed")
    check(failed == 0) { "$failed contract tests failed" }
}
