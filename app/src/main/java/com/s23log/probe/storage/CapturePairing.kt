package com.s23log.probe.storage

import org.json.JSONObject
import com.s23log.probe.core.MediaIdentity

object CapturePairing {
    /** Historical reports without a byte identity cannot establish a matched export. */
    fun matches(report: JSONObject, actual: MediaIdentity): Boolean {
        if (report.optString("kind") !in setOf("recording-validation", "raw-derived-logc3", "live-raw-logc3")) return false
        val expected = report.optJSONObject("verification")?.optJSONObject("mediaIdentity") ?: return false
        val bytes = expected.opt("byteCount")
        if (bytes !is Long && bytes !is Int) return false
        return expected.optString("algorithm") == "SHA-256" && expected.opt("sha256") == actual.sha256 &&
            (bytes as Number).toLong() == actual.byteCount && actual.byteCount > 0
    }
}
