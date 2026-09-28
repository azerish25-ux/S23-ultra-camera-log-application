package com.s23log.probe.camera

import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CaptureFailure
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.DngCreator
import android.hardware.camera2.TotalCaptureResult
import android.media.Image
import android.media.ImageReader
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.view.Surface
import com.s23log.probe.core.TimestampMatcher
import com.s23log.probe.diagnostics.atomicWrite
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.storage.CaptureHistory
import com.s23log.probe.storage.PendingMedia
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID
import java.util.concurrent.ExecutorService

/** Bounded single-shot or sequential-five DNG probe, not sustained RAW video. */
class RawCapture(
    private val context: Context,
    private val target: CameraTarget,
    private val controls: CameraControls,
    private val orientation: Int,
    private val count: Int,
    private val handler: Handler,
    private val io: ExecutorService,
    private val progress: (String) -> Unit,
    private val completed: (Outcome) -> Unit
) {
    data class Outcome(val uris: List<Uri>, val report: File?, val message: String)
    private val size = requireNotNull(target.rawSize) { "No advertised RAW_SENSOR output" }
    private val reader = ImageReader.newInstance(size.width, size.height, ImageFormat.RAW_SENSOR, 2)
    val surface: Surface get() = reader.surface
    private val matcher = TimestampMatcher<Image, CaptureResult>(2) { it.close() }
    private val outputs = mutableListOf<Uri>()
    private val frames = JSONArray()
    private var session: CameraCaptureSession? = null
    private var device: CameraDevice? = null
    private var saving = false
    private var done = false
    @Volatile private var cancelled = false
    private var reason: String? = null
    private var shot = 0
    private val began = SystemClock.elapsedRealtime()
    private var firstTimestamp: Long? = null
    private var lastTimestamp: Long? = null
    init {
        require(count == 1 || count == 5)
        reader.setOnImageAvailableListener({ source ->
            if (done || cancelled) return@setOnImageAvailableListener
            try {
                val image = source.acquireNextImage() ?: return@setOnImageAvailableListener
                matcher.image(image.timestamp, image)?.let { save(it.first, it.second) }
            } catch (e: Exception) { cancel("RAW image acquisition failed: ${e.message}") }
        }, handler)
    }
    fun start(camera: CameraDevice, captureSession: CameraCaptureSession) {
        if (cancelled || done) return
        device = camera
        session = captureSession
        next()
    }
    private fun next() {
        if (cancelled || done) return
        shot++
        val thisShot = shot
        progress("RAW $shot/$count: waiting for matched image and sensor metadata…")
        try {
            val request = requireNotNull(device).createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE).apply {
                addTarget(surface)
                controls.apply(this, target, null)
            }.build()
            requireNotNull(session).capture(request, object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(session: CameraCaptureSession, request: CaptureRequest, result: TotalCaptureResult) {
                    if (done || cancelled || thisShot != shot) return
                    try {
                        val metadata: CaptureResult = if (target.physicalId != null && Build.VERSION.SDK_INT >= 28)
                            requireNotNull(result.physicalCameraResults[target.physicalId]) { "No metadata for the selected physical RAW camera" } else result
                        val timestamp = requireNotNull(metadata[CaptureResult.SENSOR_TIMESTAMP]) { "RAW capture has no sensor timestamp" }
                        matcher.result(timestamp, metadata)?.let { save(it.first, it.second) }
                    } catch (e: Exception) { cancel(e.message ?: "RAW metadata error") }
                }
                override fun onCaptureFailed(session: CameraCaptureSession, request: CaptureRequest, failure: CaptureFailure) {
                    if (!done && thisShot == shot) cancel("RAW capture failed: ${failure.reason}")
                }
            }, handler)
            val timeout = maxOf(10_000L, controls.exposureNs / 1_000_000 + 5000)
            handler.postDelayed({ if (!done && !saving && thisShot == shot) cancel("RAW image/metadata pairing timed out") }, timeout)
        } catch (e: Exception) { cancel("RAW request failed: ${e.message}") }
    }
    private fun save(image: Image, metadata: CaptureResult) {
        if (saving || cancelled || done) { image.close(); return }
        saving = true
        val timestamp = image.timestamp
        io.execute {
            var output: PendingMedia? = null
            val result = runCatching {
                check(!cancelled) { "RAW capture cancelled" }
                output = PendingMedia.create(context, video = false)
                val exif = when (orientation) { 90 -> 6; 180 -> 3; 270 -> 8; else -> 1 }
                DngCreator(target.characteristics, metadata).use { dng ->
                    dng.setOrientation(exif)
                    dng.setDescription("S23Log RAW_SENSOR still; no log transform")
                    ParcelFileDescriptor.AutoCloseOutputStream(ParcelFileDescriptor.dup(output!!.descriptor.fileDescriptor)).use { stream -> dng.writeImage(stream, image) }
                }
                output!!.closeDescriptor()
                val signature = ByteArray(4)
                context.contentResolver.openInputStream(output!!.uri).use { input -> check(input != null && input.read(signature) == 4) }
                check(signature.contentEquals(byteArrayOf(73, 73, 42, 0)) || signature.contentEquals(byteArrayOf(77, 77, 0, 42))) { "DNG did not contain a TIFF header" }
                check(!cancelled) { "RAW capture cancelled before publication" }
                output!!.publish()
            }
            runCatching { image.close() }
            if (result.isFailure) output?.abort()
            handler.post {
                saving = false
                result.onSuccess { uri ->
                    outputs += uri
                    if (firstTimestamp == null) firstTimestamp = timestamp
                    lastTimestamp = timestamp
                    frames.put(JSONObject().put("uri", uri.toString()).put("sensorTimestampNs", timestamp)
                        .put("iso", metadata[CaptureResult.SENSOR_SENSITIVITY] ?: JSONObject.NULL)
                        .put("exposureNs", metadata[CaptureResult.SENSOR_EXPOSURE_TIME] ?: JSONObject.NULL)
                        .put("width", size.width).put("height", size.height))
                }.onFailure { reason = it.message ?: "DNG save failed"; cancelled = true }
                if (cancelled || outputs.size >= count) finish() else next()
            }
        }
    }
    fun cancel(message: String) {
        if (done) return
        cancelled = true
        reason = message
        matcher.clear()
        // Keep the reader alive while DngCreator owns an acquired image.
        if (!saving) finish()
    }
    private fun finish() {
        if (done) return
        done = true
        matcher.clear()
        reader.close()
        val elapsed = SystemClock.elapsedRealtime() - began
        val report = JSONObject().put("schemaVersion", 1).put("kind", "sequential-raw-stills")
            .put("logicalCamera", target.logicalId).put("physicalCamera", target.physicalId ?: JSONObject.NULL)
            .put("requestedControls", jsonValue(controls.describe())).put("requestedCount", count).put("savedCount", outputs.size)
            .put("elapsedMsIncludingDngWrite", elapsed).put("frames", frames)
            .put("sensorSpanNs", if (firstTimestamp != null && lastTimestamp != null) lastTimestamp!! - firstTimestamp!! else JSONObject.NULL)
            .put("error", reason ?: JSONObject.NULL).put("sustainedRawVideoVerified", false)
        io.execute {
            var file: File? = null
            var reportError: String? = null
            try {
                val directory = File(context.filesDir, "exports/validation")
                check(directory.isDirectory || directory.mkdirs())
                file = File(directory, "raw-${UUID.randomUUID()}.json")
                atomicWrite(file, report.toString(2))
            } catch (e: Exception) { reportError = e.message; file = null }
            val message = "Saved ${outputs.size}/$count RAW DNGs in ${elapsed} ms (sequential stills, not RAW video)." +
                (reason?.let { " $it" } ?: "") + (reportError?.let { " Validation report save failed: $it" } ?: "")
            runCatching { CaptureHistory.save(context, outputs.toList(), file, message) }
            handler.post { completed(Outcome(outputs.toList(), file, message)) }
        }
    }
}
