package com.s23log.probe

import com.s23log.probe.storage.CapturePairing
import com.s23log.probe.core.MediaIdentity
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class CapturePairingTest {
    private val identity = MediaIdentity("a".repeat(64), 123)
    private fun report() = JSONObject().put("kind", "recording-validation").put("verification",
        JSONObject().put("mediaIdentity", JSONObject(identity.describe())))
    @Test fun matchesOriginalBytes() { assertTrue(CapturePairing.matches(report(), identity)) }
    @Test fun logReportsRequireTheSameOriginalByteIdentity() {
        for (kind in listOf("raw-derived-logc3", "live-raw-logc3")) {
            assertTrue(CapturePairing.matches(report().put("kind",kind),identity))
            assertFalse(CapturePairing.matches(report().put("kind",kind),identity.copy(byteCount=124)))
        }
    }
    @Test fun logLabelDoesNotReplaceMissingIdentity() {
        assertFalse(CapturePairing.matches(JSONObject().put("kind","live-raw-logc3").put("status","container_checked"),identity))
    }
    @Test fun rejectsChangedBytes() { assertFalse(CapturePairing.matches(report(), identity.copy(sha256 = "b".repeat(64)))) }
    @Test fun rejectsChangedLength() { assertFalse(CapturePairing.matches(report(), identity.copy(byteCount = 124))) }
    @Test fun historicalReportIsNotSilentlyCertified() { assertFalse(CapturePairing.matches(JSONObject().put("kind", "recording-validation"), identity)) }
    @Test fun rejectsWrongReportAndCoercedSize() {
        assertFalse(CapturePairing.matches(report().put("kind", "raw-validation"), identity))
        val report = report()
        report.getJSONObject("verification").getJSONObject("mediaIdentity").put("byteCount", "123")
        assertFalse(CapturePairing.matches(report, identity))
    }
}
