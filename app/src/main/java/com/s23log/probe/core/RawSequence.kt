package com.s23log.probe.core

import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.zip.CRC32

/** Ordinary RAW_SENSOR stream only. Native sensor bit depth is not inferred from 16-bit storage. */
data class RawSequencePlan(val width: Int, val height: Int, val fps: Int, val seconds: Int,
                           val storeFrames: Boolean, val poolSize: Int = 3) {
    init {
        require(width > 0 && height > 0 && width % 2 == 0 && height % 2 == 0)
        require(width.toLong() * height * 2 <= Int.MAX_VALUE)
        require(fps in listOf(24, 30) && seconds in 1..30 && poolSize in 2..4)
    }
    val frameBytes: Int get() = (width.toLong() * height * 2).toInt()
    val poolBytes: Long get() = if (storeFrames) frameBytes.toLong() * poolSize else 0
    val expectedPayloadBytes: Long get() = if (storeFrames) frameBytes.toLong() * fps * seconds else 0
    fun rejection(heapLimit: Long, availableStorage: Long): String? = when {
        poolBytes > minOf(192L * 1024 * 1024, heapLimit / 3) ->
            "RAW copy pool exceeds the bounded heap budget; choose a smaller advertised stream"
        availableStorage < expectedPayloadBytes + (if (storeFrames) frameBytes.toLong() * (poolSize + 2) else 0) + 64L * 1024 * 1024 ->
            "Insufficient storage for the requested uncompressed RAW sequence and reserve"
        else -> null
    }
}

/** Timestamp joiner owned by one acquisition thread. Every eviction is counted by the caller. */
class RawFrameMatcher<I, M>(private val capacity: Int,
                           private val discard: (I, String) -> Unit,
                           private val missingImage: (String) -> Unit,
                           private val matched: (Long, I, M) -> Unit) {
    private val images = linkedMapOf<Long, I>()
    private val metadata = linkedMapOf<Long, M>()
    init { require(capacity in 1..32) }
    fun image(timestamp: Long, image: I) {
        require(timestamp > 0)
        val result = metadata.remove(timestamp)
        if (result != null) { matched(timestamp, image, result); return }
        images.put(timestamp, image)?.let { discard(it, "duplicate_image") }
        while (images.size > capacity) discard(images.remove(images.keys.first())!!, "metadata_overflow")
    }
    fun result(timestamp: Long, result: M) {
        require(timestamp > 0)
        val image = images.remove(timestamp)
        if (image != null) { matched(timestamp, image, result); return }
        if (metadata.put(timestamp, result) != null) missingImage("duplicate_metadata")
        while (metadata.size > capacity) { metadata.remove(metadata.keys.first()); missingImage("image_overflow") }
    }
    fun clear() {
        val abandoned = images.values.toList(); val absent = metadata.size
        images.clear(); metadata.clear()
        abandoned.forEach { discard(it, "unmatched_at_stop") }
        repeat(absent) { missingImage("unmatched_at_stop") }
    }
}

/** Append-only, little-endian, CRC-protected records; no header rewrite or giant file-sized allocation. */
object RawSequenceFormat {
    private fun lengths(metadataSize: Int, payloadSize: Int): ByteArray = ByteBuffer.allocate(12)
        .order(ByteOrder.LITTLE_ENDIAN).putInt(metadataSize).putLong(payloadSize.toLong()).array()
    fun header(stream: OutputStream, json: ByteArray) {
        require(json.size in 1..1_048_576)
        stream.write("S23RAW01".toByteArray(Charsets.US_ASCII))
        stream.write(ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(json.size).array())
        stream.write(json)
    }
    fun frame(stream: OutputStream, metadata: ByteArray, pixels: ByteArray) {
        require(metadata.size in 1..1_048_576 && pixels.isNotEmpty() && pixels.size % 2 == 0)
        val size = lengths(metadata.size, pixels.size)
        val crc = CRC32().apply { update(size); update(metadata); update(pixels) }
        stream.write("FRM1".toByteArray(Charsets.US_ASCII)); stream.write(size)
        stream.write(metadata); stream.write(pixels)
        stream.write(ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(crc.value.toInt()).array())
    }
}
