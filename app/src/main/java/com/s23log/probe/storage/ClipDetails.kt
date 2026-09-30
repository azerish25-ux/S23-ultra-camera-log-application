package com.s23log.probe.storage

import org.json.JSONObject

/** Recorded measurements and requested settings stay separate; missing evidence stays unknown. */
data class ClipDetails(val width: Int?, val height: Int?, val mime: String?, val measuredFps: Double?,
    val targetFps: Int?, val transfer: Int?, val lumaBitDepth: Int?, val status: String, val cadence: String) {
    companion object {
        fun from(report: JSONObject?): ClipDetails {
            val measured = report?.optJSONObject("verification")
            fun positive(name: String) = measured?.optInt(name)?.takeIf { it > 0 }
            return ClipDetails(positive("width"), positive("height"), measured?.optString("mime")?.takeIf { it.isNotBlank() },
                measured?.optDouble("measuredFps")?.takeIf { it.isFinite() && it > 0 },
                report?.optJSONObject("selectedMode")?.optInt("fps")?.takeIf { it > 0 },
                measured?.optInt("colorTransfer")?.takeIf { it > 0 }, positive("lumaBitDepth"),
                report?.optString("status")?.takeIf { it.isNotBlank() } ?: "unknown",
                measured?.optString("cadenceStatus")?.takeIf { it.isNotBlank() } ?: "unknown")
        }
    }
}
