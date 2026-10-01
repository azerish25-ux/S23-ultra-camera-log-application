package com.s23log.probe.core

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*

/** Row-major colour arithmetic, independent of Android, encoders and display transforms. */
object RawDevelopMath {
    val XYZ_TO_AWG3 = doubleArrayOf(1.789066, -.482534, -.200076, -.639849, 1.396400, .194432, -.041532, .082335, .878868)
    // Bradford adaptation, D50 (0.3457,0.3585) -> D65 (0.3127,0.3290).
    val D50_TO_D65 = doubleArrayOf(.955473421488, -.0230984549488, .0632592432006,
        -.0283697093344, 1.00999539808, .0210414411919, .0123140148645, -.0205076492989, 1.33036592624)
    val IDENTITY = doubleArrayOf(1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1.0)
    val BAYER = arrayOf("RGGB", "GRBG", "GBRG", "BGGR")
    fun logC3(x: Double): Double {
        require(x.isFinite())
        return if (x > .010591) .247190 * log10(5.555556*x+.052272)+.385537 else 5.367655*x+.092809
    }
    fun inverseLogC3(y: Double): Double {
        require(y.isFinite())
        return if (y > 5.367655*.010591+.092809) (10.0.pow((y-.385537)/.247190)-.052272)/5.555556 else (y-.092809)/5.367655
    }
    fun multiply(a: DoubleArray, b: DoubleArray): DoubleArray {
        require(a.size == 9 && b.size == 9 && a.all(Double::isFinite) && b.all(Double::isFinite))
        return DoubleArray(9) { i -> (0..2).sumOf { k -> a[i/3*3+k]*b[k*3+i%3] } }
    }
    fun apply(a: DoubleArray, x: DoubleArray): DoubleArray {
        require(a.size == 9 && x.size == 3)
        return DoubleArray(3) { r -> (0..2).sumOf { c -> a[r*3+c]*x[c] } }
    }
    fun diagonal(x: DoubleArray): DoubleArray { require(x.size == 3); return DoubleArray(9) { if(it/3 == it%3) x[it/3] else 0.0 } }
    fun inverse(m: DoubleArray): DoubleArray {
        require(m.size == 9 && m.all(Double::isFinite))
        val a=m[0]; val b=m[1]; val c=m[2]; val d=m[3]; val e=m[4]; val f=m[5]; val g=m[6]; val h=m[7]; val i=m[8]
        val det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
        require(det.isFinite() && abs(det)>1e-12) { "Singular colour matrix" }
        val result=doubleArrayOf(e*i-f*h,c*h-b*i,b*f-c*e,f*g-d*i,a*i-c*g,c*d-a*f,d*h-e*g,b*g-a*h,a*e-b*d).map { it/det }.toDoubleArray()
        fun norm(x: DoubleArray)=(0..2).maxOf { r -> (0..2).sumOf { cc -> abs(x[r*3+cc]) } }
        require(norm(m)*norm(result) <= 10000) { "Ill-conditioned colour matrix" }
        return result
    }
    /** Camera2 calibration is reference->actual. Forward is white-balanced reference->XYZ D50.
     * The returned matrix consumes white-balanced actual-camera RGB, NOT unbalanced samples.
     * One explicitly selected reference illuminant; no invented CCT or endpoint interpolation. */
    fun metadataMatrix(forward: DoubleArray, calibration: DoubleArray, neutral: DoubleArray): Pair<DoubleArray,DoubleArray> {
        require(neutral.size==3 && neutral.all { it.isFinite() && it>0 })
        val n=neutral.map { it/neutral[1] }.toDoubleArray()
        val inv=inverse(calibration); val reference=apply(inv,n)
        require(reference.all { it.isFinite() && it>0 }) { "Invalid reference-space neutral" }
        val toReference=multiply(diagonal(reference.map { 1/it }.toDoubleArray()), multiply(inv,diagonal(n)))
        val matrix=multiply(D50_TO_D65,multiply(forward,toReference))
        inverse(matrix)
        val white=apply(matrix,doubleArrayOf(1.0,1.0,1.0))
        val target=doubleArrayOf(.950455927,1.0,1.089057751)
        require((0..2).all { abs(white[it]/white[1]-target[it])<.035 }) { "Forward/calibration matrices do not map neutral to D65" }
        return matrix to n.map { 1/it }.toDoubleArray()
    }
    fun y(r:Double,g:Double,b:Double)=.2126*r+.7152*g+.0722*b
    fun cb(r:Double,g:Double,b:Double)=(b-y(r,g,b))/1.8556
    fun cr(r:Double,g:Double,b:Double)=(r-y(r,g,b))/1.5748
    fun lumaCode(y:Double)=(64+876*y).roundToInt().coerceIn(64,940)
    fun chromaCode(c:Double)=(512+896*c).roundToInt().coerceIn(64,960)
}

