package com.s23log.probe.camera

import android.content.Context
import android.media.MediaCodec
import android.media.MediaFormat
import android.media.MediaMuxer
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.view.Surface
import android.util.Size
import com.s23log.probe.gpu.GpuVideoProcessor
import com.s23log.probe.core.ProcessingPath
import com.s23log.probe.core.MonitorTransform
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.AvMuxCoordinator
import com.s23log.probe.core.AvMuxCoordinator.Track
import com.s23log.probe.core.AvStartGate
import com.s23log.probe.core.VideoFinalizer
import com.s23log.probe.core.VideoDisposition
import com.s23log.probe.core.FrameStatistics
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.diagnostics.ModeEvidence
import com.s23log.probe.diagnostics.atomicWrite
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.storage.PendingMedia
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.util.UUID

/** Single serial owner for both encoders, their common timeline, muxer and staged footage. */
class SurfaceRecorder private constructor(
    private val context: Context,
    val mode: RecordingMode,
    private val orientation: Int,
    private val request: Map<String, Any?>,
    val audioMode: AudioMode,
    private val onFirstSample: () -> Unit,
    private val onAudioMeter: (AudioCapture.Meter) -> Unit,
    private val onAudioFault: (String) -> Unit,
    private val completed: (Outcome) -> Unit
) {
    data class Outcome(val uri: Uri?, val report: File?, val message: String, val audioError: String? = null)
    private val thread = HandlerThread("S23Log-encoder").apply { start() }
    private val handler = Handler(thread.looper)
    private lateinit var output: PendingMedia
    private lateinit var codec: MediaCodec
    @Volatile private var audio: AudioCapture? = null
    private var muxer: MediaMuxer? = null
    @Volatile private var processor: GpuVideoProcessor? = null
    @Volatile private var processingInput: Surface? = null
    private var processingFailure: String? = null
    private var processingCloseRequested = false
    private var processingClosed = false
    private val processingCloseWaiters = mutableListOf<(String?) -> Unit>()
    private var processingSnapshot: Map<String, Any?>? = null
    val cameraSurface: Surface get() = if (mode.processing == ProcessingPath.DIRECT) surface else requireNotNull(processingInput)
    fun prepareCameraInput(preview: Surface, size: Size, monitor: MonitorTransform, ready: (Surface) -> Unit,
                           fault: (String) -> Unit) {
        handler.post {
            if (finished || stopping) return@post
            if (mode.processing == ProcessingPath.DIRECT) { ready(surface); return@post }
            check(processor == null)
            processor = GpuVideoProcessor.prepare(mode, surface, preview, size, handler, monitor, { input ->
                if (!finished && !stopping) { processingInput = input; ready(input) }
            }, { message ->
                if (!finished) { processingFailure = message; fault(message); finish() }
            })
            handler.postDelayed({
                if (!finished && !stopping && processingInput == null) {
                    processingFailure = "GPU initialization timed out"
                    fault(requireNotNull(processingFailure)); finish()
                }
            }, 8000)
        }
    }
    fun setMonitor(transform: MonitorTransform) { handler.post { processor?.setMonitor(transform) } }
    private fun closeProcessor(done: (String?) -> Unit) {
        val active = processor
        if (active == null || processingClosed) { done(processingFailure); return }
        processingCloseWaiters += done
        if (processingCloseRequested) return
        processingCloseRequested = true
        fun closed(error: String?) {
            if (processingClosed) return
            processingClosed = true
            if (error != null) processingFailure = error
            processingSnapshot = active.describe()
            val callbacks = processingCloseWaiters.toList(); processingCloseWaiters.clear()
            callbacks.forEach { it(processingFailure) }
        }
        active.close(::closed)
        handler.postDelayed({ closed("GPU/monitor shutdown timed out; native cleanup is unconfirmed") }, 3000)
    }
    private lateinit var coordinator: AvMuxCoordinator<MediaFormat>
    lateinit var surface: Surface; private set
    private val startGate = AvStartGate(audioMode.enabled)
    private var muxerStarted = false
    @Volatile private var finished = false
    private var stopping = false
    private var videoEos = false
    private var audioEos = !audioMode.enabled
    private var beganAt = 0L
    private var lastVideoAt = 0L
    private var lastAudioAt = 0L
    private val frameStats = FrameStatistics(mode.fps)
    private var audioSamples = 0L
    private var audioFailure: String? = null
    @Volatile private var applied: Map<String, Any?> = emptyMap()
    @Volatile private var sessionConfigured = false
    private val watchdog = object : Runnable {
        override fun run() {
            if (finished || stopping) return
            val now = SystemClock.elapsedRealtime()
            if (now - maxOf(beganAt, lastVideoAt) > 10_000L) complete(IllegalStateException("No written video frames for ten seconds"))
            else if (audioMode.enabled && now - maxOf(beganAt, lastAudioAt) > 10_000L)
                failAudio(IllegalStateException("No written AAC samples for ten seconds"))
            else handler.postDelayed(this, 500)
        }
    }

    private fun prepare() {
        try {
            output = PendingMedia.create(context, video = true)
            muxer = MediaMuxer(output.descriptor.fileDescriptor, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4).apply { setOrientationHint(orientation) }
            val tracks = mutableMapOf<Track, Int>()
            coordinator = AvMuxCoordinator(audioMode.enabled, object : AvMuxCoordinator.Sink<MediaFormat> {
                override fun start(formats: Map<Track, MediaFormat>) {
                    check(!muxerStarted)
                    formats.forEach { (track, format) -> tracks[track] = requireNotNull(muxer).addTrack(format) }
                    requireNotNull(muxer).start(); muxerStarted = true
                }
                override fun write(track: Track, buffer: ByteBuffer, ptsUs: Long, flags: Int) {
                    val info = MediaCodec.BufferInfo().apply { set(buffer.position(), buffer.remaining(), ptsUs, flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM.inv()) }
                    requireNotNull(muxer).writeSampleData(requireNotNull(tracks[track]), buffer, info)
                }
            }, onWritten = { track, _, ptsUs ->
                if (track == Track.VIDEO) { frameStats.add(ptsUs); lastVideoAt = SystemClock.elapsedRealtime() }
                else { audioSamples++; lastAudioAt = SystemClock.elapsedRealtime() }
                if (startGate.written(track)) onFirstSample()
            })
            if (audioMode.enabled) audio = AudioCapture.prepare(context, audioMode, handler, object : AudioCapture.Events {
                override fun format(format: MediaFormat) { if (!finished) coordinator.format(Track.AUDIO, format) }
                override fun sample(buffer: ByteBuffer, info: MediaCodec.BufferInfo) {
                    if (!finished) coordinator.sample(Track.AUDIO, buffer, info.presentationTimeUs, info.flags)
                }
                override fun ended() { audioEos = true; completeIfDrained() }
                override fun failed(error: Exception) { failAudio(error) }
                override fun meter(value: AudioCapture.Meter) { if (!finished && !stopping) onAudioMeter(value) }
            })
            codec = MediaCodec.createByCodecName(mode.encoder)
            codec.setCallback(object : MediaCodec.Callback() {
                override fun onInputBufferAvailable(codec: MediaCodec, index: Int) = Unit
                override fun onOutputFormatChanged(codec: MediaCodec, format: MediaFormat) {
                    if (!finished) try { coordinator.format(Track.VIDEO, format) } catch (e: Exception) { complete(e) }
                }
                override fun onOutputBufferAvailable(codec: MediaCodec, index: Int, info: MediaCodec.BufferInfo) {
                    if (finished) return
                    var error: Exception? = null
                    try {
                        if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                            val buffer = requireNotNull(codec.getOutputBuffer(index)).apply { position(info.offset); limit(info.offset + info.size) }
                            coordinator.sample(Track.VIDEO, buffer, info.presentationTimeUs, info.flags)
                        }
                    } catch (e: Exception) { error = e }
                    finally { runCatching { codec.releaseOutputBuffer(index, false) }.exceptionOrNull()?.let { if (error == null) error = IllegalStateException("Cannot release video buffer", it) } }
                    if (error != null) complete(error)
                    else if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) { videoEos = true; completeIfDrained() }
                }
                override fun onError(codec: MediaCodec, error: MediaCodec.CodecException) { complete(error) }
            }, handler)
            codec.configure(CameraCatalog.videoFormat(mode), null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            surface = codec.createInputSurface()
            codec.start()
        } catch (e: Exception) {
            finished = true
            handler.removeCallbacksAndMessages(null)
            val failedAudio = audio
            if (failedAudio != null) failedAudio.close { thread.quitSafely() }
            if (::codec.isInitialized) runCatching { codec.release() }
            if (::surface.isInitialized) runCatching { surface.release() }
            runCatching { muxer?.release() }
            if (::output.isInitialized) output.abort()
            if (failedAudio == null) thread.quitSafely()
            throw e
        }
    }

    fun sessionStarted() {
        sessionConfigured = true
        handler.post {
            if (finished || stopping) return@post
            beganAt = SystemClock.elapsedRealtime()
            try { audio?.start(); handler.post(watchdog) } catch (e: Exception) { failAudio(e) }
        }
    }
    fun noteApplied(values: Map<String, Any?>) { applied = values.toMap() }
    fun requestStopBoundary(cutoffNs: Long) { audio?.requestStopBoundary(cutoffNs); processor?.requestStop() }
    fun finish(cutoffNs: Long = System.nanoTime()) {
        requestStopBoundary(cutoffNs)
        handler.post {
            if (finished || stopping) return@post
            stopping = true; startGate.stop(); handler.removeCallbacks(watchdog)
            try {
                audio?.stopGracefully(cutoffNs)
                closeProcessor { error ->
                    if (error != null) processingFailure = error
                    if (!finished) try {
                        codec.signalEndOfInputStream()
                        handler.postDelayed({ if (!finished) complete(IllegalStateException("Audio/video end-of-stream timed out")) }, 8000)
                    } catch (e: Exception) { complete(e) }
                }
            } catch (e: Exception) { complete(e) }
        }
    }
    fun cancel(reason: String) { handler.post { complete(IllegalStateException(reason)) } }
    private fun failAudio(error: Exception) {
        if (finished) return
        if (audioFailure == null) {
            audioFailure = error.message ?: "Microphone failed"
            onAudioFault(requireNotNull(audioFailure))
        }
        // Drain captured PCM and video through the normal bounded EOS path. A broken
        // codec may time out; failure remains recovery, never a silently muted success.
        finish()
    }
    private fun completeIfDrained() { if (stopping && videoEos && audioEos) complete(audioFailure?.let { IllegalStateException(it) }) }

    private fun complete(initialError: Exception?) {
        if (finished) return
        finished = true; startGate.stop(); handler.removeCallbacks(watchdog)
        closeProcessor { error ->
            val failure = initialError ?: (error ?: processingFailure)?.let { IllegalStateException(it) }
            val activeAudio = audio
            if (activeAudio != null) activeAudio.close { closeError -> finalizeMedia(failure ?: closeError) }
            else finalizeMedia(failure)
        }
    }
    private fun finalizeMedia(initialError: Exception?) {
        var failure = initialError
        fun attempt(block: () -> Unit) { try { block() } catch (e: Exception) { if (failure == null) failure = e } }
        attempt { codec.stop() }; attempt { codec.release() }
        // Salvage bounded startup packets even when the other encoder never became ready.
        // Such a subset is recovery footage, never an automatic video-only success.
        attempt { if (coordinator.finish() && failure == null) failure = IllegalStateException("Requested tracks did not all start; partial footage retained") }
        if (muxerStarted) attempt { muxer?.stop() }
        attempt { muxer?.release() }; attempt { surface.release() }; attempt { output.closeDescriptor() }
        val audioEvidence = audio?.describe()
        var reportFile: File? = null
        val stats = frameStats.summary()
        val stages = JSONArray().put("advertised")
        if (sessionConfigured) stages.put("session_configured")
        if (stats.frames > 0) stages.put("encoded_frames_received").put("first_sample_written")
        if (audioSamples > 0) stages.put("audio_samples_written")
        if (stats.frames > 0 && audioSamples > 0) stages.put("av_samples_written")
        val outcome = VideoFinalizer.finish(
            samples = stats.frames, initialError = failure,
            verify = {
                if (mode.processing == ProcessingPath.GPU_HLG10) {
                    require(processingSnapshot?.get("cleanupConfirmed") == true && processingSnapshot?.get("error") == null) { "GPU recording/cleanup was not confirmed" }
                    require((processingSnapshot?.get("submittedFrames") as? Long ?: 0) >= 2) { "GPU supplied too few recorded frames" }
                    stages.put("gpu_hlg_pipeline_exercised")
                }
                RecordingVerifier.verify(context, output.uri, mode, audioMode).also { stages.put("container_and_output_checked") }
            },
            publish = { output.publish() }, retain = { reason -> output.retain(reason) }, discardEmpty = { output.abort() },
            saveReport = { result ->
                val report = JSONObject().put("schemaVersion", 3).put("kind", "recording-validation")
                    .put("device", jsonValue(ModeEvidence.device())).put("selectedMode", jsonValue(mode.describe()))
                    .put("requested", jsonValue(request)).put("mode", mode.label).put("encoder", mode.encoder)
                    .put("orientation", orientation).put("latestApplied", jsonValue(applied))
                    .put("videoOnly", !audioMode.enabled).put("customLog", false)
                    .put("colourPipeline", jsonValue(mode.colour.describe())).put("processing", jsonValue(processingSnapshot))
                    .put("processingError", processingFailure ?: JSONObject.NULL)
                    .put("audioMode", audioMode.name).put("audio", jsonValue(audioEvidence))
                    .put("timingQuality", timingQuality(audioEvidence, result.verification))
                    .put("audioError", audioFailure ?: JSONObject.NULL).put("audioEncodedSamples", audioSamples)
                    .put("commonEpochUs", coordinator.originUs ?: JSONObject.NULL)
                    .put("videoClock", if (Build.VERSION.SDK_INT >= 33) "explicit_monotonic_output" else "legacy_encoder_default_unverified")
                    .put("physicalLipSyncVerified", false).put("partialTrackRecovery", coordinator.partial)
                    .put("encodedSamples", stats.frames).put("encodedFrameGaps", stats.largeGaps)
                    .put("stages", stages).put("disposition", result.disposition.name.lowercase())
                    .put("verification", result.verification ?: JSONObject.NULL)
                    .put("status", when (result.disposition) {
                        VideoDisposition.PUBLISHED -> "checked"
                        VideoDisposition.RECOVERABLE -> "recoverable"
                        else -> "rejected"
                    }).put("error", result.errors.takeIf { it.isNotEmpty() }?.joinToString("; ") ?: JSONObject.NULL)
                val directory = File(context.filesDir, "exports/validation")
                check(directory.isDirectory || directory.mkdirs()) { "Validation directory is unavailable" }
                reportFile = File(directory, "recording-${UUID.randomUUID()}.json").also { atomicWrite(it, report.toString(2)) }
            }
        )
        val timing = timingQuality(audioEvidence, outcome.verification)
        val timingNote = if (audioMode.enabled) " Timing: ${timing.getString("status")}" +
            (timing.getJSONArray("warnings").takeIf { it.length() > 0 }?.let { " — ${it.join(", ")}" } ?: "") else ""
        val message = when (outcome.disposition) {
            VideoDisposition.PUBLISHED -> "Saved ${mode.label}; ${stats.frames} frames; ${if (audioMode.enabled) "AAC ${audioMode.channels}ch / 48 kHz" else "video only"}. File integrity checked; cadence ${outcome.verification?.optString("cadenceStatus") ?: "unknown"}. Physical sync and sustained performance are not certified.$timingNote"
            VideoDisposition.RECOVERABLE -> "Footage retained privately for recovery, NOT a verified recording: ${outcome.errors.joinToString("; ")}. Open Recover captures to export or delete it."
            VideoDisposition.EMPTY -> "Empty recording rejected; no encoded video footage arrived."
            VideoDisposition.RETENTION_FAILED -> "Recording needs recovery; no further deletion attempted: ${outcome.errors.joinToString("; ")}. Check Recover captures after reopening."
        } + (outcome.reportError?.let { " Validation report unavailable: $it. Media was not deleted." } ?: "")
        runCatching { CaptureHistory.save(context, listOfNotNull(outcome.uri), reportFile, message) }
        try { completed(Outcome(outcome.uri, reportFile, message, audioFailure)) } finally { thread.quitSafely() }
    }
    private fun timingQuality(audioEvidence: Map<String, Any?>?, verification: JSONObject?): JSONObject {
        val acquisition = audioEvidence?.get("acquisition") as? Map<*, *>
        val continuity = acquisition?.get("continuityStatus") as? String
        val warnings = JSONArray()
        if (audioMode.enabled) {
            if (continuity != "no_discontinuity_observed") warnings.put(continuity ?: "acquisition_unverified")
            if (Build.VERSION.SDK_INT < 33) warnings.put("legacy_video_clock_unverified")
            if (verification?.optString("avPacketCoverage") != "within_250ms") warnings.put("audio_video_coverage_warning")
        }
        return JSONObject().put("schemaVersion", 1).put("status", when {
            !audioMode.enabled -> "video_only"
            warnings.length() > 0 -> "warning"
            else -> "no_timing_warning_observed"
        }).put("warnings", warnings).put("physicalLipSyncVerified", false)
    }
    companion object {
        fun prepare(context: Context, mode: RecordingMode, orientation: Int, request: Map<String, Any?>,
                    audioMode: AudioMode = AudioMode.OFF, onFirstSample: () -> Unit = {},
                    onAudioMeter: (AudioCapture.Meter) -> Unit = {}, onAudioFault: (String) -> Unit = {},
                    completed: (Outcome) -> Unit): SurfaceRecorder =
            SurfaceRecorder(context.applicationContext, mode, orientation, request, audioMode, onFirstSample, onAudioMeter, onAudioFault, completed).apply { prepare() }
    }
}
