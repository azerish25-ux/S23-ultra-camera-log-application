import com.s23log.probe.core.LivePublication
import java.nio.file.Files
import java.io.File

/** Files are authored bytes, not decoded videos or phone capture evidence. */
fun main() {
    val directory = Files.createTempDirectory("s23-live-publication").toFile()
    var checks = 0
    fun expect(value: Boolean, why: String) { check(value) { why }; checks++ }
    try {
        val partial = File(directory, "take.partial.mp4").apply { writeText("irreplaceable source") }
        val destination = File(directory, "take.mp4")
        val failed = LivePublication.publish(partial, destination) { _, _ -> false }
        expect(failed.published == null, "A failed rename must never be reported as a published movie")
        expect(failed.retained == partial && partial.readText() == "irreplaceable source", "Keep partial bytes")
        expect(failed.error != null && !destination.exists(), "Explain failed publication without an invented target")
        destination.writeText("previous export")
        val collision = LivePublication.publish(partial, destination)
        expect(collision.published == null, "A pre-existing destination is not this attempt's movie")
        expect(destination.readText() == "previous export" && partial.isFile, "Never overwrite either source")
        val fresh = File(directory, "fresh.mp4")
        val good = LivePublication.publish(partial, fresh)
        expect(good.published == fresh && good.error == null, "Successful publication reports the real path")
        expect(fresh.readText() == "irreplaceable source" && !partial.exists(), "Published bytes are retained")
        val missing = LivePublication.publish(partial, File(directory, "missing.mp4"))
        expect(missing.published == null && missing.error != null, "Missing source cannot publish")
        println("$checks live publication assertions passed; synthetic file IO only")
    } finally { directory.deleteRecursively() }
}
