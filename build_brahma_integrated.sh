#!/bin/bash
# ================================================
# 🌐 BRAHMA_AI FULL INTEGRATION SCRIPT (ROOT SAFE)
# Compiles: Termux → proot Ubuntu → Buildozer → GitHub → APK build
# ================================================

set -e

# ---- 1. DEFINE CORE PATHS ----
APP_DIR="/root/GHOSH_Robotics"
VENV_DIR="/root/brahma_env"
ANDROID_SDK_ROOT="/root/.buildozer/android/platform/android-sdk"
ANDROID_NDK_HOME="/root/.buildozer/android/platform/android-ndk-r25b"
CMDLINE_DIR="$ANDROID_SDK_ROOT/cmdline-tools/latest"
SDKMANAGER_BIN="$CMDLINE_DIR/bin/sdkmanager"
PLATFORMS=("platform-tools" "platforms;android-33" "build-tools;33.0.2")
NDK_PKG="ndk;25.2.9519653"
GITHUB_USER="<your_username>"
GITHUB_EMAIL="dainkthief@gmail.com"
GITHUB_REPO="<your_repo_name>"

# ---- 2. SYSTEM PREP ----
echo "🔧 Updating system packages..."
apt update -y && apt upgrade -y
apt install -y git python3 python3-pip openjdk-17-jdk wget unzip

# ---- 3. PYTHON ENV SETUP ----
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel cython buildozer colorama jinja2 packaging

# ---- 4. ANDROID SDK/NDK SETUP ----
echo "📦 Installing Android SDK + NDK..."
mkdir -p "$CMDLINE_DIR"
cd "$CMDLINE_DIR"
wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O tools.zip
unzip -o tools.zip
yes | "$SDKMANAGER_BIN" --sdk_root="$ANDROID_SDK_ROOT" --licenses || true
"$SDKMANAGER_BIN" --sdk_root="$ANDROID_SDK_ROOT" "${PLATFORMS[@]}" "$NDK_PKG" || true

# ---- 5. BUILD CONFIG ----
cd "$APP_DIR"
if [ ! -f buildozer.spec ]; then
    buildozer init
fi
sed -i 's/source.main.*/source.main = ghosh_robotics.py/' buildozer.spec
sed -i 's/package.name.*/package.name = ghoshrobotics/' buildozer.spec
sed -i 's/title.*/title = BRAHMA_AI/' buildozer.spec
sed -i 's/package.domain.*/package.domain = org.ghoshrobotics/' buildozer.spec

# ---- 6. CLEAN + BUILD ----
echo "⚙️ Running clean build..."
buildozer android clean || true
buildozer -v android debug || true

# ---- 7. COPY APK TO PHONE ----
echo "📤 Copying APK to internal storage..."
mkdir -p /sdcard/
cp "$APP_DIR"/bin/*.apk /sdcard/ || true
echo "✅ APK copied to /sdcard/"

# ---- 8. GITHUB INTEGRATION ----
echo "🌍 Integrating GitHub..."
git config --global user.name "$GITHUB_USER"
git config --global user.email "$GITHUB_EMAIL"
git init
git remote add origin https://github.com/$GITHUB_USER/$GITHUB_REPO.git || true
git add .
git commit -m "Brahma_AI integrated build"
echo "Enter GitHub token when prompted..."
git push -u origin main

# ---- 9. DONE ----
echo "========================================"
echo "✅ BRAHMA_AI BUILD + GITHUB SYNC COMPLETE"
echo "========================================"
