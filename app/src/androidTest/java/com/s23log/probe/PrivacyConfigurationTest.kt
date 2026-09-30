package com.s23log.probe

import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.xmlpull.v1.XmlPullParser

@RunWith(AndroidJUnit4::class)
class PrivacyConfigurationTest {
    @Test fun packagedAppDeniesBackupAndHasNoNetworkOrLocationPermission() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals(0, context.applicationInfo.flags and ApplicationInfo.FLAG_ALLOW_BACKUP)
        val permissions = context.packageManager.getPackageInfo(context.packageName, PackageManager.GET_PERMISSIONS).requestedPermissions.orEmpty().toSet()
        for (permission in listOf("android.permission.INTERNET", "android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION", "android.permission.MANAGE_EXTERNAL_STORAGE"))
            assertFalse("Unexpected permission: $permission", permission in permissions)
    }
    @Test fun allAppDataDomainsAreExplicitlyExcludedFromCloudAndDeviceTransfer() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val expected = setOf("root", "file", "database", "sharedpref", "external", "device_root", "device_file", "device_database", "device_sharedpref")
        val sections = linkedMapOf<String, MutableSet<String>>()
        var current: String? = null
        context.resources.getXml(R.xml.data_extraction_rules).use { xml ->
            while (xml.eventType != XmlPullParser.END_DOCUMENT) {
                if (xml.eventType == XmlPullParser.START_TAG) {
                    when (xml.name) {
                        "cloud-backup", "device-transfer" -> { current = xml.name; sections[xml.name] = linkedSetOf() }
                        "include" -> fail("Backup rules must not include app data")
                        "exclude" -> {
                            assertEquals(".", xml.getAttributeValue(null, "path"))
                            requireNotNull(sections[current]).add(xml.getAttributeValue(null, "domain"))
                        }
                    }
                } else if (xml.eventType == XmlPullParser.END_TAG && xml.name == current) current = null
                xml.next()
            }
        }
        assertEquals(setOf("cloud-backup", "device-transfer"), sections.keys)
        sections.values.forEach { assertEquals(expected, it) }
    }
}
