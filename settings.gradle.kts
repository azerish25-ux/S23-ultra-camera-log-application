pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        // The ChatGPT Linux environment keeps a local mirror for fully offline builds.
        // Normal developer machines ignore it and resolve from Google/Maven Central.
        val offlineMirror = file("/opt/android-offline-maven")
        if (offlineMirror.isDirectory) {
            maven { url = uri(offlineMirror) }
        }
        google()
        mavenCentral()
    }
}

rootProject.name = "S23Log"
include(":app")
