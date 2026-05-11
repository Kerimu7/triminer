[app]
title = TriMiner
package.name = triminer
package.domain = org.triminer
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = miners/*.py,backend/*.py
version = 1.0.0

requirements = python3,kivy==2.3.0,Cython==0.29.33,requests,argon2-cffi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WAKE_LOCK,FOREGROUND_SERVICE
android.api = 33
android.minapi = 26
android.ndk = 25b
android.ndk_api = 26
android.accept_sdk_license = True
android.archs = arm64-v8a
android.wakelock = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
