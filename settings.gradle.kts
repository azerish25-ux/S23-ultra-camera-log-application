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
        providers.gradleProperty("offlineMavenRepo").orNull?.let { mirror ->
            maven { url = uri(mirror) }
        }
        google()
        mavenCentral()
    }
}

rootProject.name = "S23Log"
include(":app")
