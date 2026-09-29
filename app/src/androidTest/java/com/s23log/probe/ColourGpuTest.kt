package com.s23log.probe

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaFormat
import android.media.MediaMuxer
import android.net.Uri
import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.GLES30 as GL
import android.os.Build
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.camera.RecordingVerifier
import com.s23log.probe.core.*
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.gpu.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import kotlin.math.abs

/** Pixel evidence is mandatory. Missing HDR hardware is separately reported, never a precision pass. */
@RunWith(AndroidJUnit4::class)
class ColourGpuTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun save(name:String,data:JSONObject) {
        val dir=File(context.filesDir,"exports/colour");check(dir.isDirectory||dir.mkdirs())
        File(dir,name).writeText(data.put("appCommit",BuildConfig.SOURCE_REVISION).put("physicalCameraCertified",false).toString(2))
    }
    @Test fun fp16PixelsMatchReferencesAndRejectEightBitIntermediate() {
        GlEnvironment.create().use { env ->
            val probe=ColourGpuProbe.run()
            val patches=listOf(doubleArrayOf(0.0,0.0,0.0),doubleArrayOf(1.0,1.0,1.0),doubleArrayOf(.18,.18,.18),
                doubleArrayOf(1.0,0.0,0.0),doubleArrayOf(0.0,1.0,0.0),doubleArrayOf(0.0,0.0,1.0),doubleArrayOf(.125,.51,.87))
            var matrixError=0.0;var monitorError=0.0
            val out=GlTools.texture(patches.size,1,GL.GL_RGBA16F);val fbo=GlTools.fbo(out)
            try {
                ColourRenderer(patches.size,1).use { renderer ->
                    val packed=FloatArray(patches.size*4) { i -> if(i%4==3)1f else patches[i/4][i%4].toFloat() }
                    val source=GlTools.texture(patches.size,1,GL.GL_RGBA16F,GlTools.floats(packed))
                    try {
                        renderer.import(source);renderer.monitor(fbo,patches.size,1,MonitorTransform.SDR_TONEMAP)
                        val actual=GlTools.readFloatRgba(fbo,patches.size,1)
                        patches.forEachIndexed { i,rgb ->
                            val expected=ColourMath.sdrMonitor(rgb.map(ColourMath::hlgDecode).toDoubleArray())
                            for(c in 0..2) monitorError=maxOf(monitorError,abs(actual[i*4+c]-expected[c]))
                        }
                        assertTrue("Monitor CPU/GPU error $monitorError",monitorError<0.002)
                    } finally { GL.glDeleteTextures(1,intArrayOf(source),0) }
                    val yuv=FloatArray(patches.size*4)
                    patches.forEachIndexed { i,rgb ->
                        val v=ColourMath.hlgToLimitedYuv10(rgb[0],rgb[1],rgb[2]);for(c in 0..2)yuv[4*i+c]=v[c].toFloat();yuv[4*i+3]=1f
                    }
                    val sourceYuv=GlTools.texture(patches.size,1,GL.GL_RGBA16F,GlTools.floats(yuv))
                    try {
                        renderer.import(sourceYuv,yuv=true);renderer.record(fbo)
                        val actual=GlTools.readFloatRgba(fbo,patches.size,1)
                        patches.forEachIndexed { i,rgb ->for(c in 0..2)matrixError=maxOf(matrixError,abs(actual[i*4+c]-rgb[c])) }
                        assertTrue("BT.2020 matrix/range CPU/GPU error $matrixError",matrixError<0.003)
                    } finally { GL.glDeleteTextures(1,intArrayOf(sourceYuv),0) }
                }
            } finally { GL.glDeleteFramebuffers(1,intArrayOf(fbo),0);GL.glDeleteTextures(1,intArrayOf(out),0) }
            save("gpu.json",JSONObject().put("kind","colour-gpu").put("status","passed")
                .put("gpu",jsonValue(env.describe())).put("probe",jsonValue(probe))
                .put("bt2020PatchMaximumError",matrixError).put("monitorMaximumError",monitorError)
                .put("cameraYuvImportTested",false).put("scope","Synthetic texture pixel tests; camera and encoder have separate gates"))
        }
    }
    @Test fun renderedHlgEncoderIsTestedOnlyWhenItsHardwarePathIsAvailable() {
        fun unavailable(stage:String,reason:String) = save("encoder.json",JSONObject().put("kind","colour-encoder")
            .put("status","unavailable").put("stage",stage).put("reason",reason).put("encodedPixelsTested",false))
        if(Build.VERSION.SDK_INT<33) { unavailable("api","API 33 required");return }
        val candidate=MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.filter { it.isEncoder && !it.isAlias }
            .firstOrNull { info -> runCatching {
                val caps=info.getCapabilitiesForType(MediaFormat.MIMETYPE_VIDEO_HEVC)
                (caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_HdrEditing) ||
                    (Build.VERSION.SDK_INT>=35 && caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_HlgEditing))) &&
                    caps.profileLevels.any { it.profile==MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10 } &&
                    caps.videoCapabilities.areSizeAndRateSupported(1024,128,30.0)
            }.getOrDefault(false) }
        if(candidate==null) { unavailable("encoder","No advertised RGB10 HLG editing encoder at 1024x128/30");return }
        val env=try { GlEnvironment.create(rgb10=true) } catch(e:Exception) { unavailable("egl_rgb10",e.message?:e.toString());return }
        env.use {
            if("EGL_EXT_gl_colorspace_bt2020_hlg" !in EGL14.eglQueryString(env.display,EGL14.EGL_EXTENSIONS).orEmpty().split(' ')) {
                unavailable("egl_hlg","EGL HLG colourspace extension unavailable");return
            }
            val dir=File(context.filesDir,"exports/colour");check(dir.isDirectory||dir.mkdirs())
            val file=File(dir,"hlg-ramp.mp4")
            val codec=MediaCodec.createByCodecName(candidate.name)
            val muxer=MediaMuxer(file.path,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val mode=RecordingMode(1024,128,30,DynamicRange.HLG10,candidate.name,MediaFormat.MIMETYPE_VIDEO_HEVC,
                8_000_000,true,true,processing=ProcessingPath.GPU_HLG10)
            var window=EGL14.EGL_NO_SURFACE;var surface:android.view.Surface?=null
            var started=false;var muxed=false;var track=-1;var eos=false;var texture=0
            try {
                codec.configure(CameraCatalog.videoFormat(mode),null,null,MediaCodec.CONFIGURE_FLAG_ENCODE)
                surface=codec.createInputSurface();window=env.window(surface,hlg=true);env.current(window)
                codec.start();started=true
                val ramp=FloatArray(1024*128*4) { i -> if(i%4==3)1f else ((i/4)%1024)/1023f }
                texture=GlTools.texture(1024,128,GL.GL_RGBA16F,GlTools.floats(ramp))
                fun drain() {
                    val bi=MediaCodec.BufferInfo()
                    while(true) {
                        val index=codec.dequeueOutputBuffer(bi,1000)
                        if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) { track=muxer.addTrack(codec.outputFormat);muxer.start();muxed=true }
                        else if(index>=0) {
                            try {
                                if(bi.size>0 && bi.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG==0) {
                                    assertTrue(muxed);val b=requireNotNull(codec.getOutputBuffer(index));b.position(bi.offset);b.limit(bi.offset+bi.size)
                                    muxer.writeSampleData(track,b,bi)
                                }
                                if(bi.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM!=0)eos=true
                            } finally { codec.releaseOutputBuffer(index,false) }
                        } else break
                    }
                }
                ColourRenderer(1024,128).use { renderer ->
                    repeat(36) { frame ->
                        renderer.import(texture);env.current(window);renderer.record()
                        assertTrue(EGLExt.eglPresentationTimeANDROID(env.display,window,frame*1_000_000_000L/30))
                        assertTrue(EGL14.eglSwapBuffers(env.display,window));drain()
                    }
                }
                codec.signalEndOfInputStream();val deadline=SystemClock.elapsedRealtime()+8000
                while(!eos && SystemClock.elapsedRealtime()<deadline)drain()
                assertTrue("HLG encoder EOS",eos);muxer.stop();muxed=false
                save("encoder.json",JSONObject().put("kind","colour-encoder").put("status","encoded")
                    .put("file",file.name).put("width",1024).put("height",128).put("rampLevels",1024)
                    .put("verification",RecordingVerifier.verify(context,Uri.fromFile(file),mode))
                    .put("encodedPixelsTested",false).put("hostPixelCheckRequired",true))
            } finally {
                if(texture!=0)GL.glDeleteTextures(1,intArrayOf(texture),0)
                env.current();env.destroy(window)
                if(started)runCatching { codec.stop() };codec.release();surface?.release()
                if(muxed)runCatching { muxer.stop() };muxer.release()
            }
        }
    }
}
