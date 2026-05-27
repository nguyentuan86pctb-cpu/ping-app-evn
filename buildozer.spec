[app]

# (str) Title of your application
title = EVN Telemetry Tool

# (str) Package name
package.name = evntelemetry

# (str) Package domain (needed for android packaging)
package.domain = org.evn

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# Cấu hình đầy đủ các thư viện requests và urllib3 phục vụ truyền dẫn dữ liệu lên Web API
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,requests,urllib3,certifi,charset-normalizer,idna

# (str) Supported orientations (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# =============================================================================
# Android specific
# =============================================================================

# (list) Permissions
# Cấp quyền kết nối mạng Internet để gửi đồng bộ dữ liệu (Bỏ dấu thăng # ở đầu)
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Android SDK directory to use
#android.sdk_path = 

# (int) Android NDK directory to use
#android.ndk_path = 

# (int) Android NDK API to use
android.ndk_api = 24
android.ndk = 25b

# (list) Android architectures to build for (arm64-v8a và armeabi-v7a là 2 cấu trúc phổ biến nhất chạy mượt trên mọi điện thoại)
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow service to be foreground
#android.foreground_service = False

# (bool) Enable Android auto backup
android.allow_backup = True

# (str) Presplash background color
android.presplash_color = #0F172A

# =============================================================================
# Buildozer section
# =============================================================================

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
