[app]
title = 娲囨磭涓撶敤
package.name = YinYinApp
package.domain = com.yinyin
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0.0
requirements = python3,kivy==2.3.1,kivymd==1.2.0,openai
orientation = portrait
osx.package_name = YinYinApp
osx.bundle_name = 娲囨磭涓撶敤
presplash.color = #0f0f1a
icon.color = #e94560

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.api = 34
android.minapi = 21
android.sdk = 34
android.ndk = 27c
android.build_tools = 34.0.0
android.gradle_dependencies = 'androidx.appcompat:appcompat:1.6.1'
android.permissions = INTERNET
android.arch = arm64-v8a
android.accept_sdk_license = True
android.private_storage = True
android.wakelock = False
android.redirect_logs = True
android.enable_androidx = True

[app:ios]
ios.codesign.allowed = false
