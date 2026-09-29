package com.s23log.probe

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.core.PcmClock
import com.s23log.probe.core.PcmFrameQueue
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Real AAC encoders must drain short final PCM without inventing a timestamp gap. */
@RunWith(AndroidJUnit4::class)
class AacTailTest {
    @Test fun monoAndStereoTailsKeepCodecPacketTimingContinuous() {
        val results = JSONArray()
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val report = File(context.filesDir, "exports/aac-tail-test.json")
        check(report.parentFile?.isDirectory == true || report.parentFile?.mkdirs() == true)
        fun save() = report.writeText(JSONObject().put("kind", "aac-tail-test")
            .put("appCommit", BuildConfig.SOURCE_REVISION).put("cases", results).toString(2))
        try {
            for (channels in 1..2) {
                for (tail in listOf(0, 1, 128, 512, 640, 1023)) {
                    results.put(encode(channels, tail, emptyEos = false)); save()
                }
                results.put(encode(channels, 0, emptyEos = true)); save()
            }
        } finally { save() }
        assertEquals(14, results.length())
    }

    private fun encode(channels: Int, tail: Int, emptyEos: Boolean): JSONObject {
        val frames = 8 * 1024 + tail
        val pcm = ByteBuffer.allocate(frames * channels * 2).order(ByteOrder.nativeOrder())
        // Deterministic, non-silent input; no microphone or permission needed for this test.
        repeat(frames * channels) { pcm.putShort(if (it % 100 < 50) 4096.toShort() else (-4096).toShort()) }
        pcm.flip()
        val queue = PcmFrameQueue(channels).apply { offer(pcm, 0) }
        val clock = PcmClock(48_000).apply { observe(0, 87_138_167_000L) }
        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        var started = false
        val times = mutableListOf<Long>()
        var submitted = 0L
        var inputEos = false
        var outputEos = false
        val label = "${channels}ch tail=$tail emptyEos=$emptyEos"
        try {
            codec.configure(MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, 48_000, channels).apply {
                setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
                setInteger(MediaFormat.KEY_BIT_RATE, if (channels == 1) 128_000 else 192_000)
                setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 4096 * channels)
            }, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            codec.start(); started = true
            val deadline = SystemClock.elapsedRealtime() + 15_000
            val info = MediaCodec.BufferInfo()
            while (!outputEos && SystemClock.elapsedRealtime() < deadline) {
                if (!inputEos) {
                    val index = codec.dequeueInputBuffer(1000)
                    if (index >= 0) {
                        val input = requireNotNull(codec.getInputBuffer(index)).apply { clear() }
                        val batch = queue.drainTo(input, stopping = !emptyEos)
                        if (batch != null) {
                            assertEquals(label, submitted, batch.firstFrame)
                            submitted += batch.frames
                            codec.queueInputBuffer(index, 0, batch.bytes, clock.timestampUs(batch.firstFrame),
                                if (batch.endOfStream) MediaCodec.BUFFER_FLAG_END_OF_STREAM else 0)
                            inputEos = batch.endOfStream
                        } else {
                            assertEquals("$label: empty EOS only after every sample", frames.toLong(), submitted)
                            codec.queueInputBuffer(index, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputEos = true
                        }
                    }
                }
                val index = codec.dequeueOutputBuffer(info, 1000)
                if (index >= 0) {
                    try {
                        if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0)
                            times += info.presentationTimeUs
                        outputEos = info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0
                    } finally { codec.releaseOutputBuffer(index, false) }
                }
            }
            assertTrue("$label: EOS timeout", outputEos)
            assertEquals("$label: all original PCM submitted", frames.toLong(), submitted)
            assertTrue("$label: not enough encoded frames", times.size >= (frames + 1023) / 1024)
            for ((a, b) in times.zipWithNext()) {
                assertTrue("$label: non-monotonic $a -> $b", b > a)
                assertTrue("$label: AAC packet gap ${b - a}us; timestamps=$times", b - a <= 32_000)
            }
            return JSONObject().put("channels", channels).put("tailFrames", tail).put("emptyEos", emptyEos)
                .put("encoder", codec.name).put("inputFrames", submitted).put("packets", times.size)
                .put("ptsUs", JSONArray(times)).put("passed", true)
        } finally {
            if (started) runCatching { codec.stop() }
            codec.release()
        }
    }
}
