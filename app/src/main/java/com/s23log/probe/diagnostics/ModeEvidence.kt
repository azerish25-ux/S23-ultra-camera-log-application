package com.s23log.probe.diagnostics

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import com.s23log.probe.BuildConfig
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.camera.CameraTarget
import com.s23log.probe.camera.ModePlan
import org.json.JSONObject
import java.io.File
import java.util.UUID
import java.util.concurrent.Executors

/** Capability evidence is separate from actual recordings, and never promotes a mode to certified. */
object ModeEvidence {
    private val worker = Executors.newSingleThreadExecutor()
    fun device(): Map<String, Any> = mapOf("manufacturer" to Build.MANUFACTURER, "model" to Build.MODEL,
        "device" to Build.DEVICE, "fingerprint" to Build.FINGERPRINT, "sdk" to Build.VERSION.SDK_INT,
        "appVersion" to BuildConfig.VERSION_NAME, "appCommit" to BuildConfig.SOURCE_REVISION)
    fun report(target: CameraTarget, plan: ModePlan): JSONObject = JSONObject()
        .put("schemaVersion", 1).put("kind", "recording-mode-plan").put("device", jsonValue(device()))
        .put("reportId", UUID.randomUUID().toString()).put("generatedAt", java.time.Instant.now().toString())
        .put("evidence", "advertised_only").put("physicalCameraCertified", false)
        .put("logicalCamera", target.logicalId).put("physicalCamera", target.physicalId ?: JSONObject.NULL)
        .put("plan", jsonValue(plan.describe()))
    /** Preserve only the actual selected planner candidate, not an invented capability assertion. */
    fun recordingSnapshot(target: CameraTarget, plan: ModePlan?, mode: RecordingMode): JSONObject? =
        plan?.takeIf { mode in it.modes }?.let {
            report(target, ModePlan(listOf(mode), it.notes)).put("scope", "Selected planner subset; not full capability audit")
        }

    fun recordingAttempt(context: Context, mode: RecordingMode, audioMode: AudioMode,
                         requested: Map<String, Any?>): RecordingAttempt {
        val app = context.applicationContext
        val bound = JSONObject().put("device", jsonValue(device())).put("selectedMode", jsonValue(mode.describe()))
            .put("audioMode", audioMode.name).put("audioChannels", audioMode.channels)
            .put("requested", jsonValue(requested.filterKeys { it != "capabilitySnapshot" }))
        return RecordingAttempt(File(app.filesDir, "exports/recording-evidence"), BuildConfig.SOURCE_REVISION, bound,
            ::atomicWrite, schedule = { task -> worker.execute { task() } }, onPersistenceFailure = { message ->
                Handler(Looper.getMainLooper()).post {
                    android.widget.Toast.makeText(app, "Recording report save failed; footage is unchanged: $message", android.widget.Toast.LENGTH_LONG).show()
                }
            }).also { it.start(); it.advertised(requested["capabilitySnapshot"] as? JSONObject) }
    }
    fun export(context: Context, target: CameraTarget, plan: ModePlan, completed: (Result<File>) -> Unit) {
        val app = context.applicationContext
        worker.execute {
            val result = runCatching {
                val directory = File(app.filesDir, "exports/modes")
                check(directory.isDirectory || directory.mkdirs()) { "Mode export directory unavailable" }
                val file = File(directory, "mode-plan-${UUID.randomUUID()}.json")
                atomicWrite(file, report(target, plan).toString(2))
                file
            }
            Handler(Looper.getMainLooper()).post { completed(result) }
        }
    }
}
