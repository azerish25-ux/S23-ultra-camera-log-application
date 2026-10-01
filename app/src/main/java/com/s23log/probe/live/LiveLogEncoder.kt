package com.s23log.probe.live

import android.annotation.TargetApi
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaFormat
import android.media.MediaMuxer
import android.opengl.EGL14
import android.os.Handler
import android.os.HandlerThread
import android.view.Surface
import com.s23log.probe.core.LiveP010
import com.s23log.probe.core.LogHevc
import com.s23log.probe.develop.LogP010Codec
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Independent codec callback/drain owner: a blocked GPU swap does not prevent output draining. */
@TargetApi(33)
class LiveLogEncoder(private val file:File,val route:Route,val width:Int,val height:Int,val fps:Int):AutoCloseable {
    enum class Input { P010_IMAGE, RGB10_SURFACE }
    data class Route(val codec:String,val input:Input) { val label:String get()="$codec / ${input.name}" }
    private val thread=HandlerThread("S23Log-live-encode").apply { start() }
    private val handler=Handler(thread.looper)
    private val inputs=ArrayBlockingQueue<Int>(64)
    private val fault=AtomicReference<Exception?>()
    private val eos=CountDownLatch(1)
    private val timestamps=mutableListOf<Long>()
    private var codec:MediaCodec?=null
    private var surface:Surface?=null
    private var gpuOwner:RawLogGpu?=null
    private var window=EGL14.EGL_NO_SURFACE
    private var muxer:MediaMuxer?=null
    private var track=-1
    private var muxing=false
    private var started=false
    @Volatile private var closing=false
    @Volatile private var received=0
    private var sentEos=false
    val encodedFrames:Int get()=received
    val submittedFrames:Int get()=synchronized(timestamps){timestamps.size}
    private lateinit var configuration:MediaFormat
    init {
        try {
            require(!file.exists()) { "Refusing to overwrite recording" }
            configuration=format(route,width,height,fps)
            muxer=MediaMuxer(file.absolutePath,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val c=MediaCodec.createByCodecName(route.codec);codec=c
            c.setCallback(object:MediaCodec.Callback(){
                override fun onInputBufferAvailable(codec:MediaCodec,index:Int) {
                    if(!closing && route.input==Input.P010_IMAGE && !inputs.offer(index))fault.compareAndSet(null,IllegalStateException("Codec input ownership queue overflow"))
                }
                override fun onOutputFormatChanged(codec:MediaCodec,format:MediaFormat) {
                    if(closing)return
                    try {
                        check(!muxing)
                        val csd=requireNotNull(format.getByteBuffer("csd-0")).duplicate()
                        val bytes=ByteArray(csd.remaining()).also(csd::get)
                        format.setByteBuffer("csd-0",ByteBuffer.wrap(LogHevc.rewrite(bytes)))
                        format.setInteger(MediaFormat.KEY_COLOR_STANDARD,0);format.setInteger(MediaFormat.KEY_COLOR_TRANSFER,0)
                        format.setInteger(MediaFormat.KEY_COLOR_RANGE,MediaFormat.COLOR_RANGE_LIMITED)
                        format.removeKey(MediaFormat.KEY_HDR_STATIC_INFO)
                        track=requireNotNull(muxer).addTrack(format);requireNotNull(muxer).start();muxing=true
                    } catch(e:Exception){fault.compareAndSet(null,e)}
                }
                override fun onOutputBufferAvailable(codec:MediaCodec,index:Int,info:MediaCodec.BufferInfo) {
                    try {
                        if(!closing && info.size>0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG==0 && fault.get()==null) {
                            check(muxing)
                            val expected=synchronized(timestamps){timestamps.getOrNull(received)}
                            require(expected!=null && kotlin.math.abs(expected-info.presentationTimeUs)<=2) { "Live encoder altered frame order or presentation timestamps" }
                            val buffer=requireNotNull(codec.getOutputBuffer(index)).duplicate().apply { position(info.offset);limit(info.offset+info.size) }
                            val bytes=ByteArray(buffer.remaining()).also(buffer::get)
                            val packet=LogHevc.rewrite(bytes,requireSps=false)
                            val sample=MediaCodec.BufferInfo().apply {set(0,packet.size,info.presentationTimeUs,info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM.inv())}
                            requireNotNull(muxer).writeSampleData(track,ByteBuffer.wrap(packet),sample);received++
                        }
                    } catch(e:Exception){fault.compareAndSet(null,e)}
                    finally {
                        runCatching {codec.releaseOutputBuffer(index,false)}.onFailure {fault.compareAndSet(null,IllegalStateException("Output release failed",it))}
                        if(info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM!=0)eos.countDown()
                    }
                }
                override fun onError(codec:MediaCodec,e:MediaCodec.CodecException){fault.compareAndSet(null,e);eos.countDown()}
            },handler)
            c.configure(configuration,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE)
            if(route.input==Input.RGB10_SURFACE)surface=c.createInputSurface()
            c.start();started=true
        } catch(e:Exception){close();throw e}
    }
    fun checkHealthy(){fault.get()?.let {throw IllegalStateException("Live codec failed: ${it.message}",it)}}
    private fun input(check:()->Unit):Int {
        val deadline=System.nanoTime()+5_000_000_000L
        while(System.nanoTime()<deadline){check();checkHealthy();inputs.poll(50,TimeUnit.MILLISECONDS)?.let{return it}}
        error("Encoder input stalled for five seconds; output remains retained")
    }
    fun submit(gpu:RawLogGpu,ptsUs:Long,check:()->Unit) {
        check(!sentEos && !closing);checkHealthy();check()
        synchronized(timestamps){require(ptsUs>=0 && (timestamps.isEmpty() || ptsUs>timestamps.last()));timestamps+=ptsUs}
        if(route.input==Input.RGB10_SURFACE) {
            if(window==EGL14.EGL_NO_SURFACE){gpuOwner=gpu;window=gpu.encoderWindow(requireNotNull(surface))}
            gpu.submit(window,ptsUs)
        } else {
            val packed=gpu.p010()
            val index=input(check);val c=requireNotNull(codec)
            val buffer=requireNotNull(c.getInputBuffer(index));val capacity=buffer.capacity()
            require(capacity.toLong() in width.toLong()*height*3..128L*1024*1024)
            buffer.clear();while(buffer.remaining()>=8)buffer.putLong(0);while(buffer.hasRemaining())buffer.put(0)
            requireNotNull(c.getInputImage(index)) { "Advertised P010 input does not expose Image planes" }.use {
                copyPacked(it,packed)
            }
            c.queueInputBuffer(index,0,capacity,ptsUs,0)
        }
        checkHealthy()
    }
    private fun copyPacked(image:android.media.Image,source:ByteBuffer) {
        // Reuse strict layout validation, then copy rows without per-pixel object/require overhead.
        LogP010Codec.planes(image,width,height)
        val crop=image.cropRect;val planes=image.planes
        val y=planes[0];val yDest=y.buffer.duplicate();val yBase=yDest.position()+crop.top*y.rowStride+crop.left*2
        val input=source.duplicate().order(java.nio.ByteOrder.LITTLE_ENDIAN)
        for(row in 0 until height){input.limit(row*width*2+width*2);input.position(row*width*2);yDest.position(yBase+row*y.rowStride);yDest.put(input)}
        val uvBase=width*height*2
        if(planes.size==2){
            val uv=planes[1];val dest=uv.buffer.duplicate();val base=dest.position()+crop.top/2*uv.rowStride+crop.left/2*4
            for(row in 0 until height/2){input.limit(uvBase+(row+1)*width*2);input.position(uvBase+row*width*2);dest.position(base+row*uv.rowStride);dest.put(input)}
        }else{
            input.limit(source.limit())
            for(channel in 0..1){val plane=planes[channel+1];val dest=plane.buffer.duplicate().order(java.nio.ByteOrder.LITTLE_ENDIAN)
                val base=dest.position()+crop.top/2*plane.rowStride+crop.left/2*4
                for(row in 0 until height/2)for(x in 0 until width/2)dest.putShort(base+row*plane.rowStride+x*4,input.getShort(uvBase+row*width*2+x*4+channel*2))
            }
        }
    }
    fun finish():JSONObject {
        checkHealthy();check(!sentEos);sentEos=true
        val c=requireNotNull(codec)
        if(route.input==Input.RGB10_SURFACE)c.signalEndOfInputStream()
        else {
            val index=input({})
            val pts=synchronized(timestamps){(timestamps.lastOrNull() ?: 0)+1_000_000L/fps}
            c.queueInputBuffer(index,0,0,pts,MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        }
        val deadline=System.nanoTime()+10_000_000_000L
        while(!eos.await(50,TimeUnit.MILLISECONDS)){checkHealthy();require(System.nanoTime()<deadline){"Live encoder EOS timeout; partial recording retained"}}
        checkHealthy();require(received==submittedFrames && received>=2) { "Recorded $received / $submittedFrames frames; not a verified movie" }
        val stopped=CountDownLatch(1)
        check(handler.post {try {if(muxing){requireNotNull(muxer).stop();muxing=false}}catch(e:Exception){fault.compareAndSet(null,e)}finally{stopped.countDown()}})
        require(stopped.await(3,TimeUnit.SECONDS)){"Muxer finalization timed out"};checkHealthy()
        return JSONObject().put("codec",route.codec).put("input",route.input.name).put("encodedFrames",received)
            .put("bitrateTarget",configuration.getInteger(MediaFormat.KEY_BIT_RATE)).put("hlgTransferUsed",false)
            .put("metadataReauthored",true).put("pictureNalsUnchangedByMetadataRewrite",true)
            .put("timestampMapping","sensor_delta_ns_divided_by_1000").put("audio","none")
    }
    override fun close() {
        if(closing)return;closing=true
        gpuOwner?.let {runCatching{it.environment.current();it.environment.destroy(window)}};window=EGL14.EGL_NO_SURFACE
        if(started)runCatching{codec?.stop()};runCatching{codec?.release()};runCatching{surface?.release()}
        val done=CountDownLatch(1)
        if(handler.post {try {if(muxing)runCatching{muxer?.stop()};runCatching{muxer?.release()};muxer=null}finally{done.countDown()}})done.await(3,TimeUnit.SECONDS)
        thread.quitSafely()
    }
    companion object {
        private const val MIME="video/hevc"
        fun inventory(encoder:Boolean):List<MediaCodecInfo> = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos
            .filter {it.isEncoder==encoder && !it.isAlias && MIME in it.supportedTypes}
            .sortedWith(compareBy<MediaCodecInfo>{!it.isHardwareAccelerated}.thenBy{it.name})
        fun format(route:Route,width:Int,height:Int,fps:Int):MediaFormat {
            require(width%2==0 && height%2==0 && width>0 && height>0 && fps in listOf(24,30))
            val caps=inventory(true).first{it.name==route.codec}.getCapabilitiesForType(MIME)
            require(caps.profileLevels.any{it.profile==MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10}){"No HEVC Main10 profile"}
            val color=if(route.input==Input.P010_IMAGE)MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010 else MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface
            require(color in caps.colorFormats){"Requested input interface is not advertised"}
            val video=requireNotNull(caps.videoCapabilities);require(video.areSizeAndRateSupported(width,height,fps.toDouble())){"Size/rate rejected"}
            return MediaFormat.createVideoFormat(MIME,width,height).apply {
                setInteger(MediaFormat.KEY_COLOR_FORMAT,color);setInteger(MediaFormat.KEY_PROFILE,MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10)
                setInteger(MediaFormat.KEY_FRAME_RATE,fps);setInteger(MediaFormat.KEY_BIT_RATE,(width.toLong()*height*fps*2).coerceIn(video.bitrateRange.lower.toLong(),video.bitrateRange.upper.toLong()).toInt())
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL,1);setInteger(MediaFormat.KEY_MAX_B_FRAMES,0)
                // Surface RGB->YUV must be BT709-coefficient representation, NOT an HLG/PQ conversion.
                setInteger(MediaFormat.KEY_COLOR_STANDARD,if(route.input==Input.RGB10_SURFACE)MediaFormat.COLOR_STANDARD_BT709 else 0)
                setInteger(MediaFormat.KEY_COLOR_TRANSFER,0);setInteger(MediaFormat.KEY_COLOR_RANGE,MediaFormat.COLOR_RANGE_LIMITED)
            }
        }
    }
}
