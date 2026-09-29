package com.s23log.probe

import android.Manifest
import android.media.MediaCodec
import android.media.MediaFormat
import android.os.Handler
import android.os.HandlerThread
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.camera.AudioCapture
import com.s23log.probe.core.AudioMode
import com.s23log.probe.diagnostics.jsonValue
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Freeze the AAC consumer while the actual AudioRecord owner continues reading. */
@RunWith(AndroidJUnit4::class)
class AudioAcquisitionLoadTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.RECORD_AUDIO)
    @Test fun readerProgressesDuringBlockedEncoderHandlerAndDrainsOnStop() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val thread = HandlerThread("S23Log-test-encoder").apply { start() }
        val handler = Handler(thread.looper)
        val first = CountDownLatch(1); val ended = CountDownLatch(1); val closed = CountDownLatch(1)
        val blocked = CountDownLatch(1); val unblock = CountDownLatch(1)
        val error = AtomicReference<Exception?>(); val capture = AtomicReference<AudioCapture?>()
        val evidence = AtomicReference<Map<String, Any?>?>()
        handler.post {
            try {
                val audio = AudioCapture.prepare(context, AudioMode.MONO, handler, object : AudioCapture.Events {
                    override fun format(format: MediaFormat) = Unit
                    override fun sample(buffer: ByteBuffer, info: MediaCodec.BufferInfo) { first.countDown() }
                    override fun ended() { ended.countDown() }
                    override fun failed(failure: Exception) { error.compareAndSet(null, failure); first.countDown(); ended.countDown() }
                    override fun meter(value: AudioCapture.Meter) = Unit
                })
                capture.set(audio); audio.start()
            } catch (e: Exception) { error.set(e); first.countDown(); ended.countDown() }
        }
        try {
            assertTrue("AAC startup timeout", first.await(10, TimeUnit.SECONDS)); assertNull(error.get())
            val audio = requireNotNull(capture.get())
            fun accepted(): Long = (audio.acquisitionEvidence()["handoff"] as Map<*, *>) ["acceptedFrames"] as Long
            handler.post { blocked.countDown(); unblock.await(2, TimeUnit.SECONDS) }
            assertTrue(blocked.await(3, TimeUnit.SECONDS))
            val before = accepted(); Thread.sleep(250); val after = accepted()
            unblock.countDown()
            assertTrue("Microphone acquisition stopped with the encoder handler: $before -> $after", after > before)
            handler.post { audio.stopGracefully() }
            assertTrue("AAC EOS timeout", ended.await(10, TimeUnit.SECONDS)); assertNull(error.get())
            handler.post { audio.close { e ->
                if (e != null) error.compareAndSet(null, e)
                evidence.set(audio.describe()); closed.countDown()
            } }
            assertTrue(closed.await(4, TimeUnit.SECONDS)); assertNull(error.get())
            val report = JSONObject(jsonValue(requireNotNull(evidence.get())).toString())
            assertEquals(report.getLong("pcmFramesRead"), report.getLong("pcmFramesQueued"))
            assertTrue(report.getJSONObject("acquisition").getBoolean("readerTerminated"))
            assertEquals(0, report.getJSONObject("acquisition").getJSONObject("handoff").getInt("overflowCount"))
            val directory = File(context.filesDir, "exports"); check(directory.isDirectory || directory.mkdirs())
            File(directory, "acquisition-load-test.json").writeText(JSONObject().put("kind", "acquisition-load-test")
                .put("appCommit", BuildConfig.SOURCE_REVISION).put("encoderHandlerBlockedMs", 250)
                .put("acceptedBeforeBlock", before).put("acceptedDuringBlock", after)
                .put("readerProgressed", true).put("allReadPcmSubmitted", true).put("readerTerminated", true)
                .put("audio", report).put("physicalLipSyncVerified", false).toString(2))
        } finally {
            unblock.countDown()
            if (closed.count > 0) {
                handler.post { capture.get()?.close { closed.countDown() } ?: closed.countDown() }
                closed.await(4, TimeUnit.SECONDS)
            }
            thread.quitSafely()
        }
    }
}
