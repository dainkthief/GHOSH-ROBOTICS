#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
echo
echo "== Step 1: Updating base system =="
pkg update -y && pkg upgrade -y

echo
echo "== Step 2: Installing build essentials =="
pkg install -y git wget unzip openjdk-17 gradle clang make python

echo
echo "== Step 3: Creating workspace =="
WORKDIR="$HOME/termux-build"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

if [ ! -d termux-app ]; then
  echo
  echo "== Step 4: Cloning official Termux source =="
  git clone https://github.com/termux/termux-app.git
else
  echo "termux-app already exists — skipping clone."
fi

cd termux-app

echo
echo "== Step 5: Checking Gradle wrapper =="
if [ -f ./gradlew ]; then
  chmod +x ./gradlew
  echo "Using local Gradle wrapper"
else
  echo "No gradlew found, will use system Gradle"
fi

echo
echo "== Step 6: Building debug APK =="
(./gradlew assembleDebug 2>/dev/null || gradle assembleDebug) || echo "Build failed — check dependencies"

echo
echo "== Step 7: Summary =="
echo "APK (if built):"
find app/build/outputs/apk -type f -name "*.apk" || echo "No APK found"
echo
echo "== Build complete. =="

