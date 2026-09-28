package com.s23log.probe.camera

import android.content.Context
import android.media.MediaCodec
import android.media.MediaFormat
import android.media.MediaMuxer
import android.net.Uri
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.view.Surface
import com.s23log.probe.core.FrameStatistics
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.diagnostics.atomicWrite
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.storage.PendingMedia
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

/** Owns codec, muxer and pending output. All drain/finalization work stays off the camera/UI threads. */
class SurfaceRecorder private constructor(
    private val context: Context,
    val mode: RecordingMode,
    private val orientation: Int,
    private val request: Map<String, Any?>,
    private val completed: (Outcome) -> Unit
) {
    data class Outcome(val uri: Uri?, val report: File?, val message: String)
    private val thread = HandlerThread("S23Log-encoder").apply { start() }
    private val handler = Handler(thread.looper)
    private lateinit var output: PendingMedia
    private lateinit var codec: MediaCodec
    private var muxer: MediaMuxer? = null
    lateinit var surface: Surface
        private set
    private var track = -1
    private var muxerStarted = false
    @Volatile private var finished = false
    private var stopping = false
    private var beganAt = 0L
    private var lastFrameAt = 0L
    private val frameStats = FrameStatistics(mode.fps)
    @Volatile private var applied: Map<String, Any?> = emptyMap()
    @Volatile private var sessionConfigured = false
    private val watchdog = object : Runnable {
        override fun run() {
            if (finished || stopping) return
            if (SystemClock.elapsedRealtime() - maxOf(beganAt, lastFrameAt) > 10_000L) complete(IllegalStateException("No encoder frames for 10 seconds"))
            else handler.postDelayed(this, 1000)
        }
    }

    private fun prepare() {
        try {
            output = PendingMedia.create(context, video = true)
            codec = MediaCodec.createByCodecName(mode.encoder)
            codec.setCallback(object : MediaCodec.Callback() {
                override fun onInputBufferAvailable(codec: MediaCodec, index: Int) = Unit // Surface input only.
                override fun onOutputFormatChanged(codec: MediaCodec, format: MediaFormat) {
                    if (finished) return
                    try {
                        check(!muxerStarted) { "Unexpected second encoder output format" }
                        track = requireNotNull(muxer).addTrack(format)
                        requireNotNull(muxer).start()
                        muxerStarted = true
                    } catch (e: Exception) { complete(e) }
                }
                override fun onOutputBufferAvailable(codec: MediaCodec, index: Int, info: MediaCodec.BufferInfo) {
                    if (finished) return
                    var failure: Exception? = null
                    try {
                        if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                            check(muxerStarted && track >= 0) { "Encoder produced samples before a usable track format" }
                            val buffer = requireNotNull(codec.getOutputBuffer(index))
                            buffer.position(info.offset)
                            buffer.limit(info.offset + info.size)
                            requireNotNull(muxer).writeSampleData(track, buffer, info)
                            frameStats.add(info.presentationTimeUs)
                            lastFrameAt = SystemClock.elapsedRealtime()
                        }
                    } catch (e: Exception) { failure = e }
                    finally { runCatching { codec.releaseOutputBuffer(index, false) }.exceptionOrNull()?.let { if (failure == null) failure = IllegalStateException("Cannot release encoder buffer", it) } }
                    if (failure != null) complete(failure)
                    else if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) complete(null)
                }
                override fun onError(codec: MediaCodec, error: MediaCodec.CodecException) { complete(error) }
            }, handler)
            codec.configure(CameraCatalog.videoFormat(mode), null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            surface = codec.createInputSurface()
            muxer = MediaMuxer(output.descriptor.fileDescriptor, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4).apply { setOrientationHint(orientation) }
            codec.start()
        } catch (e: Exception) {
            finished = true
            handler.removeCallbacksAndMessages(null)
            if (::codec.isInitialized) runCatching { codec.release() }
            if (::surface.isInitialized) runCatching { surface.release() }
            runCatching { muxer?.release() }
            if (::output.isInitialized) output.abort()
            thread.quitSafely()
            throw e
        }
    }

    fun sessionStarted() {
        sessionConfigured = true
        handler.post { beganAt = SystemClock.elapsedRealtime(); handler.post(watchdog) }
    }
    fun noteApplied(values: Map<String, Any?>) { applied = values.toMap() }
    fun finish() {
        handler.post {
            if (finished || stopping) return@post
            stopping = true
            handler.removeCallbacks(watchdog)
            try {
                codec.signalEndOfInputStream()
                handler.postDelayed({ if (!finished) complete(IllegalStateException("Encoder end-of-stream timed out")) }, 8000)
            } catch (e: Exception) { complete(e) }
        }
    }
    fun cancel(reason: String) { handler.post { complete(IllegalStateException(reason)) } }

    private fun complete(initialError: Exception?) {
        if (finished) return
        finished = true
        handler.removeCallbacksAndMessages(null)
        var failure = initialError
        fun attempt(block: () -> Unit) { try { block() } catch (e: Exception) { if (failure == null) failure = e } }
        attempt { codec.stop() }
        attempt { codec.release() }
        if (muxerStarted) attempt { muxer?.stop() }
        attempt { muxer?.release() }
        attempt { surface.release() }
        attempt { output.closeDescriptor() }
        var uri: Uri? = null
        var reportFile: File? = null
        val report = JSONObject().put("schemaVersion", 1).put("kind", "recording-validation")
            .put("requested", jsonValue(request)).put("mode", mode.label).put("encoder", mode.encoder)
            .put("orientation", orientation).put("latestApplied", jsonValue(applied))
            .put("videoOnly", true).put("customLog", false)
        val stats = frameStats.summary()
        report.put("encodedSamples", stats.frames).put("encodedFrameGaps", stats.largeGaps)
        val stages = JSONArray().put("advertised")
        if (sessionConfigured) stages.put("session_configured")
        if (stats.frames > 0) stages.put("encoded_frames_received")
        if (failure == null) {
            try {
                require(stats.frames >= 2) { "Recording was stopped before two video frames arrived" }
                report.put("verification", RecordingVerifier.verify(context, output.uri, mode))
                stages.put("container_and_output_checked")
            } catch (e: Exception) { failure = e }
        }
        report.put("stages", stages).put("status", if (failure == null) "checked" else "rejected")
        report.put("error", failure?.let { "${it.javaClass.simpleName}: ${it.message}" } ?: JSONObject.NULL)
        try {
            val directory = File(context.filesDir, "exports/validation")
            check(directory.isDirectory || directory.mkdirs())
            reportFile = File(directory, "recording-${UUID.randomUUID()}.json")
            atomicWrite(reportFile, report.toString(2))
        } catch (e: Exception) { if (failure == null) failure = e; reportFile = null }
        if (failure == null) {
            try { uri = output.publish() } catch (e: Exception) { failure = e }
        }
        if (failure != null) {
            output.abort()
            report.put("status", "rejected").put("error", failure?.message ?: "Output publication failed")
            reportFile?.let { runCatching { atomicWrite(it, report.toString(2)) } }
        }
        val message = if (uri != null) "Saved ${mode.label}; ${stats.frames} frames. File checked; sustained device performance is not certified."
            else "Recording rejected and pending video removed: ${failure?.message ?: "unknown error"}"
        runCatching { CaptureHistory.save(context, listOfNotNull(uri), reportFile, message) }
        try { completed(Outcome(uri, reportFile, message)) } finally { thread.quitSafely() }
    }

    companion object {
        fun prepare(context: Context, mode: RecordingMode, orientation: Int, request: Map<String, Any?>, completed: (Outcome) -> Unit): SurfaceRecorder =
            SurfaceRecorder(context.applicationContext, mode, orientation, request, completed).apply { prepare() }
    }
}
