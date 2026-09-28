package com.s23log.probe.camera

import android.content.Context
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import android.net.Uri
import com.s23log.probe.core.DynamicRange
import com.s23log.probe.core.FrameStatistics
import com.s23log.probe.core.HevcSps
import com.s23log.probe.core.RecordingMode
import org.json.JSONObject
import java.nio.ByteBuffer

/** Container, sample timing, one decoded frame, and (for HLG) actual SPS + color-tag checks. */
object RecordingVerifier {
    fun verify(context: Context, uri: Uri, mode: RecordingMode): JSONObject {
        val extractor = MediaExtractor()
        val evidence = JSONObject()
        try {
            extractor.setDataSource(context, uri, null)
            val videoTracks = (0 until extractor.trackCount).filter {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true
            }
            require(videoTracks.size == 1) { "Expected one video track" }
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
            while (extractor.sampleTime >= 0) {
                buffer.clear()
                val count = extractor.readSampleData(buffer, 0)
                require(count > 0) { "Empty or unreadable encoded sample" }
                bytes += count
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
        } finally { extractor.release() }
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(context, uri)
            val frame = requireNotNull(retriever.getFrameAtTime(0, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)) { "Decoder could not return a video frame" }
            require(frame.width > 0 && frame.height > 0)
            frame.recycle()
            evidence.put("firstSyncFrameDecoded", true)
        } finally { retriever.release() }
        evidence.put("scope", "Container, all sample timestamps, one decoded frame; not a full-duration image-quality or thermal certification")
        return evidence
    }
}
