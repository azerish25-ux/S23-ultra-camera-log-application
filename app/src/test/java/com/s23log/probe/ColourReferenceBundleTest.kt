package com.s23log.probe

import com.s23log.probe.core.ColourMath
import com.s23log.probe.core.ColourReferenceBundle
import org.junit.Assert.*
import org.junit.Test
import java.util.Locale
import kotlin.math.abs

class ColourReferenceBundleTest {
    private fun samples(cube: String) = cube.lineSequence().filter { it.firstOrNull()?.isDigit() == true }.map { line ->
        val rgb = line.split(' ').map(String::toDouble)
        assertEquals(3, rgb.size); assertEquals(rgb[0], rgb[1], 0.0); assertEquals(rgb[1], rgb[2], 0.0)
        rgb[0]
    }.toList()
    private fun interpolate(values: List<Double>, x: Double): Double {
        val p = x * values.lastIndex; val lower = p.toInt().coerceAtMost(values.lastIndex - 1)
        return values[lower] + (values[lower + 1] - values[lower]) * (p - lower)
    }
    @Test fun bothLutsAreMonotonicAndHaveExactEndpointsAndExplicitDomains() {
        for (inverse in listOf(false, true)) {
            val cube = ColourReferenceBundle.cube(inverse)
            assertTrue(cube.contains("LUT_1D_SIZE 8192")); assertTrue(cube.contains("DOMAIN_MIN 0.0 0.0 0.0"))
            assertTrue(cube.contains("DOMAIN_MAX 1.0 1.0 1.0")); assertTrue(cube.contains("REFERENCE ONLY"))
            val values = samples(cube)
            assertEquals(8192, values.size); assertEquals(0.0, values.first(), 0.0); assertEquals(1.0, values.last(), 0.0)
            assertTrue(values.zipWithNext().all { (a,b) -> a <= b })
        }
    }
    @Test fun linearInterpolationIsBoundedAgainstTheAnalyticReference() {
        val forward = samples(ColourReferenceBundle.cube(false)); val inverse = samples(ColourReferenceBundle.cube(true))
        for (i in 0..10000) {
            val x = i / 10000.0
            assertTrue(abs(interpolate(forward, x) - ColourMath.referenceLogEncode(x)) < 1e-5)
            assertTrue(abs(interpolate(inverse, x) - ColourMath.referenceLogDecode(x)) < 2e-7)
            assertTrue(abs(interpolate(inverse, interpolate(forward, x)) - x) < 3e-7)
        }
    }
    @Test fun referenceFilesAreDeterministicAndLocaleIndependent() {
        val baseline = ColourReferenceBundle.files(); val old = Locale.getDefault()
        try { Locale.setDefault(Locale.FRANCE); assertEquals(baseline, ColourReferenceBundle.files()) }
        finally { Locale.setDefault(old) }
        assertEquals(4, baseline.size)
        assertTrue(requireNotNull(baseline["README.txt"]).contains("DOES NOT record this custom curve"))
        assertTrue(baseline.keys.none { it.contains('/') || it.contains("..") })
    }
    @Test fun csvVectorsContainAnalyticRoundTrips() {
        val csv = requireNotNull(ColourReferenceBundle.files()["reference-vectors.csv"])
        val rows = csv.lineSequence().drop(1).filter(String::isNotBlank).toList()
        assertEquals(1025, rows.size)
        rows.forEach { row -> val values = row.split(',').map(String::toDouble); assertEquals(values[0], values[2], 1e-11) }
    }
}
