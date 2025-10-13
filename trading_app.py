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
