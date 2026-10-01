package cinema.reference

import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.abs
import kotlin.math.max

/** Single-owner lease. Concurrent close is idempotent; do not use a borrowed value after transfer/close. */
class FrameLease<T>(private val value: T, private val release: () -> Unit) : AutoCloseable {
    private val closed = AtomicBoolean(false)
    fun get(): T {
        check(!closed.get()) { "Lease already released" }
        return value
    }
    override fun close() {
        if (closed.compareAndSet(false, true)) release()
    }
}

/** Nonblocking admission gate. This counts leases, not bytes; production also needs a byte budget. */
class LeasePool(private val capacity: Int) {
    private val active = AtomicInteger(0)
    init { require(capacity > 0) { "Capacity must be positive" } }
    fun <T> tryAcquire(value: T, release: () -> Unit = {}): FrameLease<T>? {
        while (true) {
            val count = active.get()
            if (count >= capacity) return null
            if (active.compareAndSet(count, count + 1)) break
        }
        return FrameLease(value) {
            try { release() }
            finally { check(active.decrementAndGet() >= 0) { "Lease accounting underflow" } }
        }
    }
    fun inUse(): Int = active.get()
}

/** Exact integer floor of frameIndex * 1e6 * denominator / numerator; overflow fails explicitly. */
fun presentationUs(index: Long, numerator: Long, denominator: Long): Long {
    require(index >= 0 && numerator > 0 && denominator > 0)
    val scaled = Math.multiplyExact(Math.multiplyExact(index, 1_000_000L), denominator)
    return scaled / numerator
}

enum class Origin { RAW, HLG, SDR }
fun validateLabel(origin: Origin, label: String) {
    val expected = when (origin) {
        Origin.RAW -> "raw-derived"
        Origin.HLG -> "hdr-derived"
        Origin.SDR -> "sdr-derived"
    }
    require(label == expected) { "Origin $origin cannot support label $label" }
}

/** Minimal test descriptor, not the full production contract documented in the directive. */
data class Signal(val primaries: String, val transfer: String, val bits: Int) {
    init { require(primaries.isNotBlank() && transfer.isNotBlank() && bits > 0) }
}
fun requireCompatible(output: Signal, input: Signal) {
    require(output == input) { "Insert an explicit conversion node: $output -> $input" }
}

data class ManualTarget(val generation: Long, val exposureNs: Long, val iso: Int) {
    init { require(generation >= 0 && exposureNs > 0 && iso > 0) }
}
data class ManualResult(val generation: Long, val exposureNs: Long?, val iso: Int?, val aeOff: Boolean)

/** Example 2% policy only. Actual device acceptance requires its own versioned tolerance and freshness rule. */
fun manualReady(target: ManualTarget, result: ManualResult): Boolean {
    val exposure = result.exposureNs ?: return false
    val sensitivity = result.iso ?: return false
    if (result.generation != target.generation || !result.aeOff || exposure <= 0 || sensitivity <= 0) return false
    val exposureError = abs(exposure.toDouble() - target.exposureNs.toDouble())
    val isoError = abs(sensitivity.toDouble() - target.iso.toDouble())
    return exposureError <= max(1.0, target.exposureNs.toDouble() * 0.02) &&
        isoError <= max(1.0, target.iso.toDouble() * 0.02)
}

/** Signed ideal thin-lens CoC diameter in mm. fNumber is geometric N, not a T-stop. */
fun cocMm(focal: Double, fNumber: Double, focus: Double, subject: Double): Double {
    require(focal.isFinite() && focal > 0)
    require(fNumber.isFinite() && fNumber > 0)
    require(focus.isFinite() && focus > focal)
    require((subject.isFinite() && subject > focal) || subject == Double.POSITIVE_INFINITY)
    val result = focal * focal / (fNumber * (focus - focal)) * (1.0 - focus / subject)
    require(result.isFinite()) { "Nonfinite optical result" }
    return result
}
