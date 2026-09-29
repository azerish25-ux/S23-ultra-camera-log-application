package com.s23log.probe

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.GLES20
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.core.AvMuxCoordinator
import com.s23log.probe.core.AvMuxCoordinator.Track
import com.s23log.probe.core.PcmHandoff
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sin

/** Test APK only: known flashes/tones through real AVC/AAC and the production handoff/mux coordinator. */
@RunWith(AndroidJUnit4::class)
class TimingFixtureTest {
    @Test fun knownEventsSurviveDelayedMuxingAt24And30Fps() {
        val root = File(InstrumentationRegistry.getInstrumentation().targetContext.filesDir, "exports/timing-fixtures")
        check(root.isDirectory || root.mkdirs())
        val fixtures = JSONArray()
        for (fps in listOf(24, 30)) fixtures.put(record(root, fps))
        File(root, "manifest.json").writeText(JSONObject().put("schemaVersion", 1).put("kind", "synthetic-av-timing")
            .put("appCommit", BuildConfig.SOURCE_REVISION).put("physicalLipSyncVerified", false)
            .put("fixtures", fixtures).toString(2))
    }
    private fun record(root: File, fps: Int): JSONObject {
        val file = File(root, "markers-$fps.mp4")
        val video = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        val audio = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        val muxer = MediaMuxer(file.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val tracks = mutableMapOf<Track, Int>()
        var started = false; var writes = 0; var delayedWrites = 0
        var audioDelay: Int? = null; var audioPadding: Int? = null
        val coordinator = AvMuxCoordinator(true, object : AvMuxCoordinator.Sink<MediaFormat> {
            override fun start(formats: Map<Track, MediaFormat>) {
                formats.forEach { (t, f) -> tracks[t] = muxer.addTrack(f) }
                muxer.start(); started = true
            }
            override fun write(track: Track, buffer: ByteBuffer, ptsUs: Long, flags: Int) {
                if (++writes % 29 == 0) { delayedWrites++; Thread.sleep(75) }
                val info = MediaCodec.BufferInfo().apply { set(buffer.position(), buffer.remaining(), ptsUs, flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM.inv()) }
                muxer.writeSampleData(requireNotNull(tracks[track]), buffer, info)
            }
        }, { _, _, _ -> })
        var display = EGL14.EGL_NO_DISPLAY
        var context = EGL14.EGL_NO_CONTEXT
        var window = EGL14.EGL_NO_SURFACE
        var input: android.view.Surface? = null
        var videoStarted = false; var audioStarted = false
        try {
            video.configure(MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, 320, 180).apply {
                setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
                setInteger(MediaFormat.KEY_BIT_RATE, 600_000); setInteger(MediaFormat.KEY_FRAME_RATE, fps)
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1); setInteger(MediaFormat.KEY_MAX_B_FRAMES, 0)
            }, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            input = video.createInputSurface()
            audio.configure(MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, 48000, 1).apply {
                setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
                setInteger(MediaFormat.KEY_BIT_RATE, 128000); setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 4096)
            }, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
            val version = IntArray(2)
            check(EGL14.eglInitialize(display, version, 0, version, 1))
            val configs = arrayOfNulls<android.opengl.EGLConfig>(1); val num = IntArray(1)
            val attributes = intArrayOf(EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8, EGL14.EGL_BLUE_SIZE, 8,
                EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT, 0x3142, 1, EGL14.EGL_NONE)
            check(EGL14.eglChooseConfig(display, attributes, 0, configs, 0, 1, num, 0) && num[0] > 0)
            context = EGL14.eglCreateContext(display, configs[0], EGL14.EGL_NO_CONTEXT,
                intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0)
            window = EGL14.eglCreateWindowSurface(display, configs[0], input, intArrayOf(EGL14.EGL_NONE), 0)
            check(EGL14.eglMakeCurrent(display, window, window, context))
            video.start(); videoStarted = true; audio.start(); audioStarted = true
            val epochUs = 10_000_000L
            val audioOffsetUs = 125_000L // A separate track reset would visibly move both tones by 125 ms.
            val totalPcm = 234_000 // 5s minus the deliberate 125ms audio start offset.
            val pipe = PcmHandoff(1)
            var frame = 0; var pcmFrame = 0; var videoInputEos = false; var audioInputEos = false
            var videoOutputEos = false; var audioOutputEos = false
            fun drain(codec: MediaCodec, track: Track): Boolean {
                val info = MediaCodec.BufferInfo()
                var eos = false
                while (true) {
                    val index = codec.dequeueOutputBuffer(info, 0)
                    if (index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        val format = codec.outputFormat
                        if (track == Track.AUDIO) {
                            if (format.containsKey(MediaFormat.KEY_ENCODER_DELAY)) audioDelay = format.getInteger(MediaFormat.KEY_ENCODER_DELAY)
                            if (format.containsKey(MediaFormat.KEY_ENCODER_PADDING)) audioPadding = format.getInteger(MediaFormat.KEY_ENCODER_PADDING)
                        }
                        coordinator.format(track, format)
                    } else if (index >= 0) {
                        try {
                            if (info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                                val bytes = requireNotNull(codec.getOutputBuffer(index)).apply { position(info.offset); limit(info.offset + info.size) }
                                coordinator.sample(track, bytes, info.presentationTimeUs, info.flags)
                            }
                            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) eos = true
                        } finally { codec.releaseOutputBuffer(index, false) }
                    } else break
                }
                return eos
            }
            val deadline = SystemClock.elapsedRealtime() + 30_000
            while ((!videoOutputEos || !audioOutputEos) && SystemClock.elapsedRealtime() < deadline) {
                if (!videoInputEos) {
                    if (frame < 5 * fps) {
                        val light = if (frame in fps..(fps + 1) || frame in (4 * fps)..(4 * fps + 1)) 1f else 0f
                        GLES20.glViewport(0, 0, 320, 180); GLES20.glClearColor(light, light, light, 1f)
                        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
                        check(EGLExt.eglPresentationTimeANDROID(display, window, epochUs * 1000 + frame * 1_000_000_000L / fps))
                        check(EGL14.eglSwapBuffers(display, window)); frame++
                    } else { video.signalEndOfInputStream(); videoInputEos = true }
                }
                if (!audioInputEos) {
                    val index = audio.dequeueInputBuffer(1000)
                    if (index >= 0) {
                        val size = minOf(1024, totalPcm - pcmFrame)
                        val bytes = ByteBuffer.allocate(size * 2).order(ByteOrder.nativeOrder())
                        repeat(size) { i ->
                            val globalFrame = 6000 + pcmFrame + i
                            val tone = globalFrame in 48000 until 50400 || globalFrame in 192000 until 194400
                            bytes.putShort(if (tone) (16000 * sin(2.0 * Math.PI * 1000 * globalFrame / 48000)).toInt().toShort() else 0)
                        }
                        bytes.flip(); pipe.offer(bytes, pcmFrame.toLong()); pcmFrame += size
                        if (pcmFrame == totalPcm) pipe.finish()
                        val dst = requireNotNull(audio.getInputBuffer(index)).apply { clear() }
                        val batch = requireNotNull(pipe.drain(dst))
                        audio.queueInputBuffer(index, 0, batch.bytes, epochUs + audioOffsetUs + batch.firstFrame * 1_000_000 / 48000,
                            if (batch.endOfStream) MediaCodec.BUFFER_FLAG_END_OF_STREAM else 0)
                        audioInputEos = batch.endOfStream
                    }
                }
                if (!videoOutputEos) videoOutputEos = drain(video, Track.VIDEO)
                if (!audioOutputEos) audioOutputEos = drain(audio, Track.AUDIO)
            }
            assertTrue("Synthetic fixture EOS timeout", videoOutputEos && audioOutputEos)
            assertFalse(coordinator.finish()); assertTrue(delayedWrites > 0)
            muxer.stop(); started = false
            return JSONObject().put("file", file.name).put("fps", fps).put("eventsSeconds", JSONArray(listOf(1.0, 4.0)))
                .put("audioInputStartOffsetUs", audioOffsetUs).put("audioEncoderDelaySamples", audioDelay ?: JSONObject.NULL)
                .put("audioEncoderPaddingSamples", audioPadding ?: JSONObject.NULL).put("sampleRate", 48000)
                .put("delayedWrites", delayedWrites).put("delayPerWriteMs", 75).put("commonEpochUs", coordinator.originUs)
                .put("producer", "synthetic_test_apk_only").put("physicalLipSyncVerified", false)
        } finally {
            if (display != EGL14.EGL_NO_DISPLAY) {
                EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
                if (window != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, window)
                if (context != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(display, context)
                EGL14.eglTerminate(display)
            }
            if (videoStarted) runCatching { video.stop() }; video.release(); input?.release()
            if (audioStarted) runCatching { audio.stop() }; audio.release()
            if (started) runCatching { muxer.stop() }; muxer.release()
        }
    }
}
