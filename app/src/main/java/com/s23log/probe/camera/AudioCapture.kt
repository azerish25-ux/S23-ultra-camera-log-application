package com.s23log.probe.camera

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTimestamp
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaRecorder
import android.os.Build
import android.os.Handler
import android.os.SystemClock
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.ChannelLevel
import com.s23log.probe.core.PcmClock
import com.s23log.probe.core.PcmLevels
import com.s23log.probe.core.PcmFrameQueue
import java.nio.ByteBuffer
import java.util.ArrayDeque
import java.nio.ByteOrder

/** Nonblocking microphone reads and AAC callbacks share the recorder's serial encoder handler. */
class AudioCapture private constructor(
    private val record: AudioRecord,
    private val codec: MediaCodec,
    private val preferredDeviceId: Int,
    val mode: AudioMode,
    private val handler: Handler,
    private val events: Events
) {
    data class Meter(val levels: List<ChannelLevel>, val route: String, val clockSource: String)
    interface Events {
        fun format(format: MediaFormat)
        fun sample(buffer: ByteBuffer, info: MediaCodec.BufferInfo)
        fun ended()
        fun failed(error: Exception)
        fun meter(value: Meter)
    }
    private val clock = PcmClock(AudioMode.SAMPLE_RATE)
    private val inputIndices = ArrayDeque<Int>()
    private val pending = PcmFrameQueue(mode.channels)
    private val shorts = ShortArray(1024 * mode.channels)
    private var readFrames = 0L
    private var queuedFrames = 0L
    private var firstReadNs = 0L
    private var firstReadFrames = 0L
    private var startedMs = 0L
    private var lastReadMs = 0L
    private var lastMeterMs = 0L
    private var firstQueueUs: Long? = null
    private var lastQueueEndUs = 0L
    private var started = false
    private var stopped = false
    private var closed = false
    private var eosQueued = false
    private var route = "Built-in microphone (awaiting route)"
    private var routeConfirmed = false
    private var clippingBlocks = 0
    private val pump = object : Runnable {
        override fun run() {
            if (closed || eosQueued) return
            try {
                val now = SystemClock.elapsedRealtime()
                if (!stopped) {
                    // Never block camera, UI, or encoder callbacks waiting for microphone data.
                    val count = record.read(shorts, 0, shorts.size, AudioRecord.READ_NON_BLOCKING)
                    check(count >= 0) { "Microphone read failed ($count); audio has NOT been disabled" }
                    if (count > 0) {
                        check(count % mode.channels == 0) { "Unaligned microphone frame" }
                        val frames = count / mode.channels
                        val data = ByteBuffer.allocate(count * 2).order(ByteOrder.nativeOrder())
                        data.asShortBuffer().put(shorts, 0, count)
                        pending.offer(data, readFrames); readFrames += frames
                        lastReadMs = now
                        if (firstReadNs == 0L) { firstReadNs = System.nanoTime(); firstReadFrames = readFrames }
                        val stamp = AudioTimestamp()
                        if (record.getTimestamp(stamp, AudioTimestamp.TIMEBASE_MONOTONIC) == AudioRecord.SUCCESS && stamp.nanoTime > 0 && stamp.framePosition >= 0)
                            clock.observe(stamp.framePosition, stamp.nanoTime)
                        if (now - lastMeterMs >= 125) {
                            inspectRoute(now)
                            val levels = PcmLevels.measure(shorts, count, mode.channels)
                            if (levels.any { it.clipped }) clippingBlocks++
                            events.meter(Meter(levels, route, if (clock.regressions > 0 || clock.maxDriftUs > 33_333) "${clock.source}:drift_warning" else clock.source)); lastMeterMs = now
                        }
                    }
                    check(now - lastReadMs <= 5000) { "Microphone produced no PCM for five seconds" }
                }
                // Some HALs do not supply AudioTimestamp. Preserve audio but explicitly expose uncertainty.
                if (!clock.anchored && firstReadNs > 0 && (stopped || now - startedMs >= 750))
                    clock.estimate(firstReadFrames, firstReadNs)
                queuePcm()
                if (!closed && !eosQueued) handler.postDelayed(this, 5)
            } catch (e: Exception) { events.failed(e) }
        }
    }

    @SuppressLint("MissingPermission") // Checked at prepare; revocation still throws and is retained as an error.
    fun start() {
        check(!started && !closed)
        started = true
        startedMs = SystemClock.elapsedRealtime(); lastReadMs = startedMs
        record.startRecording()
        check(record.recordingState == AudioRecord.RECORDSTATE_RECORDING) { "Microphone could not start" }
        codec.start()
        handler.post(pump)
    }
    private fun inspectRoute(now: Long) {
        val device = record.routedDevice
        if (device != null) {
            check(device.type == AudioDeviceInfo.TYPE_BUILTIN_MIC && device.id == preferredDeviceId) {
                "Microphone route changed; external inputs are not supported by this recording mode"
            }
            route = "${device.productName} · built-in · ${mode.channels}ch / 48 kHz"
            routeConfirmed = true
        } else check(now - startedMs < 2000) { "Unable to confirm the built-in microphone route" }
        if (Build.VERSION.SDK_INT >= 29) check(record.activeRecordingConfiguration?.isClientSilenced != true) {
            "Android silenced the microphone (privacy or competing capture); footage retained, not a valid audio recording"
        }
    }
    private fun queuePcm() {
        while (inputIndices.isNotEmpty() && pending.ready(stopped) && clock.anchored) {
            val index = inputIndices.removeFirst()
            val input = requireNotNull(codec.getInputBuffer(index)).apply { clear() }
            // AudioRecord reads may be partial. Coalesce them before AAC input;
            // tiny input buffers can cause codec timestamp rounding/discontinuities.
            val batch = requireNotNull(pending.drainTo(input, stopped))
            val ptsUs = clock.timestampUs(batch.firstFrame)
            check(ptsUs >= 0 && (firstQueueUs == null || ptsUs >= lastQueueEndUs)) { "Microphone clock regressed" }
            codec.queueInputBuffer(index, 0, batch.bytes, ptsUs, 0)
            firstQueueUs = firstQueueUs ?: ptsUs
            queuedFrames += batch.frames
            lastQueueEndUs = clock.timestampUs(batch.firstFrame + batch.frames)
        }
        if (stopped && pending.frames == 0 && inputIndices.isNotEmpty() && !eosQueued) {
            eosQueued = true
            codec.queueInputBuffer(inputIndices.removeFirst(), 0, 0, lastQueueEndUs.coerceAtLeast(0), MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        }
    }
    fun stopGracefully() {
        if (closed || stopped) return
        stopped = true
        if (!started) { events.ended(); return }
        // Reads are nonblocking and on this same handler; no worker join can deadlock a callback.
        if (record.recordingState == AudioRecord.RECORDSTATE_RECORDING) record.stop()
        handler.removeCallbacks(pump); handler.post(pump)
    }
    fun close() {
        if (closed) return
        closed = true
        handler.removeCallbacks(pump)
        var error: Exception? = null
        fun attempt(block: () -> Unit) { try { block() } catch (e: Exception) { if (error == null) error = e } }
        attempt { if (record.recordingState == AudioRecord.RECORDSTATE_RECORDING) record.stop() }
        attempt { record.release() }
        attempt { if (started) codec.stop() }
        attempt { codec.release() }
        pending.clear(); inputIndices.clear()
        error?.let { throw it }
    }
    fun describe(): Map<String, Any?> = mapOf(
        "requestedMode" to mode.name, "mime" to MediaFormat.MIMETYPE_AUDIO_AAC, "profile" to "AAC-LC",
        "sampleRate" to AudioMode.SAMPLE_RATE, "channels" to mode.channels, "bitrate" to mode.bitRate,
        "source" to "CAMCORDER", "route" to route, "builtInRouteConfirmed" to routeConfirmed,
        "pcmFramesRead" to readFrames, "pcmFramesQueued" to queuedFrames, "firstInputPtsUs" to firstQueueUs,
        "lastInputEndUs" to lastQueueEndUs, "clippingMeterBlocks" to clippingBlocks, "clock" to clock.describe()
    )

    companion object {
        @SuppressLint("MissingPermission") // Runtime permission is verified below, including direct controller callers.
        fun prepare(context: Context, mode: AudioMode, handler: Handler, events: Events): AudioCapture {
            require(mode.enabled)
            check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) { "Microphone permission is required; select video only explicitly to record without it" }
            val manager = context.getSystemService(AudioManager::class.java)
            val input = manager.getDevices(AudioManager.GET_DEVICES_INPUTS).firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_MIC }
                ?: error("No built-in microphone route is available")
            val channelMask = if (mode == AudioMode.STEREO) AudioFormat.CHANNEL_IN_STEREO else AudioFormat.CHANNEL_IN_MONO
            val minimum = AudioRecord.getMinBufferSize(AudioMode.SAMPLE_RATE, channelMask, AudioFormat.ENCODING_PCM_16BIT)
            check(minimum > 0) { "48 kHz ${mode.name.lowercase()} microphone input unavailable; choose another audio mode" }
            var record: AudioRecord? = null; var codec: MediaCodec? = null
            try {
                val builder = AudioRecord.Builder().setAudioSource(MediaRecorder.AudioSource.CAMCORDER)
                    .setAudioFormat(AudioFormat.Builder().setSampleRate(AudioMode.SAMPLE_RATE).setChannelMask(channelMask).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                    .setBufferSizeInBytes(maxOf(minimum * 2, AudioMode.SAMPLE_RATE / 5 * mode.channels * 2))
                if (Build.VERSION.SDK_INT >= 30) builder.setPrivacySensitive(true)
                record = builder.build()
                check(record.state == AudioRecord.STATE_INITIALIZED && record.sampleRate == AudioMode.SAMPLE_RATE && record.channelCount == mode.channels) { "Microphone format differs from the selected format" }
                check(record.setPreferredDevice(input)) { "Built-in microphone selection was rejected" }
                codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
                val capture = AudioCapture(record, codec, input.id, mode, handler, events)
                codec.setCallback(object : MediaCodec.Callback() {
                    override fun onInputBufferAvailable(codec: MediaCodec, index: Int) {
                        if (!capture.closed && !capture.eosQueued) capture.inputIndices.addLast(index)
                    }
                    override fun onOutputFormatChanged(codec: MediaCodec, format: MediaFormat) {
                        if (!capture.closed) try { events.format(format) } catch (e: Exception) { events.failed(e) }
                    }
                    override fun onOutputBufferAvailable(codec: MediaCodec, index: Int, info: MediaCodec.BufferInfo) {
                        if (capture.closed) return
                        var error: Exception? = null
                        try {
                            if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                                val buffer = requireNotNull(codec.getOutputBuffer(index)).apply { position(info.offset); limit(info.offset + info.size) }
                                events.sample(buffer, info)
                            }
                        } catch (e: Exception) { error = e }
                        finally { runCatching { codec.releaseOutputBuffer(index, false) }.exceptionOrNull()?.let { if (error == null) error = IllegalStateException("Audio output release failed", it) } }
                        if (error != null) events.failed(requireNotNull(error))
                        else if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) events.ended()
                    }
                    override fun onError(codec: MediaCodec, error: MediaCodec.CodecException) { if (!capture.closed) events.failed(error) }
                }, handler)
                codec.configure(MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, AudioMode.SAMPLE_RATE, mode.channels).apply {
                    setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
                    setInteger(MediaFormat.KEY_BIT_RATE, mode.bitRate)
                    setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 4096 * mode.channels)
                }, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
                return capture
            } catch (e: Exception) {
                runCatching { codec?.release() }; runCatching { record?.release() }; throw e
            }
        }
    }
}
