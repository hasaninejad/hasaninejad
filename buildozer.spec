[app]
title = HASANINEJAD
package.name = hasaninejad
package.domain = ir.hasaninejad
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,ttf,db,csv
version = 0.1.1

# arabic-reshaper + python-bidi render Persian text; Kivy itself does no shaping.
requirements = python3,kivy,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0

# API 34 builds reliably with the current python-for-android toolchain.
# Raise to 35 only when you publish to Google Play (targetSdk 35 is required there).
android.api = 34
android.minapi = 23

# arm64-v8a covers modern phones and halves the build time.
# Add ", armeabi-v7a" when you need to support older 32-bit devices.
android.archs = arm64-v8a

# WRITE/READ_EXTERNAL_STORAGE are no-ops from Android 13 on; the app keeps its
# database and CSV in its private directory, so nothing else is required.
android.permissions = POST_NOTIFICATIONS

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
# Accept the Android SDK licence automatically so CI and Colab never block.
android.accept_sdk_license = True