data class RawDevelopParameters(val cfa:Int, val crop:IntArray, val black:DoubleArray, val white:Double,
    val wb:DoubleArray, val cameraToXyz:DoubleArray, val sceneScale:Double, val divisor:Int=1) {
    init {
        require(cfa in 0..3 && crop.size==4 && crop.all { it>=0 && it%2==0 } && crop[2]>=4 && crop[3]>=4)
        require(black.size==4 && black.all { it.isFinite() && it>=0 && it<white } && white in 1.0..65535.0)
        require(wb.size==4 && wb.all { it.isFinite() && it>0 && it<=128 })
        require(sceneScale.isFinite() && sceneScale>0 && sceneScale<=1e6)
        RawDevelopMath.inverse(cameraToXyz)
        require(divisor in listOf(1,2,4) && crop[2]%(2*divisor)==0 && crop[3]%(2*divisor)==0)
    }
    val width:Int get()=crop[2]/divisor
    val height:Int get()=crop[3]/divisor
}

/** Implementations can supply a saved source or an owned live frame. No platform resources escape. */
interface RawRowSource { val width:Int; val height:Int; fun readRow(y:Int, into:ShortArray) }
interface LogRowSink { fun pair(y:Int, first:DoubleArray, second:DoubleArray) }
data class DevelopCounts(var sensorSaturated:Long=0,var below:Long=0,var above:Long=0)

/** CPU reference backend. Only four source rows and a few output rows are resident.
 * Box reduction happens in scene-linear AWG3 before Log encoding. This is NOT a realtime claim. */
class RawFrameDeveloper {
    fun develop(source:RawRowSource,p:RawDevelopParameters,allowClipping:Boolean=false,
                check:()->Unit={}, sink:LogRowSink):DevelopCounts {
        require(p.crop[0].toLong()+p.crop[2]<=source.width && p.crop[1].toLong()+p.crop[3]<=source.height)
        val w=p.crop[2]; val h=p.crop[3]; val pattern=RawDevelopMath.BAYER[p.cfa]
        val raw=ShortArray(source.width); val cache=Array(4) { FloatArray(w) }; val keys=IntArray(4) { -1 }
        val counted=BooleanArray(h); val counts=DevelopCounts()
        fun row(y:Int):FloatArray {
            val slot=y%4
            if(keys[slot]!=y) {
                check(); source.readRow(y+p.crop[1],raw)
                for(x in 0 until w) {
                    val v=raw[x+p.crop[0]].toInt() and 65535; val phase=(y%2)*2+x%2
                    // Match the offline reference's float32 normalization, without clamping shadows.
                    cache[slot][x]=((v.toFloat()-p.black[phase]).toFloat()*p.wb[phase]/(p.white-p.black[phase])).toFloat()
                    if(!counted[y] && v>=p.white) counts.sensorSaturated++
                }
                counted[y]=true; keys[slot]=y
            }
            return cache[slot]
        }
        fun reflect(x:Int,n:Int)=when { x<0 -> -x; x>=n -> 2*n-2-x; else -> x }
        val matrix=RawDevelopMath.multiply(RawDevelopMath.XYZ_TO_AWG3,p.cameraToXyz)
        val output=Array(2) { DoubleArray(p.width*3) }
        val camera=DoubleArray(3)
        for(oy in 0 until p.height) {
            check(); val out=output[oy%2]; out.fill(0.0)
            for(sy in oy*p.divisor until (oy+1)*p.divisor) {
                val rows=Array(3) { row(reflect(sy+it-1,h)) }
                for(sx in 0 until w) {
                    for(channel in 0..2) {
                        val name="RGB"[channel]
                        if(pattern[(sy%2)*2+sx%2]==name) camera[channel]=rows[1][sx].toDouble()
                        else {
                            var total=0.0; var weight=0
                            for(dy in -1..1) for(dx in -1..1) {
                                val x=reflect(sx+dx,w); val y=reflect(sy+dy,h)
                                if(pattern[(y%2)*2+x%2]==name) {
                                    val k=(if(dx==0)2 else 1)*(if(dy==0)2 else 1)
                                    total+=rows[dy+1][x]*k; weight+=k
                                }
                            }
                            require(weight>0); camera[channel]=total/weight
                        }
                    }
                    val at=(sx/p.divisor)*3
                    for(c in 0..2) out[at+c]+=(matrix[c*3]*camera[0]+matrix[c*3+1]*camera[1]+matrix[c*3+2]*camera[2])*p.sceneScale/(p.divisor*p.divisor)
                }
            }
            for(i in out.indices) {
                val v=RawDevelopMath.logC3(out[i])
                if(v<0) counts.below++; if(v>1) counts.above++
                require(allowClipping || v in 0.0..1.0) { "LogC3 exceeds storage range; source retained. Explicit clipping permission is required." }
                out[i]=v.coerceIn(0.0,1.0)
            }
            if(oy%2==1) sink.pair(oy-1,output[0],output[1])
        }
        return counts
    }
}

