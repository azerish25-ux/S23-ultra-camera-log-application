package com.s23log.probe.core

import java.util.Locale

/** Versioned mathematical reference assets. These are not LUTs for the app's HLG recordings. */
object ColourReferenceBundle {
    const val VERSION = "S23Log-reference-0.1"
    const val SIZE = 8192
    private fun number(value: Double) = String.format(Locale.US, "%.12f", value)
    fun cube(inverse: Boolean): String = buildString {
        appendLine("# REFERENCE ONLY. Not Samsung Log, camera calibration, or an HLG-file viewing LUT.")
        appendLine("TITLE \"$VERSION ${if (inverse) "reference-log-to-linear-BT2020" else "linear-BT2020-to-reference-log"}\"")
        appendLine("LUT_1D_SIZE $SIZE")
        appendLine("DOMAIN_MIN 0.0 0.0 0.0"); appendLine("DOMAIN_MAX 1.0 1.0 1.0")
        for (i in 0 until SIZE) {
            val input = i.toDouble() / (SIZE - 1)
            val value = number(if (inverse) ColourMath.referenceLogDecode(input) else ColourMath.referenceLogEncode(input))
            appendLine("$value $value $value")
        }
    }
    fun files(): Map<String, String> = linkedMapOf(
        "linear-bt2020-to-reference-log.cube" to cube(false),
        "reference-log-to-linear-bt2020.cube" to cube(true),
        "reference-vectors.csv" to buildString {
            appendLine("linear_bt2020_component,reference_log_component,inverse_component")
            for (i in 0..1024) {
                val x = i / 1024.0; val y = ColourMath.referenceLogEncode(x)
                appendLine("${number(x)},${number(y)},${number(ColourMath.referenceLogDecode(y))}")
            }
        },
        "README.txt" to """
            $VERSION — mathematical reference assets only

            The app DOES NOT record this custom curve. Current HLG files are HLG, not reference Log.
            Do not apply the inverse LUT directly to an HLG, SDR or proprietary Samsung Log clip.

            Forward input: independent normalized linear BT.2020 RGB components in [0,1].
            Forward output: project reference curve L=ln(1+63*x)/ln(64), retaining BT.2020 primaries.
            Inverse input: ONLY components encoded by this exact reference curve/version in [0,1].
            Inverse output: x=(exp(L*ln(64))-1)/63, normalized linear BT.2020 RGB.
            The assets perform no gamut conversion, white balance, display tone mapping, legal/full
            range conversion, camera calibration or highlight recovery. Out-of-domain preservation
            is not defined; many LUT consumers clamp it. Avoid implicit extra colour transforms.

            Each Iridas .cube contains 8192 1D RGB entries. Use linear interpolation for the tested
            approximation. The inverse output is linear data, not a finished display rendering.
            The CSV supplies analytic reference values independent of LUT interpolation.
            File SHA-256 identities and the generating app revision are in manifest.json.

            This is preparation for an explicit future editor workflow, not proof that an encoder,
            camera or editor supports a custom transfer. Never tag this curve as HLG or Samsung Log.
            A shipping path still needs measured input, explicit container/sidecar interpretation,
            editor validation, and actual-device image-quality tests.
        """.trimIndent() + "\n"
    )
}
