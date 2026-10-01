package com.s23log.probe.develop

import android.annotation.TargetApi
import android.graphics.ImageFormat
import android.media.Image
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import com.s23log.probe.core.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.roundToInt

/** Explicit P010 byte-buffer backend only. No HLG surface, implicit RGB conversion, or 8-bit fallback. */
@TargetApi(33)
object LogP010Codec {
    data class Choice(val name:String,val qualification:JSONObject)
    private const val MIME="video/hevc"
    private const val TIMEOUT_NS=15_000_000_000L
    private fun codecs(encoder:Boolean)=MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos
        .filter { it.isEncoder==encoder && !it.isAlias && MIME in it.supportedTypes }
        .sortedWith(compareBy<MediaCodecInfo> { !it.isHardwareAccelerated }.thenBy { it.name })
    private fun format(name:String,width:Int,height:Int,fps:Int):MediaFormat {
        val info=codecs(true).first { it.name==name }; val caps=info.getCapabilitiesForType(MIME)
        require(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010 in caps.colorFormats) { "No advertised P010 input" }
        require(caps.profileLevels.any { it.profile==MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10 }) { "No HEVC Main10 profile" }
        val video=requireNotNull(caps.videoCapabilities)
        require(video.areSizeAndRateSupported(width,height,fps.toDouble())) { "Encoder rejects the selected dimensions/rate" }
        val bitrate=(width.toLong()*height*fps*2).coerceIn(video.bitrateRange.lower.toLong(),video.bitrateRange.upper.toLong()).toInt()
        return MediaFormat.createVideoFormat(MIME,width,height).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT,MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010)
            setInteger(MediaFormat.KEY_PROFILE,MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10)
            setInteger(MediaFormat.KEY_FRAME_RATE,fps); setInteger(MediaFormat.KEY_BIT_RATE,bitrate)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL,1); setInteger(MediaFormat.KEY_MAX_B_FRAMES,0)
            setInteger(MediaFormat.KEY_COLOR_STANDARD,0); setInteger(MediaFormat.KEY_COLOR_TRANSFER,0)
            setInteger(MediaFormat.KEY_COLOR_RANGE,MediaFormat.COLOR_RANGE_LIMITED)
        }
    }
    fun candidates(width:Int,height:Int,fps:Int):List<String> = codecs(true).mapNotNull { info ->
        runCatching { format(info.name,width,height,fps); info.name }.getOrNull()
    }.take(8)

    /** Image planes carry their real strides; no guessed byte-buffer or vendor pixel layout. */
    fun planes(image:Image,width:Int,height:Int):P010Rows {
        require(image.format==ImageFormat.YCBCR_P010) { "Codec returned ${image.format}, not explicit 10-bit P010" }
        val crop=image.cropRect
        require(crop.width()==width && crop.height()==height && crop.left%2==0 && crop.top%2==0) { "Codec crop does not match output" }
        val p=image.planes; require(p.size==2 || p.size==3) { "Unknown P010 plane arrangement" }
        fun plane(index:Int,w:Int,h:Int,left:Int,top:Int,extra:Int=0):TenBitPlane {
            val source=p[index]; val bytes=source.buffer.duplicate().order(ByteOrder.LITTLE_ENDIAN)
            val offset=bytes.position().toLong()+top.toLong()*source.rowStride+left.toLong()*source.pixelStride+extra
            require(offset>=0 && offset<bytes.limit()); bytes.position(offset.toInt())
            return TenBitPlane(bytes,w,h,source.rowStride,source.pixelStride)
        }
        require(p[0].pixelStride==2 && p[1].pixelStride==4 && (p.size==2 || p[2].pixelStride==4)) { "Unknown P010 pixel stride" }
        return P010Rows(plane(0,width,height,crop.left,crop.top),
            plane(1,width/2,height/2,crop.left/2,crop.top/2),
            if(p.size==3)plane(2,width/2,height/2,crop.left/2,crop.top/2)else plane(1,width/2,height/2,crop.left/2,crop.top/2,2))
    }
    fun encode(file:File,name:String,width:Int,height:Int,fps:Int,count:Int,check:()->Unit,
               fill:(Int,P010Rows)->Unit):JSONObject {
        require(!file.exists() && count>=2 && width%2==0 && height%2==0)
        val config=format(name,width,height,fps)
        var codec:MediaCodec?=null; var muxer:MediaMuxer?=null; var muxing=false; var track=-1
        var started=false; var input=0; var output=0; var ended=false; var lastProgress=System.nanoTime(); var lastPts=-1L
        try {
            val c=MediaCodec.createByCodecName(name); codec=c; c.configure(config,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE); c.start(); started=true
            val m=MediaMuxer(file.absolutePath,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4); muxer=m
            val info=MediaCodec.BufferInfo()
            while(!ended) {
                check()
                if(input<=count) {
                    val index=c.dequeueInputBuffer(0)
                    if(index>=0) {
                        if(input==count)c.queueInputBuffer(index,0,0,count*1_000_000L/fps,MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                        else {
                            // Cache the capacity before getInputImage invalidates the ByteBuffer view.
                            val buffer=requireNotNull(c.getInputBuffer(index)); val size=buffer.capacity()
                            require(size in width*height*3..256*1024*1024) { "Unexpected encoder input buffer capacity" }
                            while(buffer.remaining()>=8)buffer.putLong(0); while(buffer.hasRemaining())buffer.put(0)
                            val image=requireNotNull(c.getInputImage(index)) { "Advertised P010 codec has no accessible input Image" }
                            image.use { fill(input,planes(it,width,height)) }
                            c.queueInputBuffer(index,0,size,input*1_000_000L/fps,0)
                        }
                        input++; lastProgress=System.nanoTime()
                    }
                }
                val index=c.dequeueOutputBuffer(info,10_000)
                if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    require(!muxing); val actual=c.outputFormat
                    val csd=requireNotNull(actual.getByteBuffer("csd-0")).duplicate()
                    val bytes=ByteArray(csd.remaining()).also(csd::get)
                    actual.setByteBuffer("csd-0",ByteBuffer.wrap(LogHevc.rewrite(bytes)))
                    actual.setInteger(MediaFormat.KEY_COLOR_STANDARD,0); actual.setInteger(MediaFormat.KEY_COLOR_TRANSFER,0)
                    actual.setInteger(MediaFormat.KEY_COLOR_RANGE,MediaFormat.COLOR_RANGE_LIMITED)
                    actual.removeKey(MediaFormat.KEY_HDR_STATIC_INFO)
                    track=m.addTrack(actual); m.start(); muxing=true; lastProgress=System.nanoTime()
                } else if(index>=0) {
                    try {
                        if(info.size>0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG==0) {
                            require(muxing && info.presentationTimeUs>lastPts) { "Missing track or nonmonotonic output" }
                            lastPts=info.presentationTimeUs
                            val data=requireNotNull(c.getOutputBuffer(index)).duplicate().apply { position(info.offset); limit(info.offset+info.size) }
                            val packet=ByteArray(data.remaining()).also(data::get)
                            // Handle any in-band parameter sets as well as csd-0. Picture NAL units are unchanged.
                            val authored=LogHevc.rewrite(packet,requireSps=false)
                            val sample=MediaCodec.BufferInfo().apply { set(0,authored.size,info.presentationTimeUs,info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM.inv()) }
                            m.writeSampleData(track,ByteBuffer.wrap(authored),sample); output++
                        }
                        if(info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM!=0)ended=true
                        lastProgress=System.nanoTime()
                    } finally { c.releaseOutputBuffer(index,false) }
                }
                require(System.nanoTime()-lastProgress<TIMEOUT_NS) { "P010 encoder stalled; partial output retained" }
            }
            require(input==count+1 && output==count) { "Encoder frame count differs from source" }
            m.stop(); muxing=false
            return JSONObject().put("name",name).put("input","P010_Image_with_verified_strides")
                .put("bitrateTarget",config.getInteger(MediaFormat.KEY_BIT_RATE)).put("frames",output)
                .put("vuiReauthored",true).put("pictureNalsReencodedForMetadata",false).put("hlgInputUsed",false)
        } finally {
            if(muxing)runCatching { muxer?.stop() }; runCatching { muxer?.release() }
            if(started)runCatching { codec?.stop() }; runCatching { codec?.release() }
        }
    }

    /** Fully decode every frame through a separate P010 decoder; a Bitmap is never precision evidence. */
    fun verify(file:File,width:Int,height:Int,fps:Int,count:Int,check:()->Unit,
               expectedPtsUs:List<Long>?=null,consume:(Int,P010Rows)->Unit):JSONObject {
        require(expectedPtsUs==null || (expectedPtsUs.size==count && expectedPtsUs.zipWithNext().all { (a,b) -> b>a }))
        val extractor=MediaExtractor(); var decoder:MediaCodec?=null; var started=false
        try {
            extractor.setDataSource(file.absolutePath); require(extractor.trackCount==1)
            val track=extractor.getTrackFormat(0)
            require(track.getString(MediaFormat.KEY_MIME)==MIME && track.getInteger(MediaFormat.KEY_WIDTH)==width && track.getInteger(MediaFormat.KEY_HEIGHT)==height)
            val csd=requireNotNull(track.getByteBuffer("csd-0")).duplicate(); val bytes=ByteArray(csd.remaining()).also(csd::get)
            val signal=LogHevc.signal(bytes); require(signal.isLogContract) { "Stored HEVC signal contract is incorrect" }
            extractor.selectTrack(0)
            track.setInteger(MediaFormat.KEY_COLOR_FORMAT,MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010)
            val failures=mutableListOf<String>()
            for(info in codecs(false)) {
                var candidate:MediaCodec?=null
                try {
                    if(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010 !in info.getCapabilitiesForType(MIME).colorFormats)continue
                    candidate=MediaCodec.createByCodecName(info.name); candidate.configure(track,null,null,0); candidate.start()
                    decoder=candidate; started=true; break
                } catch(e:Exception) { failures+="${info.name}: ${e.message}"; runCatching { candidate?.release() } }
            }
            val c=requireNotNull(decoder) { "No accessible 10-bit P010 decoder: ${failures.joinToString()}" }
            var inputEnded=false; var outputEnded=false; var decoded=0; var last=System.nanoTime()
            val info=MediaCodec.BufferInfo()
            while(!outputEnded) {
                check()
                if(!inputEnded) {
                    val index=c.dequeueInputBuffer(0)
                    if(index>=0) {
                        val buffer=requireNotNull(c.getInputBuffer(index)).apply { clear() }
                        val size=extractor.readSampleData(buffer,0)
                        if(size<0) { c.queueInputBuffer(index,0,0,0,MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputEnded=true }
                        else { c.queueInputBuffer(index,0,size,extractor.sampleTime,0); extractor.advance() }
                        last=System.nanoTime()
                    }
                }
                val index=c.dequeueOutputBuffer(info,10_000)
                if(index>=0) {
                    try {
                        if(info.size>0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG==0) {
                            require(decoded<count && abs(info.presentationTimeUs-(expectedPtsUs?.getOrNull(decoded) ?: (decoded*1_000_000L/fps)))<=2) { "Decoded frame count/order/timestamps differ from input" }
                            val image=requireNotNull(c.getOutputImage(index)) { "Decoder did not expose an Image for 10-bit verification" }
                            image.use { consume(decoded,planes(it,width,height)) }; decoded++
                        }
                        if(info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM!=0)outputEnded=true
                        last=System.nanoTime()
                    } finally { c.releaseOutputBuffer(index,false) }
                } else if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED)last=System.nanoTime()
                require(System.nanoTime()-last<TIMEOUT_NS) { "P010 decode timed out" }
            }
            require(decoded==count) { "Decoded fewer frames than supplied" }
            return JSONObject().put("decoder",c.name).put("decodedFrames",decoded).put("fullDecodeVerified",true)
                .put("width",width).put("height",height).put("mime",MIME).put("lumaBitDepth",signal.lumaBits).put("chromaBitDepth",signal.chromaBits)
                .put("colorPrimariesCode",signal.primaries).put("transferCharacteristicsCode",signal.transfer).put("matrixCoefficientsCode",signal.matrix)
                .put("colorRange",MediaFormat.COLOR_RANGE_LIMITED).put("colorTransfer",0)
                .put("measuredFps",if(expectedPtsUs!=null && count>1) (count-1)*1e6/(expectedPtsUs.last()-expectedPtsUs.first()) else fps.toDouble())
                .put("cadenceStatus",if(expectedPtsUs==null)"within_tolerance" else "original_pts_verified_not_cadence_certification")
                .put("timestampContract",if(expectedPtsUs==null)"CFR" else "relative_sensor_timestamps")
        } finally { if(started)runCatching { decoder?.stop() }; runCatching { decoder?.release() }; extractor.release() }
    }
    /** The positive AND deliberately 8-bit-degraded control use the same encoder and decoder.
     * Passing this is a codec route qualification, not sensor bit-depth or dynamic-range proof. */
    fun qualify(cache:File,width:Int,height:Int,fps:Int,check:()->Unit,progress:(String)->Unit):Choice {
        val failures=JSONArray()
        for(name in candidates(width,height,fps)) {
            check(); progress("Checking 10-bit route: $name")
            try {
                format(name,1024,128,fps)
                fun probe(degraded:Boolean):JSONObject {
                    val file=File(cache,"logc3-probe-${java.util.UUID.randomUUID()}.mp4")
                    try {
                        encode(file,name,1024,128,fps,4,check) { frame,p ->
                            for(y in 0 until 128) { check(); for(x in 0 until 1024) {
                                var v=64+(x+frame)%877
                                if(degraded)v=((v/4.0).roundToInt()*4).coerceIn(64,940)
                                p.y.put(x,y,v)
                            } }
                            for(y in 0 until 64) for(x in 0 until 512) { p.u.put(x,y,512); p.v.put(x,y,512) }
                        }
                        var maxMean=0.0; var maxError=0.0; var leastLevels=1024
                        val result=verify(file,1024,128,fps,4,check) { frame,p ->
                            val values=DoubleArray(877) { x -> (16 until 112).sumOf { y -> p.y.get(x,y).toDouble() }/96 }
                            val error=values.indices.map { abs(values[it]-(64+(it+frame)%877)) }
                            maxMean=maxOf(maxMean,error.average()); maxError=maxOf(maxError,error.max())
                            leastLevels=minOf(leastLevels,values.map { it.roundToInt() }.toSet().size)
                        }
                        return result.put("meanCodeError",maxMean).put("maximumCodeError",maxError).put("distinctRampLevels",leastLevels)
                            .put("passed",maxMean<=.75 && maxError<=2.0 && leastLevels>=600)
                    } finally { file.delete() }
                }
                val positive=probe(false); require(positive.getBoolean("passed")) { "10-bit ramp was not preserved: $positive" }
                val negative=probe(true); require(!negative.getBoolean("passed")) { "Precision check incorrectly accepted the deliberately degraded control" }
                return Choice(name,JSONObject().put("status","qualified").put("positive",positive).put("eightBitNegative",negative)
                    .put("probeWidth",1024).put("probeHeight",128).put("actualOutputAlsoFullyCompared",true).put("rejectedRoutes",failures)
                    .put("physicalCameraPrecisionMeasured",false))
            } catch(e:Exception) { check(); failures.put(JSONObject().put("codec",name).put("reason",e.message ?: e.javaClass.simpleName)) }
        }
        error("No P010 route passed encode/decode precision checks. Source retained; no 8-bit/HLG substitution. $failures")
    }
}

