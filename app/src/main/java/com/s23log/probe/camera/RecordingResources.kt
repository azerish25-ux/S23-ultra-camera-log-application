package com.s23log.probe.camera

import android.content.Context
import android.os.Build
import android.os.PowerManager
import android.os.StatFs
import com.s23log.probe.R
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.core.RecordingResourcePolicy
import java.io.File

object RecordingResources {
    class PreflightRejected(val snapshot: Snapshot, message: String) : IllegalStateException(message)
    data class Snapshot(val availableBytes: Long?, val stagedBytes: Long, val publicationCopy: Boolean,
        val thermalStatus: Int?, val decision: RecordingResourcePolicy.Decision) {
        fun describe(): Map<String, Any?> = mapOf("availableBytes" to availableBytes, "stagedBytes" to stagedBytes,
            "publicationCopyBudgeted" to publicationCopy, "thermalStatus" to thermalStatus,
            "thermalStatusAvailable" to (thermalStatus != null), "requiredFreeBytes" to decision.requiredFreeBytes,
            "remainingSecondsEstimate" to decision.remainingSecondsEstimate, "stopReason" to decision.stopReason,
            "estimateIsGuarantee" to false, "physicalThermalCertification" to false)
    }

    fun read(context: Context, mode: RecordingMode, audio: AudioMode, stagedBytes: Long): Snapshot {
        fun available(file: File?): Long? = runCatching {
            file?.takeIf { it.isDirectory }?.let { StatFs(it.absolutePath).availableBytes }
        }.getOrNull()
        val internal = available(runCatching { context.filesDir }.getOrNull())
        val copy = Build.VERSION.SDK_INT >= 29
        val external = if (copy) available(runCatching { context.getExternalFilesDir(null) }.getOrNull()) else internal
        val free = if (internal == null || external == null) null else minOf(internal, external)
        val thermal = if (Build.VERSION.SDK_INT >= 29) runCatching {
            context.getSystemService(PowerManager::class.java)?.currentThermalStatus
        }.getOrNull() else null
        return Snapshot(free, stagedBytes, copy, thermal, RecordingResourcePolicy.assess(free, stagedBytes,
            mode.bitRate, if (audio.enabled) audio.bitRate else 0, copy, thermal))
    }

    fun stopMessage(context: Context, reason: String): String = context.getString(when (reason) {
        "thermal_severe" -> R.string.resource_stop_thermal
        "storage_reserve_reached" -> R.string.resource_stop_storage
        else -> R.string.resource_stop_unavailable
    })
}
