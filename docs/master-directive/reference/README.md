# Companion reference code

This is a host-testable contract laboratory accompanying the S23 Cinema Master Directive. It is not an Android application, a calibrated film renderer, or proof of physical S23 capture quality.

## Python

Requires Python 3.11 or newer; the reference uses only the standard library.

```sh
cd reference
python -m unittest -v test_reference.py
```

The delivered implementation has 53 passing behavioral tests. The retained red log records the initial 48-test unimplemented boundary. A second red run records five additional failing overflow and evidence-type tests; the final 53-test run passes. LogC3 coefficients are sourced from ARRI's published EI800 exposure-domain table. The grain sampler, toy density curve, temporal helper, evidence conjunction, and filesystem helper are deliberately limited reference components, not complete production subsystems.

## Kotlin/JVM

Requires a Kotlin compiler and compatible JDK. No Android SDK or third-party test framework is required for these portable contract checks.

```sh
kotlinc kotlin/Contracts.kt kotlin/ContractsTest.kt -include-runtime -d contracts.jar
java -jar contracts.jar
```

The delivered implementation has 32 passing named checks. Its lease abstraction assumes exclusive ownership of a borrowed value; idempotent concurrent close does not make arbitrary concurrent use-after-close safe. Its pool counts leases rather than bytes. Its signal descriptor and manual-readiness policy are intentionally smaller than the production contracts in the directive.

The initial Kotlin test harness was corrected to propagate worker errors and bound latch waits before the recorded complete red run. The final red run had zero passed and 32 failed checks; the implementation then passed all 32. No claim is made that every development attempt was successful.

## Integration

Port these contracts into the repository's existing test setup. Preserve the current package structure and pinned build unless a reviewed change is necessary. Android adapters, GPU backends, codecs, models, and physical-phone experiments need additional tests and are not supplied as a functioning app by this companion bundle.
