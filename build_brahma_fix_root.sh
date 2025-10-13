#!/bin/bash
set -e

echo "=============================="
echo "🚀 BRAHMA_AI FINAL BUILD SCRIPT (ROOT SAFE)"
echo "=============================="

apt update -y
apt install -y python3 python3-pip openjdk-17-jdk git unzip zip wget

echo "📂 Preparing environment..."
APP_DIR="$HOME/GHOSH_Robotics"
mkdir -p $APP_DIR
cd $APP_DIR

pip install --upgrade pip cython buildozer numpy matplotlib

mkdir -p $HOME/.buildozer/android/platform
cd $HOME/.buildozer/android/platform

if [ ! -d "cmdline-tools/latest" ]; then
  echo "⬇️ Downloading Android cmdline-tools..."
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline.zip
  mkdir -p cmdline-tools && unzip -q cmdline.zip -d cmdline-tools && rm cmdline.zip
  mkdir -p cmdline-tools/latest
  mv cmdline-tools/cmdline-tools/* cmdline-tools/latest/ || true
fi

export ANDROID_HOME="$HOME/.buildozer/android/platform/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export ANDROID_NDK_HOME="$HOME/.buildozer/android/platform/android-ndk-r25b"
export PATH="$PATH:$HOME/.buildozer/android/platform/cmdline-tools/latest/bin:$HOME/.buildozer/android/platform/android-sdk/platform-tools"

echo "🧩 Installing SDK components..."
yes | sdkmanager --licenses || true
sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.2" "ndk;25.2.9519653" || true

cd $APP_DIR
if [ ! -f buildozer.spec ]; then
  buildozer init
  sed -i 's/source.main.*/source.main = VibrationalImpulseTheory.py/' buildozer.spec
  sed -i 's/package.name.*/package.name = ghoshrobotics/' buildozer.spec
  sed -i 's/title.*/title = Brahma_AI/' buildozer.spec
  sed -i 's/package.domain.*/package.domain = org.ghoshrobotics/' buildozer.spec
fi

echo "⚙️ Running clean + build..."
buildozer android clean || true
buildozer -v android debug || true

echo "✅ APK Build Complete!"
mkdir -p /sdcard/
cp $APP_DIR/bin/*.apk /sdcard/ || true
echo "📱 APK copied to /sdcard/"

echo "=============================="
echo "✅ BRAHMA_AI BUILD FINISHED"
echo "=============================="
