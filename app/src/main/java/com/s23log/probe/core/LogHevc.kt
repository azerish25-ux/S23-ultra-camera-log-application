package com.s23log.probe.core

import java.io.ByteArrayOutputStream

/** Re-author HEVC VUI metadata for known, numerically supplied LogC3/AWG3 P010 pixels.
 * No picture data, timing, dimensions, profile or bit-depth fields are changed. The codec may
 * default to Rec.709 tags even for custom samples. We do not feed or claim an HLG signal.
 * Primaries=2, transfer=2 (unspecified), matrix=1 (709 YCbCr coefficients), limited range.
 */
object LogHevc {
    data class Signal(val lumaBits:Int,val chromaBits:Int,val primaries:Int?,val transfer:Int?,val matrix:Int?,val fullRange:Boolean?) {
        val isLogContract:Boolean get()=lumaBits==10 && chromaBits==10 && primaries==2 && transfer==2 && matrix==1 && fullRange==false
    }
    private class Bits(val bits:MutableList<Int>,var at:Int=0) {
        fun read(n:Int):Int { require(n in 0..30 && at+n<=bits.size); var v=0; repeat(n) { v=v*2+bits[at++] }; return v }
        fun skip(n:Int) { require(n>=0 && at+n<=bits.size); at+=n }
        fun ue():Int { var n=0; while(read(1)==0) { n++; require(n<=20) }; return (1 shl n)-1+read(n) }
    }
    private data class Located(val b:Bits,val vuiAt:Int,val signalAt:Int?,val signalEnd:Int?,val signal:Signal)
    private fun locate(nal:ByteArray):Located {
        require(nal.size>=4 && (nal[0].toInt() ushr 1 and 63)==33)
        val raw=ByteArrayOutputStream(); var zeros=0
        for(i in 2 until nal.size) {
            val v=nal[i].toInt() and 255
            if(zeros>=2 && v==3) { zeros=0; continue }
            raw.write(v); zeros=if(v==0)zeros+1 else 0
        }
        val values=raw.toByteArray().flatMap { byte -> (7 downTo 0).map { (byte.toInt() ushr it) and 1 } }.toMutableList()
        val b=Bits(values); b.skip(4); val layers=b.read(3); b.skip(1); b.skip(96)
        val profiles=BooleanArray(layers); val levels=BooleanArray(layers)
        repeat(layers) { profiles[it]=b.read(1)==1; levels[it]=b.read(1)==1 }
        if(layers>0)b.skip((8-layers)*2)
        repeat(layers) { if(profiles[it])b.skip(88); if(levels[it])b.skip(8) }
        b.ue(); val chroma=b.ue(); require(chroma<=3); if(chroma==3)b.skip(1)
        b.ue(); b.ue(); if(b.read(1)==1)repeat(4){b.ue()}
        val luma=b.ue()+8; val depth=b.ue()+8; require(luma in 8..16 && depth in 8..16)
        val poc=b.ue()+4; require(poc in 4..16)
        val ordering=b.read(1)==1
        for(i in (if(ordering)0 else layers)..layers)repeat(3){b.ue()}
        repeat(6){b.ue()}
        if(b.read(1)==1 && b.read(1)==1) {
            for(sizeId in 0..3) for(matrixId in 0..5 step (if(sizeId==3)3 else 1)) {
                if(b.read(1)==0)b.ue() else {
                    if(sizeId>1)b.ue()
                    repeat(minOf(64,1 shl (4+(sizeId shl 1)))) { b.ue() }
                }
            }
        }
        b.skip(2); if(b.read(1)==1) { b.skip(8); b.ue(); b.ue(); b.skip(1) }
        val shortSets=b.ue(); require(shortSets<=64); val deltas=IntArray(shortSets)
        repeat(shortSets) { idx ->
            if(idx>0 && b.read(1)==1) {
                b.skip(1); b.ue(); var count=0
                repeat(deltas[idx-1]+1) { val used=b.read(1)==1; val use=used || b.read(1)==1; if(use)count++ }
                deltas[idx]=count
            } else {
                val neg=b.ue(); val pos=b.ue(); require(neg+pos<=64)
                repeat(neg+pos) { b.ue(); b.skip(1) }; deltas[idx]=neg+pos
            }
        }
        if(b.read(1)==1) { val count=b.ue(); require(count<=32); repeat(count){b.skip(poc+1)} }
        b.skip(2); val vuiAt=b.at
        if(b.read(1)==0)return Located(b,vuiAt,null,null,Signal(luma,depth,null,null,null,null))
        if(b.read(1)==1) { if(b.read(8)==255)b.skip(32) }
        if(b.read(1)==1)b.skip(1)
        val signalAt=b.at
        var full:Boolean?=null; var prim:Int?=null; var transfer:Int?=null; var matrix:Int?=null
        if(b.read(1)==1) {
            b.skip(3); full=b.read(1)==1
            if(b.read(1)==1) { prim=b.read(8); transfer=b.read(8); matrix=b.read(8) }
        }
        return Located(b,vuiAt,signalAt,b.at,Signal(luma,depth,prim,transfer,matrix,full))
    }
    private fun code(v:Int,n:Int)=(n-1 downTo 0).map { (v ushr it) and 1 }
    private val signalBits= listOf(1)+code(5,3)+listOf(0,1)+code(2,8)+code(2,8)+code(1,8)
    private fun rewriteSps(nal:ByteArray):ByteArray {
        val loc=locate(nal); val old=loc.b.bits; val stop=old.indexOfLast { it==1 }; require(stop>loc.vuiAt)
        val rewritten=if(loc.signalAt!=null) old.take(loc.signalAt)+signalBits+old.subList(requireNotNull(loc.signalEnd),stop+1)
            else old.take(loc.vuiAt)+listOf(1,0,0)+signalBits+List(7){0}+old.subList(loc.vuiAt+1,stop+1)
        // Seven following flags: chroma location, neutral chroma, field sequence, frame info,
        // default display window, timing info, and bitstream restriction.
        val padded=rewritten+List((8-rewritten.size%8)%8){0}
        val rbsp=ByteArray(padded.size/8) { i -> (0..7).fold(0) { a,j -> a*2+padded[i*8+j] }.toByte() }
        val output=ByteArrayOutputStream(); output.write(nal,0,2); var zeros=0
        for(byte in rbsp) { val v=byte.toInt() and 255; if(zeros>=2 && v<=3) { output.write(3); zeros=0 }; output.write(v); zeros=if(v==0)zeros+1 else 0 }
        return output.toByteArray().also { require(locate(it).signal.isLogContract) { "HEVC VUI re-authoring failed" } }
    }
    private fun split(data:ByteArray):List<ByteArray> {
        val starts=mutableListOf<Pair<Int,Int>>(); var i=0
        while(i+3<=data.size) {
            val n=if(data[i]==0.toByte() && data[i+1]==0.toByte()) when {
                data[i+2]==1.toByte()->3
                i+4<=data.size && data[i+2]==0.toByte() && data[i+3]==1.toByte()->4
                else->0
            } else 0
            if(n>0){starts+=i to n;i+=n}else i++
        }
        require(starts.isNotEmpty() && starts.first().first<=1) { "Expected Annex-B HEVC data" }
        return starts.mapIndexed { index,(at,n)->data.copyOfRange(at+n,starts.getOrNull(index+1)?.first ?: data.size) }
    }
    fun signal(csd:ByteArray):Signal=locate(split(csd).single { it.isNotEmpty() && (it[0].toInt() ushr 1 and 63)==33 }).signal
    fun rewrite(csd:ByteArray,requireSps:Boolean=true):ByteArray {
        require(csd.size<=32*1024*1024)
        val nals=split(csd); var count=0; val out=ByteArrayOutputStream()
        for(nal in nals) {
            require(nal.size>=2); out.write(byteArrayOf(0,0,0,1))
            if((nal[0].toInt() ushr 1 and 63)==33){out.write(rewriteSps(nal));count++}else out.write(nal)
        }
        require(!requireSps || count==1) { "Exactly one SPS is required" }
        return out.toByteArray()
    }
}
