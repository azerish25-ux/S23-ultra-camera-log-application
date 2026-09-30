package com.s23log.probe

import com.s23log.probe.core.MediaIdentity
import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.InputStream

class MediaIdentityTest {
    @Test fun matchesPublishedSha256Vector() {
        val identity = MediaIdentity.read(ByteArrayInputStream("abc".toByteArray()))
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", identity.sha256)
        assertEquals(3L, identity.byteCount)
    }
    @Test fun handlesPartialReadsAcrossBufferBoundaries() {
        val bytes = ByteArray(150_001) { (it % 251).toByte() }
        val reference = MediaIdentity.read(ByteArrayInputStream(bytes))
        val chunked = object : ByteArrayInputStream(bytes) {
            override fun read(b: ByteArray, off: Int, len: Int) = super.read(b, off, minOf(len, 17))
        }
        assertEquals(reference, MediaIdentity.read(chunked))
    }
    @Test fun handlesZeroLengthBulkReadWithoutSpinning() {
        val input = object : InputStream() {
            var value = 0
            override fun read() = if (value++ == 0) 97 else -1
            override fun read(b: ByteArray, off: Int, len: Int) = 0
        }
        assertEquals(MediaIdentity.read(ByteArrayInputStream(byteArrayOf(97))), MediaIdentity.read(input))
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsEmptyContainer() {
        MediaIdentity.read(ByteArrayInputStream(byteArrayOf()))
    }
    @Test fun changedByteChangesIdentity() {
        assertNotEquals(MediaIdentity.read(ByteArrayInputStream(byteArrayOf(1, 2))), MediaIdentity.read(ByteArrayInputStream(byteArrayOf(1, 3))))
    }
    @Test(expected = java.io.InterruptedIOException::class) fun cancellationStopsBeforeReadingMoreBytes() {
        MediaIdentity.read(ByteArrayInputStream(byteArrayOf(1, 2))) { false }
    }
}
