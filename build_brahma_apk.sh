#!/data/data/com.termux/files/usr/bin/bash
set -e
BOT_TOKEN="REPLACE_BOT_TOKEN"
CHAT_ID="REPLACE_CHAT_ID"
MAIN_PY="trading_app.py"
SRC="$PWD/$MAIN_PY"
UBU_ROOT="/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/root"
OUT_DIR="/sdcard/GHOSH_Robotics"
mkdir -p "$OUT_DIR"
send_msg(){ [ "$BOT_TOKEN" = "REPLACE_BOT_TOKEN" ] && return; curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" -d chat_id="${CHAT_ID}" -d text="$1" >/dev/null; }
send_file(){ [ "$BOT_TOKEN" = "REPLACE_BOT_TOKEN" ] && return; curl -s -F chat_id="${CHAT_ID}" -F document=@$1 "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" >/dev/null; }

send_msg "🔧 ZBOT build started"
pkg update -y
pkg install -y python python-pip proot-distro git wget unzip zip curl
pip install --upgrade pip
pip install kivy numpy matplotlib requests || true

if ! proot-distro list | grep -q ubuntu; then
  proot-distro install ubuntu
fi

# copy app into ubuntu root
mkdir -p "${UBU_ROOT}"
cp -f "${SRC}" "${UBU_ROOT}/" || { send_msg "⚠️ copy failed"; exit 1; }
send_msg "📁 source copied to Ubuntu root"

# run inside ubuntu
proot-distro login ubuntu <<'UBU'
set -e
export HOME=/root
cd /root
apt update -y
apt install -y python3-venv python3-pip python3-setuptools git zip unzip wget curl openjdk-17-jdk
python3 -m venv /root/venv
source /root/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install buildozer cython kivy numpy matplotlib requests || true

if [ ! -f buildozer.spec ]; then
  buildozer init
  sed -i 's#source.main = .*#source.main = trading_app.py#' buildozer.spec
  sed -i 's#title = .*#title = ZBOT Trading#' buildozer.spec
  sed -i 's#package.name = .*#package.name = zbot_trading#' buildozer.spec
  sed -i 's#package.domain = .*#package.domain = org.zbot#' buildozer.spec
fi

# auto-version
DATE_TAG=$(date +%Y%m%d_%H%M)
sed -i "s/^version = .*/version = 0.1-${DATE_TAG}/" buildozer.spec

# Ensure Android SDK tools (may take time)
export ANDROID_HOME=$HOME/.buildozer/android/platform/android-sdk
mkdir -p "$ANDROID_HOME"
# attempt sdkmanager if exists
if [ -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
  yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$ANDROID_HOME" "build-tools;33.0.2" "platforms;android-33" "platform-tools" || true
fi

# Build APK
buildozer -v android debug || { echo "buildozer failed"; exit 1; }

# copy APK to shared storage
mkdir -p /sdcard/GHOSH_Robotics
cp /root/bin/*.apk /sdcard/GHOSH_Robotics/ || true
UBU
# end proot

APK=$(ls /sdcard/GHOSH_Robotics/*.apk 2>/dev/null | tail -n1 || true)
if [ -f "$APK" ]; then
  send_msg "✅ Build complete. APK saved to /sdcard/GHOSH_Robotics/"
  send_file "$APK"
else
  send_msg "⚠️ Build finished but APK not found. Check /root/.buildozer for logs"
fi
echo "Done. APK (if built) copied to $OUT_DIR"
