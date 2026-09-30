package com.s23log.probe.camera

import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CaptureFailure
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.TotalCaptureResult
import android.media.Image
import android.media.ImageReader
import android.os.Build
import android.os.Handler
import android.os.PowerManager
import android.os.SystemClock
import android.view.Surface
import androidx.core.content.FileProvider
import com.s23log.probe.core.RawFrameMatcher
import com.s23log.probe.core.RawSequenceFormat
import com.s23log.probe.core.RawSequencePlan
import com.s23log.probe.diagnostics.ModeEvidence
import com.s23log.probe.diagnostics.atomicWrite
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Repeating RAW capture. Camera callbacks never wait for disk; bounded copied buffers own each frame. */
class RawSequenceCapture(
    private val context: Context, private val target: CameraTarget, private val controls: CameraControls,
    private val plan: RawSequencePlan, private val orientation: Int, private val handler: Handler,
    private val io: ExecutorService, private val progress: (String) -> Unit,
    private val completed: (RawCapture.Outcome) -> Unit
) : RawCaptureJob {
    private data class Packet(val metadata: ByteArray, val pixels: ByteArray, val timestamp: Long)
    private val c = target.characteristics
    private val id = UUID.randomUUID().toString()
    private val directory = File(context.filesDir, "exports/raw-sequences")
    private val file = File(directory, "raw-$id.s23raw")
    private val stopped = AtomicBoolean()
    private val free = ArrayBlockingQueue<ByteArray>(plan.poolSize)
    private val writes = ArrayBlockingQueue<Packet>(plan.poolSize)
    private val effective = controls.effective(target, plan.fps)
    private var reader: ImageReader? = null
    override val surface: Surface get() = requireNotNull(reader).surface
    private var session: CameraCaptureSession? = null
    private var workerStarted = false
    private var finalized = false
    private var closing = false
    private var stopKind = "completed"
    private var reason: String? = null
    private var imagesReceived = 0L
    private var metadataReceived = 0L
    private var matchedFrames = 0L
    private var unmatchedImages = 0L
    private var unmatchedMetadata = 0L
    private var poolOverflows = 0L
    private var firstTimestamp: Long? = null
    private var lastTimestamp: Long? = null
    private var maximumGapNs = 0L
    private var largeGaps = 0L
    private var beganAt = 0L
    private var lastImageAt = 0L
    private var firstImageAt = 0L
    private var bytesWritten = 0L // Read only after the writer posts completion.
    private var framesWritten = 0L
    private var lastWrittenTimestamp = 0L
    private var writerError: String? = null
    private var maximumCopyNs = 0L
    private val matcher = RawFrameMatcher<ByteArray, JSONObject>(plan.poolSize + 2,
        discard = { pixels, why ->
            unmatchedImages++
            recycle(pixels)
            if (!closing && !stopped.get()) cancel("RAW metadata pairing failed: $why")
        }, missingImage = { why ->
            unmatchedMetadata++
            if (!closing && !stopped.get()) cancel("RAW image pairing failed: $why")
        }, matched = ::accept)

    init {
        require(controls.manualExposure && target.manualSensor) { "Apply and confirm manual exposure before RAW capture" }
        require(ByteOrder.nativeOrder() == ByteOrder.LITTLE_ENDIAN) { "RAW_SENSOR byte order is unqualified on this device" }
        val map = requireNotNull(c[C.SCALER_STREAM_CONFIGURATION_MAP])
        val size = android.util.Size(plan.width, plan.height)
        require(size in map.getOutputSizes(ImageFormat.RAW_SENSOR).orEmpty()) { "Selected RAW size is not advertised" }
        val minFrame = map.getOutputMinFrameDuration(ImageFormat.RAW_SENSOR, size)
        require(minFrame == 0L || minFrame <= 1_000_000_000L / plan.fps + 1) { "RAW minimum frame duration exceeds the requested rate" }
        require(c[C.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT] in 0..3) { "Only declared Bayer RAW_SENSOR mosaics are supported" }
        plan.rejection(Runtime.getRuntime().maxMemory(), context.filesDir.usableSpace)?.let { error(it) }
        repeat(plan.poolSize) { free.add(ByteArray(if (plan.storeFrames) plan.frameBytes else 0)) }
        reader = ImageReader.newInstance(plan.width, plan.height, ImageFormat.RAW_SENSOR, 3).also { source ->
            source.setOnImageAvailableListener({ onImages(it) }, handler)
        }
    }
    override fun start(camera: CameraDevice, captureSession: CameraCaptureSession) {
        if (stopped.get() || workerStarted) return
        session = captureSession
        workerStarted = true
        beganAt = SystemClock.elapsedRealtime(); lastImageAt = beganAt
        progress("Starting continuous RAW ${plan.width}×${plan.height} / ${plan.fps}; ${if (plan.storeFrames) "saving sensor frames" else "acquisition-only benchmark"}. No audio.")
        io.execute {
            try {
                if (plan.storeFrames) {
                    check(directory.isDirectory || directory.mkdirs()) { "RAW directory unavailable" }
                    FileOutputStream(file).use { raw ->
                        BufferedOutputStream(raw, 256 * 1024).use { output ->
                            RawSequenceFormat.header(output, header().toString().toByteArray(Charsets.UTF_8))
                            output.flush(); raw.fd.sync()
                            handler.post { begin(camera, captureSession) }
                            drain { packet -> RawSequenceFormat.frame(output, packet.metadata, packet.pixels) }
                            output.flush(); raw.fd.sync()
                        }
                    }
                } else {
                    handler.post { begin(camera, captureSession) }
                    drain { _ -> }
                }
            } catch (e: Exception) {
                writerError = e.message ?: e.javaClass.simpleName
                stopped.set(true)
            } finally {
                while (true) recycle(writes.poll()?.pixels ?: break)
                handler.post { finishOnCameraThread() }
            }
        }
    }
    private fun drain(write: (Packet) -> Unit) {
        while (!stopped.get() || writes.isNotEmpty()) {
            val packet = writes.poll(100, TimeUnit.MILLISECONDS) ?: continue
            try {
                check(packet.timestamp > lastWrittenTimestamp) { "RAW writer received out-of-order frames" }
                write(packet)
                if (plan.storeFrames) { framesWritten++; bytesWritten += packet.pixels.size }
                lastWrittenTimestamp = packet.timestamp
            } finally { recycle(packet.pixels) }
        }
    }
    private fun begin(camera: CameraDevice, active: CameraCaptureSession) {
        if (stopped.get()) return
        try {
            val request = target.request(camera, CameraDevice.TEMPLATE_RECORD).apply {
                addTarget(surface)
                effective.apply(this, target, plan.fps)
            }.build()
            active.setRepeatingRequest(request, object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(s: CameraCaptureSession, r: CaptureRequest, result: TotalCaptureResult) {
                    if (stopped.get()) return
                    try {
                        val m: CaptureResult = if (target.physicalId != null && Build.VERSION.SDK_INT >= 28)
                            requireNotNull(result.physicalCameraResults[target.physicalId]) { "Physical RAW metadata missing" } else result
                        val timestamp = requireNotNull(m[CaptureResult.SENSOR_TIMESTAMP])
                        val exposure = requireNotNull(m[CaptureResult.SENSOR_EXPOSURE_TIME])
                        val iso = requireNotNull(m[CaptureResult.SENSOR_SENSITIVITY])
                        require(kotlin.math.abs(exposure - effective.exposureNs) <= maxOf(100_000L, effective.exposureNs / 20) &&
                            kotlin.math.abs(iso - effective.iso) <= maxOf(1, effective.iso / 20) &&
                            m[CaptureResult.CONTROL_AE_MODE] == CaptureRequest.CONTROL_AE_MODE_OFF) {
                            "RAW sensor results do not match the requested manual exposure"
                        }
                        val black = m[CaptureResult.SENSOR_DYNAMIC_BLACK_LEVEL]?.map { it.toDouble() } ?: blackLevels()
                        val white = m[CaptureResult.SENSOR_DYNAMIC_WHITE_LEVEL] ?: c[C.SENSOR_INFO_WHITE_LEVEL]
                        require(black != null && white != null) { "RAW black/white levels missing" }
                        metadataReceived++
                        val gains = m[CaptureResult.COLOR_CORRECTION_GAINS]
                        val meta = JSONObject().put("sensorTimestampNs", timestamp).put("frameNumber", result.frameNumber)
                            .put("iso", iso).put("exposureNs", exposure)
                            .put("frameDurationNs", m[CaptureResult.SENSOR_FRAME_DURATION] ?: JSONObject.NULL)
                            .put("blackLevels", jsonValue(black)).put("whiteLevel", white)
                            .put("neutralColorPoint", jsonValue(m[CaptureResult.SENSOR_NEUTRAL_COLOR_POINT]?.map { it.toDouble() }))
                            .put("gains", jsonValue(gains?.let { listOf(it.red, it.greenEven, it.greenOdd, it.blue) }))
                            .put("awbState", m[CaptureResult.CONTROL_AWB_STATE] ?: JSONObject.NULL)
                        matcher.result(timestamp, meta)
                    } catch (e: Exception) { cancel("RAW result rejected: ${e.message}") }
                }
                override fun onCaptureFailed(s: CameraCaptureSession, request: CaptureRequest, failure: CaptureFailure) {
                    if (!stopped.get()) cancel("RAW request failed: ${failure.reason}")
                }
            }, handler)
            handler.postDelayed(watchdog, 500)
        } catch (e: Exception) { cancel("Continuous RAW request rejected: ${e.message}") }
    }
    private fun onImages(source: ImageReader) {
        if (stopped.get()) return
        try {
            while (!stopped.get()) {
                val image = source.acquireNextImage() ?: break
                val timestamp = image.timestamp
                val pixels = free.poll()
                if (pixels == null) {
                    image.close(); poolOverflows++
                    cancel("RAW buffer pool exhausted; requested throughput is not sustained"); return
                }
                try {
                    image.use {
                        imagesReceived++; lastImageAt = SystemClock.elapsedRealtime()
                        if (firstImageAt == 0L) firstImageAt = lastImageAt
                        require(timestamp > 0 && image.width == plan.width && image.height == plan.height && image.format == ImageFormat.RAW_SENSOR)
                        if (plan.storeFrames) {
                            val started = System.nanoTime(); copy(image, pixels)
                            maximumCopyNs = maxOf(maximumCopyNs, System.nanoTime() - started)
                        }
                    }
                } catch (e: Exception) { recycle(pixels); throw e }
                // Ownership moves only after Image.close(). The match callback may recycle or queue it.
                matcher.image(timestamp, pixels)
            }
        } catch (e: Exception) { cancel("RAW acquisition failed: ${e.message}") }
    }
    private fun copy(image: Image, pixels: ByteArray) {
        val plane = image.planes.single()
        require(plane.pixelStride == 2 && plane.rowStride >= plan.width * 2) { "Unsupported RAW_SENSOR plane layout" }
        val buffer = plane.buffer.duplicate(); val base = buffer.position()
        require(base.toLong() + (plan.height - 1L) * plane.rowStride + plan.width * 2 <= buffer.limit()) { "Truncated RAW plane" }
        for (row in 0 until plan.height) {
            buffer.position(base + row * plane.rowStride)
            buffer.get(pixels, row * plan.width * 2, plan.width * 2)
        }
    }
    private fun accept(timestamp: Long, pixels: ByteArray, metadata: JSONObject) {
        if (stopped.get()) { recycle(pixels); return }
        val previous = lastTimestamp
        if (previous != null && timestamp <= previous) { recycle(pixels); cancel("RAW timestamps repeated or regressed"); return }
        if (previous != null) {
            val gap = timestamp - previous; maximumGapNs = maxOf(maximumGapNs, gap)
            if (gap > 1_500_000_000L / plan.fps) largeGaps++
        }
        if (firstTimestamp == null) firstTimestamp = timestamp
        lastTimestamp = timestamp; matchedFrames++
        if (plan.storeFrames) {
            if (!writes.offer(Packet(metadata.toString().toByteArray(Charsets.UTF_8), pixels, timestamp))) {
                recycle(pixels); poolOverflows++; cancel("RAW writer queue overflow; sequence retained without pretending cadence passed")
            }
        } else recycle(pixels)
        if (matchedFrames % plan.fps == 0L) progress("RAW: $matchedFrames matched frames; $largeGaps cadence gaps. ${if (plan.storeFrames) "Saving source" else "No source pixels saved"}.")
        if (timestamp - requireNotNull(firstTimestamp) >= plan.seconds * 1_000_000_000L) requestStop("completed", null)
    }
    private val watchdog = object : Runnable {
        override fun run() {
            if (stopped.get()) return
            val now = SystemClock.elapsedRealtime()
            when {
                imagesReceived == 0L && now - beganAt > 10_000 -> cancel("No RAW frames arrived within ten seconds")
                imagesReceived > 0L && now - lastImageAt > 3000 -> cancel("RAW stream stalled for three seconds")
                firstImageAt > 0L && now - firstImageAt >= plan.seconds * 1000L + 1000L -> requestStop("stopped", "Wall-clock limit reached; inspect cadence")
                context.filesDir.usableSpace < 64L * 1024 * 1024 -> cancel("RAW storage reserve reached")
                Build.VERSION.SDK_INT >= 29 && context.getSystemService(PowerManager::class.java).currentThermalStatus >= PowerManager.THERMAL_STATUS_SEVERE -> cancel("Severe thermal pressure; RAW capture stopped")
                else -> handler.postDelayed(this, 500)
            }
        }
    }
    override fun stop() = requestStop("stopped", "Stopped by user")
    override fun cancel(message: String) = requestStop("failed", message)
    private fun requestStop(kind: String, message: String?) {
        if (stopped.getAndSet(true)) return
        stopKind = kind; reason = message
        closeInput()
        progress("Stopping RAW acquisition; draining retained frames…")
        if (!workerStarted) finishOnCameraThread()
    }
    private fun closeInput() {
        if (closing) return
        closing = true
        handler.removeCallbacks(watchdog)
        runCatching { session?.stopRepeating() }
        fun cleanup(block: () -> Unit) {
            runCatching(block).onFailure { if (reason == null) { reason = "RAW cleanup: ${it.message}"; stopKind = "failed" } }
        }
        cleanup { matcher.clear() }
        cleanup { reader?.setOnImageAvailableListener(null, null) }
        cleanup { reader?.close() }; reader = null
    }
    private fun recycle(pixels: ByteArray) { check(free.offer(pixels)) { "RAW buffer was recycled twice" } }
    private fun blackLevels(): List<Double>? = c[C.SENSOR_BLACK_LEVEL_PATTERN]?.let { pattern ->
        listOf(pattern.getOffsetForIndex(0, 0).toDouble(), pattern.getOffsetForIndex(1, 0).toDouble(),
            pattern.getOffsetForIndex(0, 1).toDouble(), pattern.getOffsetForIndex(1, 1).toDouble())
    }
    private fun header(): JSONObject = JSONObject().put("schemaVersion", 1).put("kind", "continuous-raw")
        .put("device", jsonValue(ModeEvidence.device())).put("logicalCamera", target.logicalId)
        .put("physicalCamera", target.physicalId ?: JSONObject.NULL)
        .put("width", plan.width).put("height", plan.height).put("fpsRequested", plan.fps)
        .put("secondsRequested", plan.seconds).put("orientationDegrees", orientation)
        .put("sampleEncoding", "uint16le").put("rowBytes", plan.width * 2)
        .put("source", "RAW_SENSOR").put("sensorBitDepth", JSONObject.NULL)
        .put("cfa", c[C.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT] ?: JSONObject.NULL)
        .put("blackLevels", jsonValue(blackLevels())).put("whiteLevel", c[C.SENSOR_INFO_WHITE_LEVEL] ?: JSONObject.NULL)
        .put("activeArray", c[C.SENSOR_INFO_ACTIVE_ARRAY_SIZE]?.let { jsonValue(listOf(it.left, it.top, it.right, it.bottom)) } ?: JSONObject.NULL)
        .put("requestedControls", jsonValue(controls.describe())).put("effectiveControls", jsonValue(effective.describe()))
        .put("colourCalibration", "not_supplied").put("audio", "none").put("samsungLog", false)
        .put("physicalCameraCertified", false).put("arriraw", false)
    private fun finishOnCameraThread() {
        if (finalized) return
        finalized = true; stopped.set(true); closeInput()
        // The worker has finished, and this owner can no longer enqueue; reclaim a racing final offer.
        while (true) recycle(writes.poll()?.pixels ?: break)
        if (writerError != null) { stopKind = "failed"; reason = "RAW writer failed: $writerError" }
        val span = (lastTimestamp ?: 0L) - (firstTimestamp ?: 0L)
        val rate = if (matchedFrames > 1 && span > 0) (matchedFrames - 1) * 1e9 / span else null
        val cadence = rate != null && span >= 2_000_000_000L && kotlin.math.abs(rate / plan.fps - 1) <= .03 && largeGaps == 0L && poolOverflows == 0L
        val report = header().put("kind", if (plan.storeFrames) "raw-sequence-report" else "raw-acquisition-benchmark")
            .put("status", stopKind).put("reason", reason ?: JSONObject.NULL).put("imagesReceived", imagesReceived)
            .put("metadataReceived", metadataReceived).put("matchedFrames", matchedFrames).put("framesWritten", framesWritten)
            .put("unmatchedImages", unmatchedImages).put("unmatchedMetadata", unmatchedMetadata).put("poolOverflows", poolOverflows)
            .put("firstSensorTimestampNs", firstTimestamp ?: JSONObject.NULL).put("lastSensorTimestampNs", lastTimestamp ?: JSONObject.NULL)
            .put("measuredFps", rate ?: JSONObject.NULL).put("largeGaps", largeGaps).put("maximumGapNs", maximumGapNs)
            .put("cadenceWithinTolerance", cadence).put("payloadBytesWritten", bytesWritten).put("poolBytes", plan.poolBytes)
            .put("maximumCopyNs", maximumCopyNs).put("elapsedMs", if (beganAt > 0) SystemClock.elapsedRealtime() - beganAt else 0)
            .put("imageReaderMaxImages", 3).put("copyPoolSize", plan.poolSize).put("sustainedRawVideoCertified", false)
            .put("logC3EncodedOnPhone", false).put("sourceFile", if (file.isFile) file.name else JSONObject.NULL)
        io.execute {
            val publication = runCatching {
                if (file.isFile && file.length() > 0) listOf(FileProvider.getUriForFile(context, "${context.packageName}.files", file)) else emptyList()
            }
            val uris = publication.getOrDefault(emptyList())
            publication.exceptionOrNull()?.let { report.put("shareError", it.message ?: it.javaClass.simpleName) }
            val validation = File(context.filesDir, "exports/validation/raw-$id.json")
            val reportResult = runCatching { check(validation.parentFile!!.isDirectory || validation.parentFile!!.mkdirs()); atomicWrite(validation, report.toString(2)); validation }
            val message = "RAW $stopKind: $matchedFrames matched, $framesWritten saved frames. " +
                (reason?.let { "$it. " } ?: "") + "${if (plan.storeFrames) "Source retained for offline development" else "Acquisition benchmark; no pixels saved"}. No audio or physical certification." +
                (reportResult.exceptionOrNull()?.let { " Report could not be saved: ${it.message}" } ?: "") +
                (publication.exceptionOrNull()?.let { " Share preparation failed; source remains in Retained RAW sequences: ${it.message}" } ?: "")
            runCatching { CaptureHistory.save(context, uris, reportResult.getOrNull(), message) }
            handler.post { completed(RawCapture.Outcome(uris, reportResult.getOrNull(), message)) }
        }
    }
}
