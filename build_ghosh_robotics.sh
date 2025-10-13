# ==========================================================
# GHOSH ROBOTICS — Smart Auto Builder (v3.0 Stable)
# Compatible with Ubuntu 24.04+ inside Termux
# Fixes: distutils removal, SDK caching, auto version
# ==========================================================

set -e
cd /root

# --- CONFIG ---
APP_NAME="ghoshrobotics"
MAIN_FILE="ghosh_robotics.py"
SDK_VERSION="33.0.2"
PLATFORM_VERSION="android-33"
VERSION_FILE=".ghosh_version"

# --- STEP 1: SYSTEM PREP ---
echo "[1/9] Updating base system..."
apt update -y
apt install -y python3-venv python3-pip python3-setuptools git zip unzip openjdk-17-jdk wget curl
pip install --upgrade setuptools wheel packaging

# --- STEP 2: VENV INIT ---
echo "[2/9] Creating virtual environment..."
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip

# --- STEP 3: DEPENDENCIES ---
echo "[3/9] Installing Python dependencies..."
pip install buildozer cython kivy

# --- STEP 4: SOURCE VALIDATION ---
echo "[4/9] Checking source..."
if [ ! -f "$MAIN_FILE" ]; then
  echo "[❌] Missing $MAIN_FILE in /root. Place your Python app here first."
  exit 1
fi

# --- STEP 5: VERSION CONTROL ---
if [ ! -f "$VERSION_FILE" ]; then
  echo "1.0" > "$VERSION_FILE"
fi
OLD_VER=$(cat "$VERSION_FILE")
NEW_VER=$(awk -F. -v OFS=. '{$NF++;print}' "$VERSION_FILE")
echo "$NEW_VER" > "$VERSION_FILE"

# --- STEP 6: BUILDOZER CONFIG ---
echo "[5/9] Preparing Buildozer configuration..."
if [ ! -f buildozer.spec ]; then
  buildozer init
  sed -i "s/source.main = main.py/source.main = $MAIN_FILE/" buildozer.spec
fi
sed -i "s/^version = .*/version = $NEW_VER/" buildozer.spec

# --- STEP 7: ANDROID SDK CONFIG ---
echo "[6/9] Setting up Android SDK..."
export ANDROID_HOME=$HOME/.buildozer/android/platform/android-sdk
mkdir -p $ANDROID_HOME
if [ ! -d "$ANDROID_HOME/build-tools/$SDK_VERSION" ]; then
  echo "[+] Downloading Android SDK components..."
  yes | buildozer android update || true
  yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --sdk_root=$ANDROID_HOME \
      "build-tools;$SDK_VERSION" "platforms;$PLATFORM_VERSION" "platform-tools" || true
else
  echo "[✔] SDK cached and ready."
fi

# --- STEP 8: BUILD APK ---
echo "[7/9] Building APK v$NEW_VER (may take 30–60 minutes first time)..."
buildozer -v android debug || { echo "[❌] Build failed. Check buildozer.log"; exit 1; }

# --- STEP 9: EXPORT APK ---
echo "[8/9] Copying APK to phone storage..."
cp /root/bin/*.apk /data/data/com.termux/files/home/storage/shared/ 2>/dev/null || true

echo "=========================================================="
echo "✅ BUILD COMPLETE — GHOSH ROBOTICS v$NEW_VER"
echo "APK saved to: Internal Storage (Files app)"
echo "Filename: ${APP_NAME}-${NEW_VER}-debug.apk"
echo "=========================================================="
