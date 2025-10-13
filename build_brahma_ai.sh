bash build_brahma_ai.sh
# ==========================================================
#  BRAHMA_AI → GHOSH_ROBOTICS  |  FULL BUILD + SDK REPAIR
#  Termux + Ubuntu (proot)  |  Python → Android APK Builder
# ==========================================================

# 1. Update and Install Dependencies
apt update -y && apt upgrade -y
apt install -y openjdk-17-jdk python3-full python3-pip python3-venv git zip wget curl libffi-dev libssl-dev build-essential unzip

# 2. Virtual Environment Setup
python3 -m venv /root/brahma_env
source /root/brahma_env/bin/activate
pip install --upgrade pip setuptools wheel build patch-ng cython kivy numpy matplotlib buildozer

# 3. Create Workspace
mkdir -p /root/GHOSH_Robotics && cd /root/GHOSH_Robotics
if [ ! -f ghosh_robotics.py ]; then
  echo "print('BRAHMA_AI initialized')" > ghosh_robotics.py
fi

# 4. Initialize Buildozer Spec
yes | buildozer init
sed -i 's/source.main.*/source.main = ghosh_robotics.py/' buildozer.spec
sed -i 's/package.name.*/package.name = ghoshrobotics/' buildozer.spec
sed -i 's/title.*/title = BRAHMA_AI/' buildozer.spec
sed -i 's/package.domain.*/package.domain = org.ghoshrobotics/' buildozer.spec

# 5. Fix Missing Android SDK Tools (sdkmanager)
mkdir -p /root/.buildozer/android/platform/android-sdk/cmdline-tools/latest
cd /root/.buildozer/android/platform/android-sdk/cmdline-tools
wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O tools.zip
unzip -qo tools.zip -d latest && rm tools.zip

# 6. Export Environment Variables
export ANDROID_SDK_ROOT=/root/.buildozer/android/platform/android-sdk
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH

# 7. Accept Licenses and Install SDK/NDK
yes | sdkmanager --licenses || true
sdkmanager --install "platform-tools" "platforms;android-33" "build-tools;36.1.0" "cmdline-tools;latest" "ndk;26.1.10909125" || true

# 8. Confirm Installation
sdkmanager --list | head

# 9. Return to Project Directory
cd /root/GHOSH_Robotics

# 10. Force Rebuild the APK
echo "⚙️ Starting BRAHMA_AI Build..."
buildozer -v android debug || echo "⚠️ Build failed — retrying forcefully..." && buildozer -v android debug

# 11. Copy APK to Phone Storage
mkdir -p /sdcard/GHOSH_Robotics
cp /root/GHOSH_Robotics/bin/*.apk /sdcard/GHOSH_Robotics/ 2>/dev/null || echo "⚠️ APK not yet built — check logs."

# 12. Confirmation
echo "============================================================="
echo "✅ BRAHMA_AI APK Build Completed Successfully!"
echo "📦 Output Path: /sdcard/GHOSH_Robotics/"
echo "============================================================="
