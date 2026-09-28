package com.s23log.probe.core

/** Reads HEVC SPS bit depth from Android's Annex-B codec-specific data, not from UI labels. */
object HevcSps {
    data class Depth(val luma: Int, val chroma: Int)
    fun bitDepth(data: ByteArray): Depth? = runCatching {
        val starts = mutableListOf<Pair<Int, Int>>()
        var i = 0
        while (i + 3 < data.size) {
            val length = if (data[i] == 0.toByte() && data[i + 1] == 0.toByte()) {
                when {
                    data[i + 2] == 1.toByte() -> 3
                    data[i + 2] == 0.toByte() && data[i + 3] == 1.toByte() -> 4
                    else -> 0
                }
            } else 0
            if (length > 0) { starts += i to length; i += length } else i++
        }
        val n = starts.indices.firstOrNull {
            val p = starts[it].first + starts[it].second
            p < data.size && (data[p].toInt() and 0x7e) shr 1 == 33
        } ?: return null
        val start = starts[n].first + starts[n].second + 2
        val end = starts.getOrNull(n + 1)?.first ?: data.size
        val rbsp = ArrayList<Byte>()
        var zeros = 0
        for (p in start until end) {
            val value = data[p].toInt() and 255
            if (zeros >= 2 && value == 3) { zeros = 0; continue }
            rbsp += data[p]
            zeros = if (value == 0) zeros + 1 else 0
        }
        val bits = Bits(rbsp.toByteArray())
        bits.skip(4)
        val layers = bits.read(3)
        bits.skip(1)
        bits.skip(96) // general profile_tier_level
        val profile = BooleanArray(layers)
        val level = BooleanArray(layers)
        for (s in 0 until layers) { profile[s] = bits.read(1) == 1; level[s] = bits.read(1) == 1 }
        if (layers > 0) bits.skip((8 - layers) * 2)
        for (s in 0 until layers) { if (profile[s]) bits.skip(88); if (level[s]) bits.skip(8) }
        bits.ue() // sps_seq_parameter_set_id
        val chroma = bits.ue()
        require(chroma <= 3)
        if (chroma == 3) bits.skip(1)
        bits.ue(); bits.ue() // dimensions
        if (bits.read(1) == 1) repeat(4) { bits.ue() }
        val lumaDepth = bits.ue() + 8
        val chromaDepth = bits.ue() + 8
        require(lumaDepth in 8..16 && chromaDepth in 8..16)
        Depth(lumaDepth, chromaDepth)
    }.getOrNull()

    private class Bits(private val bytes: ByteArray) {
        private var position = 0
        fun read(count: Int): Int {
            require(count in 0..31 && position + count <= bytes.size * 8)
            var result = 0
            repeat(count) {
                result = (result shl 1) or ((bytes[position / 8].toInt() ushr (7 - position % 8)) and 1)
                position++
            }
            return result
        }
        fun skip(count: Int) { require(count >= 0 && position + count <= bytes.size * 8); position += count }
        fun ue(): Int {
            var zeros = 0
            while (read(1) == 0) { zeros++; require(zeros < 30) }
            return (1 shl zeros) - 1 + read(zeros)
        }
    }
}
