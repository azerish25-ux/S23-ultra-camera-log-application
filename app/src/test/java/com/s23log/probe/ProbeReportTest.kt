package com.s23log.probe

import com.s23log.probe.diagnostics.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files

class ProbeReportTest {
    @Test fun allFortyResolutionsSurviveJsonAndTextExport() {
        val section = ProbeSection("camera", "0")
        section.query("sizes") { (1..40).map { "${it}x${it}" } }
        val report = ProbeReport("test", listOf(section))
        val json = JSONObject(report.json())
        assertEquals(40, json.getJSONArray("sections").getJSONObject(0).getJSONObject("fields").getJSONObject("sizes").getJSONArray("value").length())
        assertTrue(report.text().contains("40x40")); assertTrue(report.text().contains("1x1"))
    }
    @Test fun failingPropertyDoesNotDiscardItsNeighbors() {
        val section = ProbeSection("camera", "0")
        section.query("before") { true }; section.query("bad") { error("vendor error") }; section.query("after") { 7 }
        val report = ProbeReport("test", listOf(section))
        assertEquals(1, report.errorCount); assertEquals(7, section.fields["after"]!!.value)
        assertTrue(report.text().contains("vendor error")); assertTrue(report.json().contains("before"))
    }
    @Test fun nullUnsupportedAndFailureRemainDistinct() {
        val section = ProbeSection("camera", "0")
        section.query("null") { null }; section.unavailable("oldApi", "requires API 33"); section.query("bad") { throw SecurityException("denied") }
        assertEquals("not_reported", section.fields["null"]!!.status)
        assertEquals("unsupported", section.fields["oldApi"]!!.status)
        assertEquals("query_failed", section.fields["bad"]!!.status)
    }
    @Test fun jsonCarriesVersionAndEvidenceLevel() {
        val report = JSONObject(ProbeReport("test", emptyList()).json())
        assertEquals(2, report.getInt("schemaVersion")); assertEquals("advertised_only", report.getString("evidence"))
    }
    @Test fun stringsAreEscapedAndNumbersStayNumeric() {
        val section = ProbeSection("camera", "quoted\"")
        section.query("value") { mapOf("quoted" to "line\n\"value\"", "number" to 5) }
        val values = JSONObject(ProbeReport("test", listOf(section)).json()).getJSONArray("sections").getJSONObject(0).getJSONObject("fields").getJSONObject("value").getJSONObject("value")
        assertEquals(5, values.getInt("number")); assertEquals("line\n\"value\"", values.getString("quoted"))
    }
    @Test fun atomicWriteReplacesAndLeavesNoTemporaryFiles() {
        val directory = Files.createTempDirectory("report-test").toFile()
        try {
            val file = java.io.File(directory, "report.txt")
            atomicWrite(file, "old"); atomicWrite(file, "new")
            assertEquals("new", file.readText()); assertEquals(listOf("report.txt"), directory.list()!!.toList())
        } finally { directory.deleteRecursively() }
    }
}
