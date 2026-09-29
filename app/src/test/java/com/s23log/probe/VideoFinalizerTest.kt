package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test

class VideoFinalizerTest {
    private class Fixture {
        val calls = mutableListOf<String>()
        var samples = 3
        var initialError: Exception? = null
        var verificationError = false
        var publicationError = false
        var retentionError = false
        var reportError = false
        var discardError = false
        fun finish() = VideoFinalizer.finish(samples, initialError,
            verify = { calls += "verify"; check(!verificationError) { "bad format" }; "verification" },
            publish = { calls += "publish"; check(!publicationError) { "gallery full" }; "gallery" },
            retain = { reason -> calls += "retain"; assertTrue(reason.isNotEmpty()); check(!retentionError); "private" },
            discardEmpty = { calls += "discard"; check(!discardError) },
            saveReport = { calls += "report"; check(!reportError) { "report directory full" } })
    }
    @Test fun verifiedVideoPublishesBeforeAuxiliaryReport() {
        val f = Fixture(); val result = f.finish()
        assertEquals(listOf("verify", "publish", "report"), f.calls)
        assertEquals(VideoDisposition.PUBLISHED, result.disposition)
        assertEquals("gallery", result.uri)
        assertNull(result.reportError)
    }
    @Test fun reportFailureNeverDeletesPublishedVideo() {
        val f = Fixture().apply { reportError = true }; val result = f.finish()
        assertEquals(VideoDisposition.PUBLISHED, result.disposition)
        assertEquals("gallery", result.uri)
        assertNotNull(result.reportError)
        assertFalse(f.calls.contains("discard"))
    }
    @Test fun failedPublicationRetainsOriginal() {
        val f = Fixture().apply { publicationError = true }; val result = f.finish()
        assertEquals(VideoDisposition.RECOVERABLE, result.disposition)
        assertEquals("private", result.uri)
        assertEquals(listOf("verify", "publish", "retain", "report"), f.calls)
    }
    @Test fun invalidOutputIsPrivateNotAdvertisedAsChecked() {
        val f = Fixture().apply { verificationError = true }; val result = f.finish()
        assertEquals(VideoDisposition.RECOVERABLE, result.disposition)
        assertNull(result.verification)
        assertFalse(f.calls.contains("publish"))
        assertFalse(f.calls.contains("discard"))
    }
    @Test fun interruptedEncodingRetainsEvenIfFileDecodes() {
        val f = Fixture().apply { initialError = IllegalStateException("encoder interrupted") }; val result = f.finish()
        assertEquals(VideoDisposition.RECOVERABLE, result.disposition)
        assertEquals("verification", result.verification)
        assertFalse(f.calls.contains("publish"))
    }
    @Test fun oneFrameIsNotDiscarded() {
        val f = Fixture().apply { samples = 1; verificationError = true }
        assertEquals(VideoDisposition.RECOVERABLE, f.finish().disposition)
        assertFalse(f.calls.contains("discard"))
    }
    @Test fun trulyEmptyCaptureCanBeDiscarded() {
        val f = Fixture().apply { samples = 0 }
        assertEquals(VideoDisposition.EMPTY, f.finish().disposition)
        assertEquals(listOf("discard", "report"), f.calls)
    }
    @Test fun emptyCleanupFailureStillReports() {
        val f = Fixture().apply { samples = 0; discardError = true }
        assertEquals(VideoDisposition.EMPTY, f.finish().disposition)
        assertEquals("report", f.calls.last())
    }
    @Test fun retentionFailureDoesNotFallThroughToDeletion() {
        val f = Fixture().apply { verificationError = true; retentionError = true }
        val result = f.finish()
        assertEquals(VideoDisposition.RETENTION_FAILED, result.disposition)
        assertNull(result.uri)
        assertFalse(f.calls.contains("discard"))
    }
    @Test fun simultaneousReportAndFormatFailuresKeepFootage() {
        val f = Fixture().apply { verificationError = true; reportError = true }
        val result = f.finish()
        assertEquals(VideoDisposition.RECOVERABLE, result.disposition)
        assertNotNull(result.reportError)
        assertEquals("private", result.uri)
    }
    @Test fun simultaneousPublicationAndReportFailuresKeepFootage() {
        val f = Fixture().apply { publicationError = true; reportError = true }
        assertEquals("private", f.finish().uri)
        assertFalse(f.calls.contains("discard"))
    }
}
