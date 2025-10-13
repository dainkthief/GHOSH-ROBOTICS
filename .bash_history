        return 1000.0 + sum(xs)*2.0
    def evaluate(self):
        xs=self.kernel.snapshot()
        signs=[1 if x>=0 else -1 for x in xs]
        alternations=sum(1 for i in range(1,len(signs)) if signs[i]!=signs[i-1])
        mean=sum(xs)/len(xs)
        signal = "LONG" if mean>0 else "SHORT" if alternations>=max(2,int(len(signs)/2)) else "WAIT"
        price=self.synthetic_price()
        if self.mode=="NEUTRAL" and signal in ("LONG","SHORT"):
            self.mode=signal; self.entry_price=price; self.peak=price
            self.logs.append(("ENTRY", time.time(), signal, price))
            tg_notify(f"[TRADER] ENTRY {signal} @ {price:.2f}")
            return {"action":"ENTRY","side":signal,"price":price}
        if self.mode in ("LONG","SHORT"):
            if self.mode=="LONG" and price>self.peak: self.peak=price
            if self.mode=="SHORT" and price<self.peak: self.peak=price
            if self.mode=="LONG":
                stop=self.peak*(1-self.trail_pct)
                if price<=stop:
                    exit_price=price; pnl=exit_price-self.entry_price
                    self.logs.append(("EXIT",time.time(),"LONG",exit_price,pnl))
                    tg_notify(f"[TRADER] EXIT LONG @ {exit_price:.2f} PNL {pnl:.2f}")
                    self.mode="NEUTRAL"; self.entry_price=None; self.peak=None
                    return {"action":"EXIT","side":"LONG","price":exit_price,"pnl":pnl}
            else:
                stop=self.peak*(1+self.trail_pct)
                if price>=stop:
                    exit_price=price; pnl=self.entry_price-exit_price
                    self.logs.append(("EXIT",time.time(),"SHORT",exit_price,pnl))
                    tg_notify(f"[TRADER] EXIT SHORT @ {exit_price:.2f} PNL {pnl:.2f}")
                    self.mode="NEUTRAL"; self.entry_price=None; self.peak=None
                    return {"action":"EXIT","side":"SHORT","price":exit_price,"pnl":pnl}
        return {"action":"HOLD","signal":signal,"price":price}
    def dump_csv(self, path=None):
        path = path or os.path.join(SAVE_DIR, f"trade_log_{int(time.time())}.csv")
        with open(path,"w",newline="") as f:
            import csv
            w=csv.writer(f); w.writerow(["type","timestamp","side","price","pnl"])
            for row in self.logs: w.writerow(row)
        return path

# Kivy GUI
class OscWidget(Widget):
    def __init__(self,kernel,**kw):
        super().__init__(**kw); self.kernel=kernel
        Clock.schedule_interval(self.redraw, 1/30.)
    def redraw(self, dt):
        self.canvas.clear()
        w,h=self.width,self.height
        xs=self.kernel.snapshot()
        spacing=w/(len(xs)+1)
        with self.canvas:
            Color(0.06,0.06,0.06,1); Rectangle(pos=self.pos,size=self.size)
            Color(0.6,0.6,0.6,1); Line(points=[self.x, self.y+h/2, self.x+w, self.y+h/2], width=1)
            for i,v in enumerate(xs):
                px=self.x+(i+1)*spacing; py=self.y+h/2+v*80
                Color(0.2,0.7,0.9,1); Line(points=[px,self.y+h/2,px,py], width=2)
                Color(0.9,0.3,0.2,1); Line(circle=(px,py,6), width=1.5)

