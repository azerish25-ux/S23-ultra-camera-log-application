package com.s23log.probe

import com.s23log.probe.core.HevcSps
import org.junit.Assert.*
import org.junit.Test

class HevcSpsTest {
    private fun sps(depth: Int, layers: Int = 0, crop: Boolean = false, chroma: Int = 1): ByteArray {
        val bits = StringBuilder()
        fun put(n: Int, width: Int) { bits.append(n.toString(2).padStart(width, '0').takeLast(width)) }
        fun ue(n: Int) { val code = (n + 1).toString(2); bits.append("0".repeat(code.length - 1)); bits.append(code) }
        put(0, 4); put(layers, 3); put(1, 1); bits.append("0".repeat(96))
        repeat(layers) { put(0, 1); put(0, 1) }
        if (layers > 0) bits.append("0".repeat((8 - layers) * 2))
        ue(0); ue(chroma); if (chroma == 3) put(0, 1)
        ue(1920); ue(1080); put(if (crop) 1 else 0, 1); if (crop) repeat(4) { ue(0) }
        ue(depth - 8); ue(depth - 8); bits.append('1')
        while (bits.length % 8 != 0) bits.append('0')
        val rbsp = bits.toString().chunked(8).map { it.toInt(2).toByte() }
        val escaped = mutableListOf<Byte>()
        var zeros = 0
        rbsp.forEach { b ->
            if (zeros >= 2 && (b.toInt() and 255) <= 3) { escaped += 3.toByte(); zeros = 0 }
            escaped += b; zeros = if (b == 0.toByte()) zeros + 1 else 0
        }
        return byteArrayOf(0, 0, 0, 1, 0x42, 1) + escaped.toByteArray()
    }
    @Test fun parsesEightBitNotMainTen() { assertEquals(HevcSps.Depth(8, 8), HevcSps.bitDepth(sps(8))) }
    @Test fun parsesTenBitSps() { assertEquals(HevcSps.Depth(10, 10), HevcSps.bitDepth(sps(10))) }
    @Test fun parsesSubLayers() { assertEquals(HevcSps.Depth(10, 10), HevcSps.bitDepth(sps(10, layers = 3))) }
    @Test fun parsesConformanceWindowAndChroma() { assertEquals(HevcSps.Depth(10, 10), HevcSps.bitDepth(sps(10, crop = true, chroma = 3))) }
    @Test fun findsSpsAmongOtherNalUnits() { assertEquals(HevcSps.Depth(10, 10), HevcSps.bitDepth(byteArrayOf(0, 0, 1, 0x40, 1, 8, 9) + sps(10) + byteArrayOf(0, 0, 1, 0x44, 1, 1))) }
    @Test fun truncatedDataReturnsUnknownNotTenBit() { assertNull(HevcSps.bitDepth(sps(10).copyOf(12))) }
    @Test fun garbageAndMissingSpsAreRejected() { assertNull(HevcSps.bitDepth(byteArrayOf(1, 2, 3))); assertNull(HevcSps.bitDepth(byteArrayOf(0, 0, 1, 0x40, 1))) }
    @Test fun twelveBitDoesNotBecomeTenBit() { assertEquals(HevcSps.Depth(12, 12), HevcSps.bitDepth(sps(12))) }
    @Test fun parsesRealLibx265EightAndTenBitStreams() {
        for (depth in listOf(8, 10)) {
            val hex = requireNotNull(javaClass.classLoader!!.getResourceAsStream("hevc$depth.annexb.hex")).bufferedReader().use { it.readText() }.filterNot { it.isWhitespace() }
            val bytes = hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
            assertEquals(HevcSps.Depth(depth, depth), HevcSps.bitDepth(bytes))
        }
    }
}