/** Full-frame code-value comparison against the RAW developer, after defined 4:2:0 subsampling. */
class LogFrameComparison(private val actual:P010Rows):LogRowSink {
    private var yError=0.0; private var cError=0.0; private var yn=0L; private var cn=0L; private var maximum=0
    override fun pair(y:Int,first:DoubleArray,second:DoubleArray) {
        for(r in 0..1) {
            val rgb=if(r==0)first else second
            for(x in 0 until actual.y.width) {
                val i=x*3; val expected=RawDevelopMath.lumaCode(RawDevelopMath.y(rgb[i],rgb[i+1],rgb[i+2]))
                val e=abs(actual.y.get(x,y+r)-expected); yError+=e; yn++; maximum=maxOf(maximum,e)
            }
        }
        for(x in 0 until actual.u.width) {
            var u=0.0; var v=0.0
            for(r in 0..1)for(dx in 0..1){val rgb=if(r==0)first else second;val i=(x*2+dx)*3
                u+=RawDevelopMath.cb(rgb[i],rgb[i+1],rgb[i+2])*.25;v+=RawDevelopMath.cr(rgb[i],rgb[i+1],rgb[i+2])*.25}
            val a=abs(actual.u.get(x,y/2)-RawDevelopMath.chromaCode(u)); val b=abs(actual.v.get(x,y/2)-RawDevelopMath.chromaCode(v))
            cError+=a+b;cn+=2;maximum=maxOf(maximum,a,b)
        }
    }
    fun result():JSONObject {
        require(yn==actual.y.width.toLong()*actual.y.height && cn==yn/2) { "Incomplete pixel comparison" }
        val y=yError/yn;val c=cError/cn
        require(y<=4.0 && c<=4.0 && maximum<=64) { "Decoded pixels differ from the Log reference (Y $y, chroma $c, peak $maximum codes)" }
        return JSONObject().put("meanLumaCodeError",y).put("meanChromaCodeError",c).put("maximumCodeError",maximum)
    }
}
