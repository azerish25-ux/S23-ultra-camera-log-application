package com.s23log.probe.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.util.zip.CRC32
import kotlin.math.abs

/** Strict JSON fields: do not accept strings, booleans, infinities or fractional dimensions. */
object RawJson {
    fun number(j:JSONObject,key:String):Double=(j.get(key) as? Number)?.toDouble()?.also { require(it.isFinite()) { "Nonfinite $key" } }
        ?: error("Numeric $key required")
    fun integer(j:JSONObject,key:String):Long {
        val value=j.get(key); require(value is Int || value is Long) { "Integer $key required" }; return (value as Number).toLong()
    }
    fun array(j:JSONObject,key:String,count:Int):DoubleArray {
        val a=j.getJSONArray(key); require(a.length()==count) { "$key requires $count entries" }
        return DoubleArray(count) { i -> (a.get(i) as? Number)?.toDouble()?.also { require(it.isFinite()) } ?: error("Numeric $key required") }
    }
    fun ints(j:JSONObject,key:String,count:Int):IntArray {
        val a=j.getJSONArray(key); require(a.length()==count)
        return IntArray(count) { i -> val v=a.get(i); require(v is Int || v is Long); (v as Number).toLong().also { require(it in 0..Int.MAX_VALUE) }.toInt() }
    }
    fun matrix(j:JSONObject,key:String):DoubleArray {
        val a=j.getJSONArray(key); require(a.length()==3)
        return DoubleArray(9) { i -> val r=a.getJSONArray(i/3); require(r.length()==3)
            (r.get(i%3) as? Number)?.toDouble()?.also { require(it.isFinite()) } ?: error("Numeric $key required") }.also { RawDevelopMath.inverse(it) }
    }
    fun matrixJson(a:DoubleArray)=JSONArray((0..2).map { r -> (0..2).map { c -> a[r*3+c] } })
    fun parse(bytes:ByteArray):JSONObject {
        require(bytes.size in 1..1_048_576)
        val text=Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString()
        return JSONObject(text)
    }
    fun hash(file:File,check:()->Unit={}):String {
        val digest=MessageDigest.getInstance("SHA-256"); val buf=ByteArray(64*1024)
        file.inputStream().use { stream -> while(true) { check(); val n=stream.read(buf); if(n<0)break; digest.update(buf,0,n) } }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}

data class RawFrameRef(val metadata:JSONObject,val offset:Long,val size:Int)
data class RawSourceIndex(val file:File,val header:JSONObject,val frames:List<RawFrameRef>,val bytes:Long,val modified:Long) {
    val width:Int get()=header.getInt("width")
    val height:Int get()=header.getInt("height")
    val cfa:Int get()=header.getInt("cfa")
    val fps:Int get()=header.getInt("fpsRequested")
    fun unchanged() { require(file.length()==bytes && file.lastModified()==modified) { "RAW source changed; stop capture before development" } }
    fun binding()=JSONObject().put("fingerprint",header.getJSONObject("device").getString("fingerprint"))
        .put("logicalCamera",header.getString("logicalCamera")).put("physicalCamera",header.opt("physicalCamera") ?: JSONObject.NULL)
        .put("width",width).put("height",height).put("cfa",cfa)
    fun timing():JSONObject {
        require(frames.size>=2) { "At least two complete RAW frames are required" }
        val times=frames.map { it.metadata.getLong("sensorTimestampNs") }
        val span=times.last()-times.first(); require(span>0)
        val maxDeviation=times.zipWithNext().maxOf { (a,b)-> abs((b-a)*fps/1e9-1) }
        val measured=(times.size-1)*1e9/span
        require(maxDeviation<=.03 && abs(measured/fps-1)<=.03) { "Source is outside the 3% cadence tolerance. Android export does not silently retime missing frames." }
        return JSONObject().put("outputFps",fps).put("sourceMeasuredFps",measured).put("sourceMaximumIntervalDeviation",maxDeviation)
            .put("sourceTimestampsNs",JSONArray(times)).put("cfrMapping",true).put("framesDuplicatedOrInterpolated",0)
    }
    fun rows(frame:RawFrameRef)=FileRows(this,frame)
    class FileRows(private val index:RawSourceIndex,private val frame:RawFrameRef):RawRowSource,AutoCloseable {
        private val input=RandomAccessFile(index.file,"r")
        private val row=ByteArray(index.width*2)
        override val width:Int get()=index.width
        override val height:Int get()=index.height
        override fun readRow(y:Int,into:ShortArray) {
            require(y in 0 until height && into.size>=width)
            input.seek(frame.offset+y.toLong()*row.size); input.readFully(row)
            for(x in 0 until width) into[x]=((row[x*2].toInt() and 255) or ((row[x*2+1].toInt() and 255) shl 8)).toShort()
        }
        override fun close()=input.close()
    }
}

/** Existing S23RAW01 format. CRC checked in bounded blocks; no implicit tail recovery in the app. */
object RawSourceReader {
    fun scan(file:File,check:()->Unit={}):RawSourceIndex {
        require(file.isFile); val length=file.length(); val modified=file.lastModified(); val frames=mutableListOf<RawFrameRef>()
        RandomAccessFile(file,"r").use { input ->
            fun bytes(n:Int)=ByteArray(n).also { input.readFully(it) }
            fun uint()=Integer.reverseBytes(input.readInt()).toLong() and 0xffffffffL
            require(String(bytes(8),Charsets.US_ASCII)=="S23RAW01") { "Not an S23RAW01 source" }
            val headerLength=uint(); require(headerLength in 1..1_048_576)
            val header=RawJson.parse(bytes(headerLength.toInt()))
            require(RawJson.integer(header,"schemaVersion")==1L && header.getString("kind")=="continuous-raw" && header.getString("source")=="RAW_SENSOR")
            val width=RawJson.integer(header,"width"); val height=RawJson.integer(header,"height")
            require(width in 4..65536 && height in 4..65536 && width%2==0L && height%2==0L && width*height<=64_000_000)
            require(header.getString("sampleEncoding")=="uint16le" && RawJson.integer(header,"rowBytes")==2*width)
            require(RawJson.integer(header,"cfa") in 0..3 && RawJson.integer(header,"fpsRequested") in listOf(24L,30L))
            require(header.getJSONObject("device").getString("fingerprint").isNotBlank())
            require(header.getString("logicalCamera").isNotBlank())
            val scratch=ByteArray(64*1024); var lastTimestamp=-1L
            while(input.filePointer<length) {
                check(); require(length-input.filePointer>=16) { "Incomplete final RAW record; source retained" }
                require(String(bytes(4),Charsets.US_ASCII)=="FRM1") { "Unknown RAW record marker" }
                val sizes=bytes(12); val buffer=ByteBuffer.wrap(sizes).order(ByteOrder.LITTLE_ENDIAN)
                val metaSize=buffer.int; val payload=buffer.long
                require(metaSize in 1..65536 && payload==width*height*2) { "RAW record dimensions or metadata length are invalid" }
                require(length-input.filePointer>=metaSize+payload+4) { "Incomplete RAW frame; use explicit desktop tail recovery" }
                val metaBytes=bytes(metaSize); val meta=RawJson.parse(metaBytes); val at=input.filePointer
                val crc=CRC32().apply { update(sizes); update(metaBytes) }; var left=payload
                while(left>0) { check(); val n=minOf(left,scratch.size.toLong()).toInt(); input.readFully(scratch,0,n); crc.update(scratch,0,n); left-=n }
                require(crc.value==uint()) { "RAW checksum mismatch at $at" }
                val timestamp=RawJson.integer(meta,"sensorTimestampNs")
                require(timestamp>0 && timestamp>lastTimestamp) { "RAW timestamps repeat or regress" }; lastTimestamp=timestamp
                levels(meta)
                require(RawJson.integer(meta,"iso")>0 && RawJson.integer(meta,"exposureNs")>0)
                frames+=RawFrameRef(meta,at,payload.toInt()); require(frames.size<=4096) { "Android source index limit exceeded" }
            }
            return RawSourceIndex(file,header,frames.toList(),length,modified).also { it.unchanged(); require(frames.isNotEmpty()) { "No complete RAW frames" } }
        }
    }
    fun levels(meta:JSONObject):Pair<DoubleArray,Double> {
        val black=RawJson.array(meta,"blackLevels",4); val white=RawJson.number(meta,"whiteLevel")
        require(white in 1.0..65535.0 && black.all { it>=0 && it<white }); return black to white
    }
}
