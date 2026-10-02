package com.s23log.probe.core

import java.io.File

data class LivePublicationResult(val published: File?, val retained: File?, val error: String?)

/** One owner publishes a UUID-named file in the same private directory. A failed operation never
 * creates a published reference, takes over a previous export, or deletes retained footage. */
object LivePublication {
    fun publish(partial: File, destination: File,
                rename: (File, File) -> Boolean = { source, target -> source.renameTo(target) }): LivePublicationResult {
        return try {
            require(partial.isFile && partial.length() > 0) { "Verified source file is missing or empty" }
            require(partial.canonicalFile != destination.canonicalFile &&
                partial.parentFile?.canonicalFile == destination.parentFile?.canonicalFile) { "Publication must stay in its private directory" }
            require(!destination.exists()) { "Destination already exists; previous export retained" }
            require(rename(partial, destination)) { "Final naming failed; checked output remains under its partial name" }
            require(destination.isFile && destination.length() > 0 && !partial.exists()) { "Publication did not complete as requested" }
            LivePublicationResult(destination, null, null)
        } catch (e: Exception) {
            LivePublicationResult(null, partial.takeIf { it.isFile }, e.message ?: e.javaClass.simpleName)
        }
    }
}
