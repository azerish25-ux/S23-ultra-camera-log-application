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
import com.s23log.probe.core.PcmHandoff
import com.s23log.probe.core.MicrophoneReader
import java.util.concurrent.atomic.AtomicBoolean
import java.nio.ByteBuffer
import java.util.ArrayDeque
import java.nio.ByteOrder

/** Microphone acquisition has its own owner; only AAC and handoff draining use the encoder handler. */
class AudioCapture private constructor(
    private val record: AudioRecord,
    private val codec: MediaCodec,
    private val preferredDeviceId: Int,
    val mode: AudioMode,
    private val handler: Handler,
    private val events: Events
) {
    data class Meter(val levels: List<ChannelLevel>, val route: String, val clockSource: String, val timingStatus: String = "clock_unverified")
    interface Events {
        fun format(format: MediaFormat)
        fun sample(buffer: ByteBuffer, info: MediaCodec.BufferInfo)
        fun ended()
        fun failed(error: Exception)
        fun meter(value: Meter)
    }
    private val clock = PcmClock(AudioMode.SAMPLE_RATE, stableStartup = true)
    private val inputIndices = ArrayDeque<Int>() // Encoder-handler owned.
    private val pending = PcmHandoff(mode.channels)
    private var queuedFrames = 0L
    private var endPaddingFrames = 0
    private var lastEncoderInputEndUs = 0L
    private var lastMeterMs = 0L
    private var firstQueueUs: Long? = null
    private var lastQueueEndUs = 0L
    private var started = false
    private var stopped = false
    @Volatile private var closed = false
    private var eosQueued = false
    private var readerFailureNotified = false
    @Volatile private var route = "Built-in microphone (awaiting route)"
    @Volatile private var routeConfirmed = false
    private val pumpPosted = AtomicBoolean()
    private val reader = MicrophoneReader(mode.channels, record.bufferSizeInFrames,
        object : MicrophoneReader.Source {
            private var startedNs = 0L
            @SuppressLint("MissingPermission")
            override fun start() {
                record.startRecording(); startedNs = System.nanoTime()
                check(record.recordingState == AudioRecord.RECORDSTATE_RECORDING) { "Microphone could not start" }
            }
            override fun read(samples: ShortArray, count: Int): Int = record.read(samples, 0, count, AudioRecord.READ_NON_BLOCKING)
            override fun timestamp(): MicrophoneReader.Stamp? {
                val stamp = AudioTimestamp()
                return if (record.getTimestamp(stamp, AudioTimestamp.TIMEBASE_MONOTONIC) == AudioRecord.SUCCESS && stamp.nanoTime > 0 && stamp.framePosition >= 0)
                    MicrophoneReader.Stamp(stamp.framePosition, stamp.nanoTime) else null
            }
            override fun inspect() {
                val device = record.routedDevice
                if (device != null) {
                    check(device.type == AudioDeviceInfo.TYPE_BUILTIN_MIC && device.id == preferredDeviceId) {
                        "Microphone route changed; external inputs are not supported by this recording mode"
                    }
                    route = "${device.productName} · built-in · ${mode.channels}ch / 48 kHz"; routeConfirmed = true
                } else check(System.nanoTime() - startedNs < 2_000_000_000) { "Unable to confirm the built-in microphone route" }
                if (Build.VERSION.SDK_INT >= 29) check(record.activeRecordingConfiguration?.isClientSilenced != true) {
                    "Android silenced the microphone (privacy or competing capture); footage retained, not a valid audio recording"
                }
            }
            override fun close() {
                try { if (record.recordingState == AudioRecord.RECORDSTATE_RECORDING) record.stop() }
                finally { record.release() }
            }
        }, pending, clock, ::schedulePump,
        initializeThread = { android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_AUDIO) })
    private val pump = Runnable {
        pumpPosted.set(false)
        if (!closed && !eosQueued) try {
            if (reader.done && reader.failure != null && !readerFailureNotified) {
                readerFailureNotified = true
                // Stop the video too, but still drain already accepted PCM before finalization.
                events.failed(requireNotNull(reader.failure))
            }
            if (!closed) {
                queuePcm()
                val now = SystemClock.elapsedRealtime()
                if (!stopped && now - lastMeterMs >= 125 && reader.levels.isNotEmpty()) {
                    events.meter(Meter(reader.levels, route, clock.source, reader.continuity())); lastMeterMs = now
                }
            }
        } catch (e: Exception) { events.failed(e) }
    }
    private fun schedulePump() {
        if (!closed && pumpPosted.compareAndSet(false, true)) {
            if (!handler.post(pump)) pumpPosted.set(false)
        }
    }
    fun start() {
        check(!started && !closed)
        codec.start(); started = true
        reader.start()
    }
    private fun queuePcm() {
        while (!closed && !eosQueued && inputIndices.isNotEmpty() && pending.ready() && clock.anchored) {
            val index = inputIndices.removeFirst()
            val input = requireNotNull(codec.getInputBuffer(index)).apply { clear() }
            val batch = requireNotNull(pending.drain(input))
            val ptsUs = clock.timestampUs(batch.firstFrame)
            check(ptsUs >= 0 && (firstQueueUs == null || ptsUs >= lastQueueEndUs)) { "Microphone clock regressed" }
            codec.queueInputBuffer(index, 0, batch.bytes, ptsUs,
                if (batch.endOfStream) MediaCodec.BUFFER_FLAG_END_OF_STREAM else 0)
            if (batch.endOfStream) eosQueued = true
            firstQueueUs = firstQueueUs ?: ptsUs
            queuedFrames += batch.frames; endPaddingFrames += batch.paddingFrames
            lastQueueEndUs = clock.timestampUs(batch.firstFrame + batch.frames)
            lastEncoderInputEndUs = clock.timestampUs(batch.firstFrame + batch.frames + batch.paddingFrames)
        }
        if (reader.done && pending.exhausted() && inputIndices.isNotEmpty() && !eosQueued) {
            eosQueued = true
            codec.queueInputBuffer(inputIndices.removeFirst(), 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        }
    }
    /** Thread-safe cutoff signalling does not wait behind codec or disk callbacks. */
    fun requestStopBoundary(cutoffNs: Long) { reader.requestStop(cutoffNs) }
    fun stopGracefully(cutoffNs: Long = System.nanoTime()) {
        if (closed || stopped) return
        stopped = true; reader.requestStop(cutoffNs)
        if (!started) { reader.cancel(); events.ended(); return }
        schedulePump()
    }
    /** Async native-owner shutdown. Never join a microphone thread on an encoder/camera/UI thread. */
    fun close(completed: (Exception?) -> Unit = {}) {
        if (closed) { completed(null); return }
        closed = true; reader.cancel(); handler.removeCallbacks(pump)
        var error: Exception? = null
        fun attempt(block: () -> Unit) { try { block() } catch (e: Exception) { if (error == null) error = e } }
        attempt { if (started) codec.stop() }; attempt { codec.release() }
        inputIndices.clear()
        val deadline = SystemClock.elapsedRealtime() + 2000
        val checkOwner = object : Runnable {
            override fun run() {
                if (!reader.done && SystemClock.elapsedRealtime() < deadline) { handler.postDelayed(this, 10); return }
                if (!reader.done && error == null) error = IllegalStateException("Microphone owner shutdown timed out; native release unconfirmed")
                if (error == null) error = reader.failure
                // Snapshot retains accepted/consumed counts even on an exceptional abort.
                pending.cancel()
                completed(error)
            }
        }
        handler.post(checkOwner)
    }
    fun acquisitionEvidence(): Map<String, Any?> = reader.describe()
    fun describe(): Map<String, Any?> = mapOf(
        "requestedMode" to mode.name, "mime" to MediaFormat.MIMETYPE_AUDIO_AAC, "profile" to "AAC-LC",
        "sampleRate" to AudioMode.SAMPLE_RATE, "channels" to mode.channels, "bitrate" to mode.bitRate,
        "source" to "CAMCORDER", "route" to route, "builtInRouteConfirmed" to routeConfirmed,
        "pcmFramesRead" to reader.framesRead, "pcmFramesQueued" to queuedFrames, "firstInputPtsUs" to firstQueueUs,
        "pcmFramesSubmittedWithPadding" to (queuedFrames + endPaddingFrames), "appEndPaddingFrames" to endPaddingFrames,
        "appEndPaddingUs" to (endPaddingFrames * 1_000_000L / AudioMode.SAMPLE_RATE), "appEndPaddingTrimmed" to false,
        "lastInputEndUs" to lastQueueEndUs, "lastEncoderInputEndUs" to lastEncoderInputEndUs,
        "clippingMeterBlocks" to reader.clippingBlocks, "clock" to clock.describe(),
        "acquisition" to reader.describe(), "timingSchemaVersion" to 1
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
                        if (!capture.closed && !capture.eosQueued) { capture.inputIndices.addLast(index); capture.schedulePump() }
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
