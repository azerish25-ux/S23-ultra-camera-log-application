package com.s23log.probe.camera

import android.content.Context
import android.media.MediaCodec
import android.os.Build
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import android.net.Uri
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.AacLcConfig
import com.s23log.probe.core.DynamicRange
import com.s23log.probe.core.FrameStatistics
import com.s23log.probe.core.HevcSps
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.core.MediaIdentity
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.core.cadenceStatus
import org.json.JSONObject
import java.nio.ByteBuffer

/** Container, sample timing, one decoded frame, and (for HLG) actual SPS + color-tag checks. */
object RecordingVerifier {
    fun verify(context: Context, uri: Uri, mode: RecordingMode, audioMode: AudioMode = AudioMode.OFF): JSONObject {
        val extractor = MediaExtractor()
        val evidence = JSONObject()
        try {
            extractor.setDataSource(context, uri, null)
            val videoTracks = (0 until extractor.trackCount).filter {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true
            }
            require(videoTracks.size == 1) { "Expected one video track" }
            val audioTracks = (0 until extractor.trackCount).filter {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true
            }
            require(audioTracks.size == (if (audioMode.enabled) 1 else 0) && extractor.trackCount == 1 + audioTracks.size) {
                "Recorded tracks differ from the explicitly selected audio mode"
            }
            evidence.put("audioTrackCount", audioTracks.size).put("audioRequested", audioMode.enabled)
            val track = videoTracks.single()
            val format = extractor.getTrackFormat(track)
            require(format.getString(MediaFormat.KEY_MIME) == mode.mime) { "Recorded codec differs from the requested codec" }
            require(format.getInteger(MediaFormat.KEY_WIDTH) == mode.width && format.getInteger(MediaFormat.KEY_HEIGHT) == mode.height) { "Recorded dimensions differ from the selected mode" }
            evidence.put("mime", format.getString(MediaFormat.KEY_MIME)).put("width", mode.width).put("height", mode.height)
            fun integer(key: String): Int? = if (format.containsKey(key)) format.getInteger(key) else null
            evidence.put("colorStandard", integer(MediaFormat.KEY_COLOR_STANDARD) ?: JSONObject.NULL)
            evidence.put("colorTransfer", integer(MediaFormat.KEY_COLOR_TRANSFER) ?: JSONObject.NULL)
            evidence.put("colorRange", integer(MediaFormat.KEY_COLOR_RANGE) ?: JSONObject.NULL)
            if (mode.range == DynamicRange.HLG10) {
                val csd = requireNotNull(format.getByteBuffer("csd-0")) { "HLG10 output has no SPS data" }.duplicate()
                val bytes = ByteArray(csd.remaining()).also(csd::get)
                val depth = requireNotNull(HevcSps.bitDepth(bytes)) { "Cannot establish bit depth from HEVC SPS; refusing to label output HLG10" }
                evidence.put("lumaBitDepth", depth.luma).put("chromaBitDepth", depth.chroma)
                require(depth.luma == 10 && depth.chroma == 10) { "Encoder did not produce 10-bit HEVC" }
                require(integer(MediaFormat.KEY_COLOR_STANDARD) == MediaFormat.COLOR_STANDARD_BT2020) { "BT.2020 output tag is missing or incorrect" }
                require(integer(MediaFormat.KEY_COLOR_TRANSFER) == MediaFormat.COLOR_TRANSFER_HLG) { "HLG transfer tag is missing or incorrect" }
                require(integer(MediaFormat.KEY_COLOR_RANGE) == MediaFormat.COLOR_RANGE_LIMITED) { "Limited-range output tag is missing or incorrect" }
            }
            extractor.selectTrack(track)
            val buffer = ByteBuffer.allocate(16 * 1024 * 1024)
            val stats = FrameStatistics(mode.fps)
            var bytes = 0L
            var firstVideoUs: Long? = null
            var lastVideoUs = 0L
            while (extractor.sampleTime >= 0) {
                buffer.clear()
                val count = extractor.readSampleData(buffer, 0)
                require(count > 0) { "Empty or unreadable encoded sample" }
                bytes += count
                firstVideoUs = firstVideoUs ?: extractor.sampleTime
                lastVideoUs = extractor.sampleTime
                stats.add(extractor.sampleTime)
                if (!extractor.advance()) break
            }
            val summary = stats.summary()
            require(summary.frames >= 2) { "Recording is too short: fewer than two video samples" }
            require(summary.invalidTimestamps == 0) { "Non-monotonic encoded timestamps" }
            evidence.put("samples", summary.frames).put("encodedBytes", bytes)
                .put("sampleSpanUs", summary.durationUs).put("measuredFps", summary.measuredFps ?: JSONObject.NULL)
                .put("largeFrameIntervals", summary.largeGaps)
                .put("nominalFpsIsNotSustainedRateProof", true)
                .put("cadenceStatus", summary.cadenceStatus(mode.fps)).put("requestedFps", mode.fps)
                .put("cadenceToleranceFraction", 0.03).put("cadenceMinimumSpanUs", 2_000_000)
                .put("cadenceWarningPreservesFootage", true)
                .put("firstVideoPtsUs", firstVideoUs).put("lastVideoPtsUs", lastVideoUs)
            if (audioMode.enabled) {
                val audioTrack = audioTracks.single()
                val audioFormat = extractor.getTrackFormat(audioTrack)
                require(audioFormat.getString(MediaFormat.KEY_MIME) == MediaFormat.MIMETYPE_AUDIO_AAC) { "Expected AAC audio" }
                require(audioFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE) == AudioMode.SAMPLE_RATE &&
                    audioFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT) == audioMode.channels) { "Recorded audio format differs from selection" }
                val config = requireNotNull(audioFormat.getByteBuffer("csd-0")) { "Missing AAC configuration" }.duplicate()
                val configBytes = ByteArray(config.remaining()).also(config::get)
                require(AacLcConfig.matches(configBytes, AudioMode.SAMPLE_RATE, audioMode.channels)) { "Audio is not the selected 1024-frame AAC-LC format" }
                extractor.unselectTrack(track); extractor.selectTrack(audioTrack); extractor.seekTo(0, MediaExtractor.SEEK_TO_CLOSEST_SYNC)
                var count = 0L; var audioBytes = 0L; var firstAudio: Long? = null; var lastAudio = -1L; var gaps = 0
                val periodUs = 1024L * 1_000_000 / AudioMode.SAMPLE_RATE
                while (extractor.sampleTime >= 0) {
                    buffer.clear()
                    val size = extractor.readSampleData(buffer, 0)
                    require(size > 0) { "Unreadable audio sample" }
                    val pts = extractor.sampleTime
                    require(pts > lastAudio) { "Non-monotonic audio timestamps" }
                    if (lastAudio >= 0 && pts - lastAudio > periodUs * 3 / 2) gaps++
                    firstAudio = firstAudio ?: pts; lastAudio = pts; count++; audioBytes += size
                    if (!extractor.advance()) break
                }
                require(count >= 2) { "Fewer than two AAC samples" }
                val startOffset = requireNotNull(firstAudio) - requireNotNull(firstVideoUs)
                val endOffset = lastAudio + periodUs - (lastVideoUs + 1_000_000L / mode.fps)
                evidence.put("audio", JSONObject().put("mime", MediaFormat.MIMETYPE_AUDIO_AAC).put("profile", "AAC-LC")
                    .put("sampleRate", AudioMode.SAMPLE_RATE).put("channels", audioMode.channels).put("samples", count)
                    .put("encodedBytes", audioBytes).put("firstPtsUs", firstAudio).put("lastPtsUs", lastAudio)
                    .put("packetSpanUs", lastAudio - firstAudio).put("largeFrameIntervals", gaps)
                    .put("encoderDelaySamples", if (audioFormat.containsKey(MediaFormat.KEY_ENCODER_DELAY)) audioFormat.getInteger(MediaFormat.KEY_ENCODER_DELAY) else JSONObject.NULL)
                    .put("encoderPaddingSamples", if (audioFormat.containsKey(MediaFormat.KEY_ENCODER_PADDING)) audioFormat.getInteger(MediaFormat.KEY_ENCODER_PADDING) else JSONObject.NULL))
                    .put("avStartOffsetUs", startOffset).put("avEndOffsetUs", endOffset)
                    .put("avPacketCoverage", if (kotlin.math.abs(startOffset) <= 250_000 && kotlin.math.abs(endOffset) <= 250_000 && gaps == 0) "within_250ms" else "warning")
                    .put("packetCoverageIsNotLipSyncProof", true).put("physicalLipSyncVerified", false)
            }
        } finally { extractor.release() }
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(context, uri)
            val frame = requireNotNull(if (Build.VERSION.SDK_INT >= 27) retriever.getScaledFrameAtTime(0, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, 640, 360) else retriever.getFrameAtTime(0, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)) { "Decoder could not return a video frame" }
            require(frame.width > 0 && frame.height > 0)
            frame.recycle()
            evidence.put("firstSyncFrameDecoded", true)
        } finally { retriever.release() }
        if (audioMode.enabled) { decodeAudioFrame(context, uri, audioMode); evidence.put("firstAudioPcmDecoded", true) }
        val identity = requireNotNull(context.contentResolver.openInputStream(uri)) { "Finalized media is unavailable for identity verification" }
            .use(MediaIdentity::read)
        evidence.put("mediaIdentity", jsonValue(identity.describe()))
        evidence.put("scope", "Selected tracks, all packet timestamps, one video frame and (if requested) decoded audio PCM; not lip-sync, full-duration quality or thermal certification")
        return evidence
    }
    private fun decodeAudioFrame(context: Context, uri: Uri, mode: AudioMode) {
        val extractor = MediaExtractor()
        var decoder: MediaCodec? = null
        var started = false
        try {
            extractor.setDataSource(context, uri, null)
            val track = (0 until extractor.trackCount).single { extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME) == MediaFormat.MIMETYPE_AUDIO_AAC }
            val format = extractor.getTrackFormat(track)
            extractor.selectTrack(track)
            val codec = MediaCodec.createDecoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
            decoder = codec
            codec.configure(format, null, null, 0); codec.start(); started = true
            val info = MediaCodec.BufferInfo()
            var inputEnded = false
            val deadline = System.nanoTime() + 5_000_000_000L
            while (System.nanoTime() < deadline) {
                if (!inputEnded) {
                    val index = codec.dequeueInputBuffer(10_000)
                    if (index >= 0) {
                        val input = requireNotNull(codec.getInputBuffer(index)).apply { clear() }
                        val size = extractor.readSampleData(input, 0)
                        if (size < 0) {
                            codec.queueInputBuffer(index, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputEnded = true
                        } else {
                            codec.queueInputBuffer(index, 0, size, extractor.sampleTime, 0); extractor.advance()
                        }
                    }
                }
                val index = codec.dequeueOutputBuffer(info, 10_000)
                if (index >= 0) {
                    val hasPcm = info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0
                    try {
                        if (hasPcm) {
                            require(codec.outputFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE) == AudioMode.SAMPLE_RATE &&
                                codec.outputFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT) == mode.channels) { "Decoded PCM format mismatch" }
                            require(requireNotNull(codec.getOutputBuffer(index)).capacity() >= info.offset + info.size)
                            return
                        }
                    } finally { codec.releaseOutputBuffer(index, false) }
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                }
            }
            error("Audio decoder returned no PCM before the deadline")
        } finally {
            if (started) runCatching { decoder?.stop() }
            decoder?.release(); extractor.release()
        }
    }
}
