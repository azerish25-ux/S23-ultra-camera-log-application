package com.s23log.probe

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.camera2.CameraManager
import android.os.BatteryManager
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.os.StatFs
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.camera.CameraTarget
import com.s23log.probe.core.DynamicRange
import com.s23log.probe.core.ProcessingPath
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.time.Instant
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/** Test-only mechanics for P016. Production camera ownership stays in the existing engine. */
internal object P016PhysicalHarness {
    const val SETTINGS_NAME = "camera_settings_v1"
    const val BUNDLE_KIND = "p016-physical-capture-bundle"
    const val MARKER_PROTOCOL = "p016-flash-tone-v1"
    const val RECORDING_HOLD_MS = 65_000L
    const val MEDIA_NAME = "capture.mp4"
    const val VALIDATION_NAME = "recording-validation.json"
    const val ATTEMPT_NAME = "recording-attempt.json"
    const val MANIFEST_NAME = "device-capture.json"
    val MARKER_EVENTS_SECONDS = listOf(10, 20, 30, 40, 50, 60)

    data class Selection(
        val target: CameraTarget,
        val mode: RecordingMode,
        val catalogErrors: List<String>
    )

    data class CompletedCapture(
        val entry: CaptureHistory.Entry,
        val validationFile: File,
        val validation: JSONObject,
        val attemptFile: File,
        val attempt: JSONObject
    )

    data class Identity(val sha256: String, val byteCount: Long) {
        fun json(): JSONObject = JSONObject()
            .put("algorithm", "SHA-256")
            .put("sha256", sha256)
            .put("byteCount", byteCount)
    }

    fun requireArgument(arguments: Bundle, name: String): String =
        requireNotNull(arguments.getString(name)?.takeIf { it.isNotBlank() }) {
            "Missing instrumentation argument $name"
        }

    fun selectConservativeRearMode(context: Context): Selection {
        val manager = context.getSystemService(CameraManager::class.java)
        val catalog = CameraCatalog.discover(manager)
        val orderedTargets = catalog.targets
            .filterNot { it.front }
            .sortedWith(compareBy<CameraTarget> { it.physicalId != null }.thenBy { it.key })
        for (target in orderedTargets) {
            val modes = CameraCatalog.plan(target).modes.filter {
                it.range == DynamicRange.SDR &&
                    it.processing == ProcessingPath.DIRECT &&
                    !it.ratePlan.requiresManual &&
                    it.width <= 1920 && it.height <= 1080 && it.fps <= 30
            }
            if (modes.isEmpty()) continue
            val mode = modes.sortedWith(
                compareBy<RecordingMode> { modeRank(it) }
                    .thenByDescending { it.width.toLong() * it.height }
                    .thenByDescending { it.fps }
                    .thenBy { if (it.mime == "video/avc") 0 else 1 }
                    .thenBy { it.encoder }
            ).first()
            return Selection(target, mode, catalog.errors)
        }
        error("No conservative rear SDR direct <=1080p30 recording tuple is available")
    }

    private fun modeRank(mode: RecordingMode): Int = when {
        mode.width == 1920 && mode.height == 1080 && mode.fps == 30 -> 0
        mode.width == 1280 && mode.height == 720 && mode.fps == 30 -> 1
        mode.fps == 30 -> 2
        mode.fps == 24 -> 3
        else -> 4
    }

    fun await(
        scenario: ActivityScenario<MainActivity>,
        label: String,
        seconds: Long = 45,
        predicate: (MainActivity) -> Boolean
    ) {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(seconds)
        val success = AtomicBoolean(false)
        while (System.nanoTime() < deadline) {
            scenario.onActivity { success.set(predicate(it)) }
            if (success.get()) return
            Thread.sleep(150)
        }
        val status = AtomicReference("")
        scenario.onActivity { status.set(it.findViewById<TextView>(R.id.cameraStatus).text.toString()) }
        error("Timed out waiting for $label. Last camera state: ${status.get()}")
    }

