package com.s23log.probe.core

import org.json.JSONObject

object CapturePairing {
    /** Historical reports without a byte identity cannot establish a matched export. */
    fun matches(report: JSONObject, actual: MediaIdentity): Boolean {
        if (report.optString("kind") != "recording-validation") return false
        val expected = report.optJSONObject("verification")?.optJSONObject("mediaIdentity") ?: return false
        val bytes = expected.opt("byteCount")
        if (bytes !is Long && bytes !is Int) return false
        return expected.optString("algorithm") == "SHA-256" && expected.opt("sha256") == actual.sha256 &&
            (bytes as Number).toLong() == actual.byteCount && actual.byteCount > 0
    }
}
