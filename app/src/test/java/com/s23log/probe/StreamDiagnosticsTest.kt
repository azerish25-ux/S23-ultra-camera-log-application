package com.s23log.probe

import com.s23log.probe.diagnostics.*
import org.junit.Assert.*
import org.junit.Test

class StreamDiagnosticsTest {
    private class Queries : StreamDiagnostics.Queries {
        var discoveryFail = false
        var codecFail = false
        var failedFormat = -1
        var timingFail = false
        override fun formats(): List<Int> { check(!discoveryFail); return (1..6).toList() }
        override fun sizes(format: Int): List<StreamDiagnostics.Size> { check(format != failedFormat); return (1..40).map { StreamDiagnostics.Size(it * 100, it * 50) } }
        override fun minimumDuration(format: Int, size: StreamDiagnostics.Size): Long { check(!timingFail); return 33_333_333 }
        override fun stallDuration(format: Int, size: StreamDiagnostics.Size) = 0L
        override fun codecSizes(): List<String> { check(!codecFail); return listOf("1920x1080") }
    }
    @Test fun optionalCodecFailureKeepsAllSixFormatsAndFortySizes() {
        val rows = StreamDiagnostics.collect(Queries().apply { codecFail = true }, emptyList())
        assertEquals(7, rows.size)
        assertEquals(6, rows.count { it["status"] == "reported" })
        rows.take(6).forEach { assertEquals(40, (it["outputs"] as List<*>).size) }
        assertEquals("query_failed", rows.last()["status"])
        assertEquals(1, nestedQueryErrors(rows))
    }
    @Test fun enumerationFailureStillUsesFallbackFormats() {
        val rows = StreamDiagnostics.collect(Queries().apply { discoveryFail = true }, listOf(1, 2, 3))
        assertEquals(5, rows.size)
        assertEquals(3, rows.count { it.containsKey("format") })
        assertEquals(1, nestedQueryErrors(rows))
    }
    @Test fun oneFormatFailureDoesNotLoseOtherRows() {
        val rows = StreamDiagnostics.collect(Queries().apply { failedFormat = 2 }, emptyList())
        assertEquals(7, rows.size)
        assertEquals(1, rows.count { it["status"] == "query_failed" })
        assertEquals("reported", rows.last()["status"])
    }
    @Test fun nestedTimingErrorsCountButKeepDimensionsAndStallTiming() {
        val rows = StreamDiagnostics.collect(Queries().apply { timingFail = true }, emptyList())
        assertEquals(240, nestedQueryErrors(rows))
        val item = (rows.first()["outputs"] as List<*>).first() as Map<*, *>
        assertEquals(4000, item["width"])
        assertEquals(0L, item["stallDurationNs"])
    }
    @Test fun reportIncludesNestedErrorsExactlyOnce() {
        val section = ProbeSection("camera", "test")
        section.query("streams") { StreamDiagnostics.collect(Queries().apply { codecFail = true }, emptyList()) }
        section.query("other") { error("separate") }
        val report = ProbeReport("test", listOf(section))
        assertEquals(2, report.errorCount)
        assertTrue(report.text().contains("Query errors: 2"))
    }
}