    fun click(scenario: ActivityScenario<MainActivity>, id: Int) {
        scenario.onActivity { activity ->
            val button = activity.findViewById<Button>(id)
            require(button.isEnabled) {
                "${activity.resources.getResourceEntryName(id)} is disabled; state: " +
                    activity.findViewById<TextView>(R.id.cameraStatus).text
            }
            require(button.performClick()) { "Click was not accepted" }
        }
    }

    fun awaitCompletedCapture(context: Context, previousReport: String?): CompletedCapture {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(75)
        while (System.nanoTime() < deadline) {
            val entry = CaptureHistory.latest(context)
            val reportFile = entry.report
            if (reportFile != null && reportFile.name != previousReport && entry.uris.size == 1) {
                val validation = runCatching { JSONObject(reportFile.readText()) }.getOrNull()
                if (validation != null && validation.optString("status") == "checked") {
                    val verification = validation.getJSONObject("verification")
                    require(verification.getLong("sampleSpanUs") >= 60_000_000L) {
                        "P016 sample span is shorter than sixty seconds"
                    }
                    require(verification.getBoolean("audioRequested") &&
                        verification.getInt("audioTrackCount") == 1 &&
                        verification.getBoolean("firstAudioPcmDecoded")) {
                        "P016 mono audio was not retained and decoded on device"
                    }
                    val attemptFile = File(
                        context.filesDir,
                        "exports/recording-evidence/${validation.getString("attemptReport")}"
                    )
                    val attempt = runCatching { JSONObject(attemptFile.readText()) }.getOrNull()
                    if (attempt?.optBoolean("closed") == true) {
                        require(attempt.getString("sourceRevision") == BuildConfig.SOURCE_REVISION)
                        require(attempt.getJSONObject("classification").getBoolean("recordingSucceeded"))
                        require(!attempt.getJSONObject("classification").getBoolean("fullDecodeVerified"))
                        require(!attempt.getJSONObject("classification").getBoolean("physicalCameraCertified"))
                        return CompletedCapture(entry, reportFile, validation, attemptFile, attempt)
                    }
                }
            }
            if (reportFile?.name != previousReport && entry.message.contains("rejected", ignoreCase = true)) {
                error("P016 recording was rejected: ${entry.message}")
            }
            Thread.sleep(200)
        }
        error("No new checked P016 recording was published: ${CaptureHistory.latest(context).message}")
    }

    fun createBundleDirectory(context: Context, runId: String): File {
        val parent = requireNotNull(context.getExternalFilesDir("p016")) {
            "App-specific external evidence directory is unavailable"
        }
        require(parent.isDirectory || parent.mkdirs()) { "Cannot create P016 evidence parent" }
        val directory = File(parent, runId)
        require(!directory.exists()) { "P016 run id already exists; refusing overwrite" }
        require(directory.mkdir()) { "Cannot create P016 bundle directory" }
        return directory
    }

    fun copyMedia(context: Context, entry: CaptureHistory.Entry, target: File): Identity {
        require(entry.uris.size == 1) { "Expected exactly one published media URI" }
        require(target.createNewFile()) { "Refusing to overwrite existing P016 media" }
        requireNotNull(context.contentResolver.openInputStream(entry.uris.single())).use { input ->
            FileOutputStream(target).use { output -> input.copyTo(output, 1024 * 1024) }
        }
        return identity(target)
    }

