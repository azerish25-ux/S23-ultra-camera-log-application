package com.s23log.probe.core

import java.io.InputStream
import java.io.InterruptedIOException
import java.security.MessageDigest

/** Streaming identity of the finalized container bytes, independent of its eventual URI/name. */
data class MediaIdentity(val sha256: String, val byteCount: Long) {
    fun describe(): Map<String, Any> = mapOf("algorithm" to "SHA-256", "sha256" to sha256, "byteCount" to byteCount)

    companion object {
        fun read(input: InputStream): MediaIdentity = read(input) { true }

        fun read(input: InputStream, continueReading: () -> Boolean): MediaIdentity {
            val digest = MessageDigest.getInstance("SHA-256")
            val buffer = ByteArray(64 * 1024)
            var size = 0L
            while (true) {
                if (!continueReading()) throw InterruptedIOException("Media identity read cancelled")
                val count = input.read(buffer)
                if (count < 0) break
                if (count == 0) {
                    val value = input.read()
                    if (value < 0) break
                    digest.update(value.toByte()); size = Math.addExact(size, 1)
                } else {
                    digest.update(buffer, 0, count); size = Math.addExact(size, count.toLong())
                }
            }
            require(size > 0) { "Cannot identify an empty media container" }
            return MediaIdentity(digest.digest().joinToString("") { "%02x".format(it) }, size)
        }
    }
}
