package com.s23log.probe

import com.s23log.probe.storage.ClipDetails
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class ClipDetailsTest {
    @Test fun requestedModeNeverSubstitutesForRecordedMeasurements() {
        val report = JSONObject().put("selectedMode", JSONObject().put("width", 7680).put("fps", 30).put("mime", "video/hevc"))
        val details = ClipDetails.from(report)
        assertNull(details.width); assertNull(details.mime); assertNull(details.measuredFps)
        assertEquals(30, details.targetFps); assertEquals("unknown", details.status)
    }
    @Test fun preservesCadenceWarningAndActualDimensions() {
        val report = JSONObject().put("status", "checked").put("selectedMode", JSONObject().put("fps", 30))
            .put("verification", JSONObject().put("width", 1280).put("height", 720).put("mime", "video/avc")
                .put("measuredFps", 28.5).put("cadenceStatus", "warning").put("colorTransfer", 3))
        val details = ClipDetails.from(report)
        assertEquals(1280, details.width); assertEquals(28.5, details.measuredFps!!, 0.0)
        assertEquals("warning", details.cadence); assertNull(details.lumaBitDepth)
    }
    @Test fun missingReportCannotBecomeChecked() {
        val details = ClipDetails.from(null)
        assertEquals("unknown", details.status); assertNull(details.targetFps)
    }
    @Test fun invalidMeasurementsStayUnknown() {
        val details = ClipDetails.from(JSONObject().put("verification", JSONObject().put("width", -1).put("measuredFps", "NaN")))
        assertNull(details.width); assertNull(details.measuredFps)
    }
}