class TradingGUI(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.kernel=GRRFP(N=7); self.trail=TrailingManager(self.kernel)
        ctrl=BoxLayout(size_hint_y=0.12)
        self.mode_label=Label(text="MODE: DEV (24h)", size_hint_x=0.4)
        self.live_btn=Button(text="LIVE OFF", on_release=self.toggle_live)
        self.auto_btn=Button(text="AUTO OFF", on_release=self.toggle_auto)
        ctrl.add_widget(self.mode_label); ctrl.add_widget(self.live_btn); ctrl.add_widget(self.auto_btn)
        self.add_widget(ctrl)
        self.osc=OscWidget(self.kernel, size_hint_y=0.6); self.add_widget(self.osc)
        bottom=BoxLayout(orientation="vertical", size_hint_y=0.28)
        info=BoxLayout(size_hint_y=0.32)
        self.status=Label(text="Status: IDLE"); self.signal=Label(text="Signal: WAIT")
        info.add_widget(self.status); info.add_widget(self.signal)
        bottom.add_widget(info)
        self.log=TextInput(text="Events:\n", readonly=True)
        bottom.add_widget(self.log)
        self.add_widget(bottom)
        self.live=False; self.auto=False
        Clock.schedule_interval(self.step, 0.05)
    def toggle_live(self, *_):
        self.live=not self.live; self.live_btn.text="LIVE ON" if self.live else "LIVE OFF"
        self.mode_label.text = "MODE: LIVE" if self.live else "MODE: DEV (24h)"
        tg_notify(f"[UI] Live set to {self.live}")
    def toggle_auto(self, *_):
        self.auto=not self.auto; self.auto_btn.text="AUTO ON" if self.auto else "AUTO OFF"
        tg_notify(f"[UI] Auto set to {self.auto}")
    def manual_order(self, side="LONG"):
        price=self.trail.synthetic_price()
        self.log_event(f"MANUAL {side}", price); tg_notify(f"[MANUAL] {side} @ {price:.2f}")
    def log_event(self, ev, price=None):
        t=time.strftime("%H:%M:%S"); s=f"{t} | {ev}"
        if price is not None: s+=f" @ {price:.2f}"
        self.log.text += s+"\n"; self.log.cursor=(0,len(self.log.text))
    def step(self, dt):
        t=self.kernel.time
        impulses=[]
        if int(t*10)%50==0: impulses.append((t, int(t)%self.kernel.N, 2.0))
        self.kernel.step(dt, impulses)
        if self.auto:
            res=self.trail.evaluate()
            if res["action"]=="ENTRY": self.log_event(f"ENTRY {res['side']}", res["price"])
            if res["action"]=="EXIT": self.log_event(f"EXIT {res['side']} PNL {res.get('pnl',0):.2f}", res["price"])
            self.status.text=f"State: {self.trail.mode}; Price {res['price']:.2f}"
            self.signal.text=f"Signal: {res['signal']}"
        else:
            self.status.text=f"Dev Sum:{sum(self.kernel.snapshot()):.3f}"
            self.signal.text="Signal: DEV"
    def save_logs(self):
        path=self.trail.dump_csv(os.path.join(SAVE_DIR, "trade_log.csv"))
        self.log_event("SAVED_LOG", 0); tg_notify(f"[TRADER] Log saved {path}")

class TradingApp(App):
    def build(self): self.title="ZBOT Trading - DEV+LIVE"; return TradingGUI()
    def on_stop(self):
        try: self.root.save_logs()
        except Exception: pass

if __name__=="__main__":
    TradingApp().run()
PY

# ------------------------
# Builder script: Termux -> Ubuntu -> Buildozer -> APK
# ------------------------
cat > build_brahma_apk.sh <<'SH'
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
SH

chmod +x build_brahma_apk.sh
echo "Files created: trading_app.py, build_brahma_apk.sh"
echo "Edit BOT_TOKEN, CHAT_ID, and KITE credentials inside trading_app.py or builder if needed."
echo "Run builder: bash build_brahma_apk.sh"
#!/usr/bin/env python3
# trading_app.py
# Kivy trading GUI + GRRFP engine + trailing logic + logs + Telegram notify (simulation-mode)
import os, time, math, json, csv, threading
from dataclasses import dataclass, field
from typing import List
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
# ------------------------
# Config
# ------------------------
SAVE_DIR = "/sdcard/ZBOT_Trading"
os.makedirs(SAVE_DIR, exist_ok=True)
BOT_TOKEN = "REPLACE_WITH_YOUR_TELEGRAM_BOT_TOKEN"   # optional
CHAT_ID  = "REPLACE_WITH_CHAT_ID"                   # optional
SIMULATION = True  # True = no real orders, False = send to broker (implement adapter)
# ------------------------
# Simple Telegram helper
# ------------------------
def tg_notify(msg: str):
# ------------------------
# GRRFP Kernel (oscillators)
# ------------------------
@dataclass
class Node:
class GRRFP:
# ------------------------
# Trailing logic (diagram-based)
# - pattern: alternating peaks across nodes produce entry signal
# - trailing stop: follows peak in favor
# ------------------------
class TrailingManager:
# ------------------------
# Kivy GUI
# ------------------------
class OscWidget(Widget):
class TradingGUI(BoxLayout):
class TradingApp(App):
if __name__ == "__main__":;     TradingApp().run()
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export LANG=C.UTF-8
# -------------------------
# Config - edit here if needed
# -------------------------
BOT_TOKEN="${BOT_TOKEN:-REPLACE_TELEGRAM_BOT_TOKEN}"   # set in env or edit here
CHAT_ID="${CHAT_ID:-REPLACE_CHAT_ID}"                 # set in env or edit here
OUT_DIR="/sdcard/GHOSH_Robotics"
SRC_NAME="trading_app.py"
UBU_ROOT="/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu/root"
mkdir -p "$OUT_DIR"
notify(){ 
  echo "$1";   if [[ "$BOT_TOKEN" != "REPLACE_TELEGRAM_BOT_TOKEN" && "$CHAT_ID" != "REPLACE_CHAT_ID" ]]; then     curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"       -d chat_id="$CHAT_ID" -d text="$1" >/dev/null || true;   fi; }
notify "🔧 BRAHMA / ZBOT auto builder starting"
# -------------------------
# Write Python Kivy app (no BOM)
# -------------------------
cat > "$SRC_NAME" <<'PYCODE'
#!/usr/bin/env python3
# trading_app.py - Kivy trading GUI + GRRFP engine + trailing logic + Telegram notify (simulation-mode)
import os, time, math, csv
from dataclasses import dataclass, field
from typing import List
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle

SAVE_DIR = "/sdcard/ZBOT_Trading"
os.makedirs(SAVE_DIR, exist_ok=True)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
SIMULATION = True

def tg_notify(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except Exception:
        pass

@dataclass
class Node:
    id: int
    freq: float = 1.0
    damping: float = 0.05
    state: List[float] = field(default_factory=lambda:[0.0,0.0])
    def step(self, dt, force=0.0):
        k = (2*math.pi*self.freq)**2
        x,v = self.state
        a = (-self.damping*v - k*x + force)
        v += a*dt
        x += v*dt
        self.state = [x,v]

class GRRFP:
    def __init__(self,N=7,coupling=0.7):
        self.N=N; self.nodes=[Node(i, freq=0.5+0.25*i) for i in range(N)]
        self.time=0.0
        self.coupling=coupling
    def step(self, dt, impulses=[]):
        xs=[n.state[0] for n in self.nodes]
        coupling_terms=[0.0]*self.N
        for i in range(self.N):
            s=0.0
            for j in range(self.N):
                if i==j: continue
                s += self.coupling*(xs[j]-xs[i])
            coupling_terms[i]=s
        forces=[0.0]*self.N
        for (ti,nid,amp) in impulses:
            if abs(self.time - ti) < 0.05:
                forces[nid] += amp
        for i,n in enumerate(self.nodes):
            n.step(dt, forces[i] + coupling_terms[i])
        self.time += dt
    def snapshot(self):
        return [n.state[0] for n in self.nodes]

class TrailingManager:
    def __init__(self, kernel: GRRFP, trail_pct=0.006):
        self.kernel = kernel
        self.mode = "NEUTRAL"
        self.entry_price = None
        self.peak = None
        self.trail_pct = trail_pct
        self.logs = []
    def evaluate(self):
        xs = self.kernel.snapshot()
        price = 1000.0 + sum(xs)*2.0
        signs = [1 if x>=0 else -1 for x in xs]
        alternations = sum(1 for i in range(1,len(signs)) if signs[i]!=signs[i-1])
        if alternations >= max(2, int(len(signs)/2)):
            mean = sum(xs)/len(xs)
            signal = "LONG" if mean > 0 else "SHORT"
        else:
            signal = "WAIT"
        if self.mode=="NEUTRAL" and signal in ("LONG","SHORT"):
            self.mode = signal
            self.entry_price = price
            self.peak = price
            self.logs.append(("ENTRY", time.time(), signal, price))
            tg_notify(f"[TRADER] ENTRY {signal} @ {price:.2f}")
            return {"action":"ENTRY","side":signal,"price":price}
        if self.mode in ("LONG","SHORT"):
            if self.mode=="LONG" and price>self.peak: self.peak=price
            if self.mode=="SHORT" and price<self.peak: self.peak=price
            if self.mode=="LONG":
                stop = self.peak*(1 - self.trail_pct)
                if price <= stop:
                    exit_price = price
                    pnl = exit_price - self.entry_price
                    self.logs.append(("EXIT", time.time(), "LONG", exit_price, pnl))
                    tg_notify(f"[TRADER] EXIT LONG @ {exit_price:.2f} PNL {pnl:.2f}")
                    self.mode="NEUTRAL"; self.entry_price=None; self.peak=None
                    return {"action":"EXIT","side":"LONG","price":exit_price,"pnl":pnl}
            else:
                stop = self.peak*(1 + self.trail_pct)
                if price >= stop:
                    exit_price = price
                    pnl = self.entry_price - exit_price
                    self.logs.append(("EXIT", time.time(), "SHORT", exit_price, pnl))
                    tg_notify(f"[TRADER] EXIT SHORT @ {exit_price:.2f} PNL {pnl:.2f}")
                    self.mode="NEUTRAL"; self.entry_price=None; self.peak=None
                    return {"action":"EXIT","side":"SHORT","price":exit_price,"pnl":pnl}
        return {"action":"HOLD","signal":signal,"price":price}
    def dump_csv(self, path=None):
        path = path or os.path.join(SAVE_DIR, f"trade_log_{int(time.time())}.csv")
        with open(path,"w",newline="") as f:
            w=csv.writer(f); w.writerow(["type","timestamp","side","price","pnl"])
            for row in self.logs: w.writerow(row)
        return path

class OscWidget(Widget):
    def __init__(self,kernel,**kw):
        super().__init__(**kw); self.kernel=kernel
        Clock.schedule_interval(self.redraw, 1/20.)
    def redraw(self, dt):
        self.canvas.clear()
        w,h = self.width, self.height
        xs = self.kernel.snapshot()
        spacing = w/(len(xs)+1)
        with self.canvas:
            Color(0.06,0.06,0.06,1); Rectangle(pos=self.pos,size=self.size)
            Color(0.6,0.6,0.6,1); Line(points=[self.x, self.y+h/2, self.x+w, self.y+h/2], width=1)
            for i,v in enumerate(xs):
                px = self.x + (i+1)*spacing
                py = self.y + h/2 + v*80
                Color(0.2,0.7,0.9,1); Line(points=[px, self.y+h/2, px, py], width=2)
                Color(0.9,0.3,0.2,1); Line(circle=(px,py,6), width=1.5)

class TradingGUI(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.kernel = GRRFP(N=7)
        self.trail = TrailingManager(self.kernel, trail_pct=0.006)
        ctrl = BoxLayout(size_hint_y=0.12)
        self.mode_label = Label(text="MODE: DEV", size_hint_x=0.5)
        self.auto_btn = Button(text="AUTO: OFF", on_release=self.toggle_auto)
        self.manual_btn = Button(text="MANUAL ORDER", on_release=self.manual_order)
        ctrl.add_widget(self.mode_label); ctrl.add_widget(self.auto_btn); ctrl.add_widget(self.manual_btn)
        self.add_widget(ctrl)
        self.osc = OscWidget(self.kernel, size_hint_y=0.6)
        self.add_widget(self.osc)
        bottom = BoxLayout(size_hint_y=0.28, orientation="vertical")
        info = BoxLayout(size_hint_y=0.3)
        self.status = Label(text="Status: IDLE")
        self.signal = Label(text="Signal: WAIT")
        info.add_widget(self.status); info.add_widget(self.signal)
        bottom.add_widget(info)
        self.log = TextInput(text="Events:\n", readonly=True)
        bottom.add_widget(self.log)
        self.add_widget(bottom)
        self.auto = False
        Clock.schedule_interval(self.step_kernel, 0.05)

    def toggle_auto(self, *_):
        self.auto = not self.auto
        self.auto_btn.text = "AUTO: ON" if self.auto else "AUTO: OFF"
        self.mode_label.text = "MODE: LIVE" if self.auto else "MODE: DEV"
        tg_notify(f"[UI] Auto set to {self.auto}")

    def manual_order(self, *_):
        price = 1000.0 + sum(self.kernel.snapshot())*2.0
        self.log_event("MANUAL_ORDER", price)
        tg_notify(f"[MANUAL] Order requested @ {price:.2f}")

    def log_event(self, ev, price=None):
        t = time.strftime("%H:%M:%S")
        s = f"{t} | {ev}"
        if price is not None: s += f" @ {price:.2f}"
        self.log.text += s + "\n"
        self.log.cursor = (0, len(self.log.text))

    def step_kernel(self, dt):
        t = self.kernel.time
        impulses = []
        if int(t*10) % 50 == 0:
            impulses.append((t, int(t) % self.kernel.N, 2.5))
        self.kernel.step(dt, impulses)
        if self.auto:
            res = self.trail.evaluate()
            if res["action"]=="ENTRY":
                self.log_event(f"ENTRY {res['side']}", res["price"])
            if res["action"]=="EXIT":
                self.log_event(f"EXIT {res['side']} PNL {res.get('pnl',0):.2f}", res["price"])
            self.status.text = f"State: {self.trail.mode}"
            self.signal.text = f"Signal: {res['signal']}"
        else:
            snapshot = sum(self.kernel.snapshot())
            self.status.text = f"Dev Sum:{snapshot:.3f}"
            self.signal.text = "Signal: DEV"

    def save_and_shutdown(self):
        path = self.trail.dump_csv(os.path.join(SAVE_DIR, "trade_log.csv"))
        self.log_event("SAVED_LOG", 0)
        tg_notify(f"[TRADER] Log saved to {path}")

class TradingApp(App):
    def build(self):
        self.title = "ZBOT Trading - BRAHMA"
        return TradingGUI()
    def on_stop(self):
        try:
            self.root.save_and_shutdown()
        except Exception:
            pass

if __name__ == "__main__":
    TradingApp().run()
PYCODE

notify "✅ Python app written: $SRC_NAME"
# -------------------------
# Install Termux packages (native)
# -------------------------
notify "📦 Installing Termux packages (may prompt)"
pkg update -y
pkg install -y clang make cmake ninja git python python-dev python-pip proot-distro wget unzip zip openjdk-17 curl
