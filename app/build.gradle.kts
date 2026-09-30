plugins {
    id("com.android.application")
}

// Opt-in only. CI development builds remain unsigned for release; never fall back to a debug key.
val releaseSigningInputs = listOf("S23LOG_RELEASE_STORE_FILE", "S23LOG_RELEASE_STORE_PASSWORD",
    "S23LOG_RELEASE_KEY_ALIAS", "S23LOG_RELEASE_KEY_PASSWORD").associateWith {
    providers.environmentVariable(it).orNull?.takeIf(String::isNotBlank)
}
val hasReleaseSigning = releaseSigningInputs.values.all { it != null }
val requireSignedRelease = providers.gradleProperty("requireReleaseSigning").orNull?.let {
    require(it == "true" || it == "false") { "requireReleaseSigning must be true or false" }
    it == "true"
} ?: false
require(releaseSigningInputs.values.none { it != null } || hasReleaseSigning) {
    "Release signing is partially configured. Supply all four documented environment variables or none."
}
require(!requireSignedRelease || hasReleaseSigning) {
    "A signed release was required, but release-key configuration is absent. No debug-key fallback is allowed."
}

android {
    namespace = "com.s23log.probe"
    compileSdk = 36
    buildToolsVersion = "36.0.0"

    defaultConfig {
        applicationId = "com.s23log.probe"
        minSdk = 26
        targetSdk = 36
        versionCode = 9
        versionName = "0.7.0-raw-sequence"
        val revision = System.getenv("GITHUB_SHA") ?: providers.gradleProperty("sourceRevision").orNull ?: "local-unversioned"
        require(revision.matches(Regex("[a-zA-Z0-9-]+")))
        buildConfigField("String", "SOURCE_REVISION", "\"$revision\"")
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { buildConfig = true }
    if (hasReleaseSigning) signingConfigs {
        create("production") {
            storeFile = file(requireNotNull(releaseSigningInputs["S23LOG_RELEASE_STORE_FILE"]))
            require(storeFile?.isFile == true && storeFile?.canRead() == true) { "Configured release keystore is unavailable or unreadable" }
            storePassword = releaseSigningInputs["S23LOG_RELEASE_STORE_PASSWORD"]
            keyAlias = releaseSigningInputs["S23LOG_RELEASE_KEY_ALIAS"]
            keyPassword = releaseSigningInputs["S23LOG_RELEASE_KEY_PASSWORD"]
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            if (hasReleaseSigning) signingConfig = signingConfigs.getByName("production")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    lint {
        abortOnError = true
        checkReleaseBuilds = true
    }
    testOptions { unitTests.isReturnDefaultValues = false }
}

dependencies {
    implementation("androidx.core:core:1.15.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
