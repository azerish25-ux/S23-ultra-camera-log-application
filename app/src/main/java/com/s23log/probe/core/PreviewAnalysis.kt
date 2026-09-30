package com.s23log.probe.core

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.sqrt

enum class PreviewAid { GRID, LEVEL, HISTOGRAM, WAVEFORM, ZEBRAS, FALSE_COLOUR, PEAKING }

data class PreviewAnalysis(val width: Int, val height: Int, val validPixels: Int, val meanCode: Double?,
    val histogram: IntArray, val waveform: IntArray, val zebras: IntArray, val falseColour: IntArray, val peaking: IntArray)

/** Bounded RGB8 display analysis. It does not measure sensor exposure, RAW or encoded HDR precision. */
object PreviewAnalyzer {
    const val ZEBRA_CODE = 243 // First integer RGB8 code at or above 95% of 255.
    fun analyze(pixels: IntArray, width: Int, height: Int): PreviewAnalysis {
        require(width in 1..320 && height in 1..180 && pixels.size == width * height)
        val histogram = IntArray(64); val waveform = IntArray(width * 64)
        val zebra = IntArray(pixels.size); val falseColour = IntArray(pixels.size); val peaking = IntArray(pixels.size)
        val luma = IntArray(pixels.size) { -1 }
        var count = 0; var sum = 0L
        for (i in pixels.indices) {
            val pixel = pixels[i]
            if ((pixel ushr 24) == 0) continue
            val y = (54 * ((pixel ushr 16) and 255) + 183 * ((pixel ushr 8) and 255) + 19 * (pixel and 255) + 128) shr 8
            luma[i] = y; count++; sum += y
            histogram[y shr 2]++
            waveform[(63 - (y shr 2)) * width + i % width]++
            if (y >= ZEBRA_CODE) zebra[i] = if (((i % width + i / width) / 4) % 2 == 0) 0xa0ffffff.toInt() else 0xa0202020.toInt()
            falseColour[i] = when (y) {
                in 0..15 -> 0x704433aa
                in 16..63 -> 0x702783c4
                in 64..127 -> 0x7027b888
                in 128..191 -> 0x70e5cf52
                in 192..242 -> 0x70f28b42
                else -> 0x70e34878
            }
        }
        for (y in 1 until height - 1) for (x in 1 until width - 1) {
            val i = y * width + x
            val left = luma[i - 1]; val right = luma[i + 1]
            val above = luma[i - width]; val below = luma[i + width]
            if (luma[i] >= 0 && minOf(left, right, above, below) >= 0 && abs(left - right) + abs(above - below) >= 64)
                peaking[i] = 0xc0ff7043.toInt()
        }
        return PreviewAnalysis(width, height, count, if (count == 0) null else sum.toDouble() / count,
            histogram, waveform, zebra, falseColour, peaking)
    }
}

object PreviewLevel {
    /** Rotation is the Android display quarter-turn, 0..3. Near-flat or unreliable gravity is unknown. */
    fun degrees(x: Float, y: Float, z: Float, rotation: Int): Float? {
        if (!x.isFinite() || !y.isFinite() || !z.isFinite() || rotation !in 0..3) return null
        val norm = sqrt(x * x + y * y + z * z)
        if (norm !in 7f..12f || sqrt(x * x + y * y) < 3f) return null
        val (sx, sy) = when (rotation) { 1 -> y to -x; 2 -> -x to -y; 3 -> -y to x; else -> x to y }
        var angle = Math.toDegrees(atan2(-sx.toDouble(), sy.toDouble())).toFloat()
        if (angle > 90) angle -= 180
        if (angle < -90) angle += 180
        return angle
    }
}
