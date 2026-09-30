plugins {
    id("com.android.application")
}

android {
    namespace = "com.s23log.probe"
    compileSdk = 36
    buildToolsVersion = "36.0.0"

    defaultConfig {
        applicationId = "com.s23log.probe"
        minSdk = 26
        targetSdk = 36
        versionCode = 8
        versionName = "0.6.0-camera-controls"
        val revision = System.getenv("GITHUB_SHA") ?: providers.gradleProperty("sourceRevision").orNull ?: "local-unversioned"
        require(revision.matches(Regex("[a-zA-Z0-9-]+")))
        buildConfigField("String", "SOURCE_REVISION", "\"$revision\"")
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { buildConfig = true }
    buildTypes {
        release { isMinifyEnabled = false }
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