    fun identity(file: File): Identity {
        require(file.isFile && file.length() > 0) { "Missing or empty evidence file ${file.name}" }
        val digest = MessageDigest.getInstance("SHA-256")
        var count = 0L
        file.inputStream().use { input ->
            val buffer = ByteArray(1024 * 1024)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                if (read == 0) continue
                digest.update(buffer, 0, read)
                count += read
            }
        }
        return Identity(digest.digest().joinToString("") { "%02x".format(it) }, count)
    }

    fun fileRecord(name: String, identity: Identity): JSONObject = JSONObject()
        .put("name", name)
        .put("identity", identity.json())

    fun atomicWrite(target: File, payload: String) {
        val temporary = File(target.parentFile, ".${target.name}.tmp")
        require(!temporary.exists() && temporary.createNewFile()) { "Cannot create temporary evidence file" }
        temporary.writeText(payload)
        require(temporary.renameTo(target)) { "Cannot atomically publish ${target.name}" }
    }

    fun deviceSnapshot(context: Context): JSONObject {
        val internal = StatFs(context.filesDir.absolutePath).availableBytes
        val externalDirectory = context.getExternalFilesDir(null)
        val external = externalDirectory?.let { StatFs(it.absolutePath).availableBytes }
        val batteryIntent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val level = batteryIntent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryIntent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val percentage = if (level >= 0 && scale > 0) level * 100.0 / scale else null
        val power = context.getSystemService(PowerManager::class.java)
        val thermal = if (Build.VERSION.SDK_INT >= 29) power.currentThermalStatus else null
        return JSONObject()
            .put("capturedAtUtc", Instant.now().toString())
            .put("manufacturer", Build.MANUFACTURER)
            .put("brand", Build.BRAND)
            .put("model", Build.MODEL)
            .put("device", Build.DEVICE)
            .put("product", Build.PRODUCT)
            .put("fingerprint", Build.FINGERPRINT)
            .put("hardware", Build.HARDWARE)
            .put("board", Build.BOARD)
            .put("bootloader", Build.BOOTLOADER)
            .put("sdkInt", Build.VERSION.SDK_INT)
            .put("androidRelease", Build.VERSION.RELEASE)
            .put("securityPatch", Build.VERSION.SECURITY_PATCH)
            .put("elapsedRealtimeMs", android.os.SystemClock.elapsedRealtime())
            .put("internalAvailableBytes", internal)
            .put("externalAvailableBytes", external ?: JSONObject.NULL)
            .put("thermalStatus", thermal ?: JSONObject.NULL)
            .put("battery", JSONObject()
                .put("percent", percentage ?: JSONObject.NULL)
                .put("temperatureC", batteryIntent?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1)
                    ?.takeIf { it >= 0 }?.div(10.0) ?: JSONObject.NULL)
                .put("voltageMv", batteryIntent?.getIntExtra(BatteryManager.EXTRA_VOLTAGE, -1)
                    ?.takeIf { it >= 0 } ?: JSONObject.NULL)
                .put("status", batteryIntent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
                    ?.takeIf { it >= 0 } ?: JSONObject.NULL)
                .put("health", batteryIntent?.getIntExtra(BatteryManager.EXTRA_HEALTH, -1)
                    ?.takeIf { it >= 0 } ?: JSONObject.NULL)
                .put("plugged", batteryIntent?.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1)
                    ?.takeIf { it >= 0 } ?: JSONObject.NULL)
                .put("present", batteryIntent?.getBooleanExtra(BatteryManager.EXTRA_PRESENT, false)
                    ?: JSONObject.NULL))
    }

    fun snapshotPreferences(preferences: android.content.SharedPreferences): Map<String, Any?> =
        preferences.all.mapValues { (_, value) ->
            @Suppress("UNCHECKED_CAST")
            if (value is Set<*>) (value as Set<String>).toSet() else value
        }

    fun restorePreferences(preferences: android.content.SharedPreferences, values: Map<String, Any?>) {
        val editor = preferences.edit().clear()
        for ((key, value) in values) {
            when (value) {
                is String -> editor.putString(key, value)
                is Boolean -> editor.putBoolean(key, value)
                is Int -> editor.putInt(key, value)
                is Long -> editor.putLong(key, value)
                is Float -> editor.putFloat(key, value)
                is Set<*> -> {
                    @Suppress("UNCHECKED_CAST")
                    editor.putStringSet(key, value as Set<String>)
                }
                null -> editor.remove(key)
                else -> error("Unsupported saved preference type for $key")
            }
        }
        require(editor.commit()) { "Could not restore camera settings after P016" }
    }
}