/** Explicit 10-bit plane views. Handles row padding, sliced buffers and semiplanar U/V overlap. */
class TenBitPlane(buffer:ByteBuffer,val width:Int,val height:Int,val rowStride:Int,val pixelStride:Int) {
    private val bytes=buffer.duplicate().order(ByteOrder.LITTLE_ENDIAN)
    private val base=bytes.position()
    init {
        require(width>0 && height>0 && pixelStride>=2 && pixelStride%2==0 && rowStride.toLong()>=(width-1L)*pixelStride+2)
        require(base.toLong()+(height-1L)*rowStride+(width-1L)*pixelStride+2<=bytes.limit()) { "Truncated P010 plane" }
    }
    fun get(x:Int,y:Int):Int { require(x in 0 until width && y in 0 until height); return (bytes.getShort(base+y*rowStride+x*pixelStride).toInt() and 65535) ushr 6 }
    fun put(x:Int,y:Int,code:Int) { require(x in 0 until width && y in 0 until height && code in 0..1023); bytes.putShort(base+y*rowStride+x*pixelStride,(code shl 6).toShort()) }
}
class P010Rows(val y:TenBitPlane,val u:TenBitPlane,val v:TenBitPlane):LogRowSink {
    init { require(y.width==u.width*2 && y.height==u.height*2 && u.width==v.width && u.height==v.height) }
    override fun pair(row:Int,first:DoubleArray,second:DoubleArray) {
        require(row%2==0 && first.size==y.width*3 && second.size==first.size)
        for(r in 0..1) {
            val rgb=if(r==0)first else second
            for(x in 0 until y.width) {
                val i=x*3; y.put(x,row+r,RawDevelopMath.lumaCode(RawDevelopMath.y(rgb[i],rgb[i+1],rgb[i+2])))
            }
        }
        for(x in 0 until u.width) {
            var cb=0.0; var cr=0.0
            for(r in 0..1) for(dx in 0..1) {
                val rgb=if(r==0)first else second; val i=(x*2+dx)*3
                cb+=RawDevelopMath.cb(rgb[i],rgb[i+1],rgb[i+2])*.25
                cr+=RawDevelopMath.cr(rgb[i],rgb[i+1],rgb[i+2])*.25
            }
            u.put(x,row/2,RawDevelopMath.chromaCode(cb)); v.put(x,row/2,RawDevelopMath.chromaCode(cr))
        }
    }
}
