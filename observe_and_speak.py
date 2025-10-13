#!/usr/bin/env python3
# observe_and_speak.py
# GRRFP + Rahul.ai + IoT unified loop
# Works in Termux with TTS + WiFi relay triggers

import asyncio, json, time, random, os, csv
from subprocess import call

try:
    import requests
except ImportError:
    requests = None

LOG_FILE = os.path.expanduser("~/rkc_observe_log.csv")
RELAY_ON = "http://192.168.0.105/relay_on"      # change to your ESP/IoT URL
RELAY_OFF = "http://192.168.0.105/relay_off"    # change to your ESP/IoT URL

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def speak(text):
    if text:
        try:
            call(["termux-tts-speak", text])
        except Exception:
            print("[TTS]", text)

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def rkc_log(module, level, payload):
    print(f"[RKC] {now()} | {module} | {level} | {json.dumps(payload)}")
    try:
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([now(), module, level, json.dumps(payload)])
    except Exception:
        pass

class FakeNRPI:
    def read(self):
        return {
            "attention": clamp(random.gauss(0.5, 0.2)),
            "relax": clamp(random.gauss(0.5, 0.2)),
            "intent": clamp(random.gauss(0.4, 0.25))
        }

class FakeMIPA:
    def read(self):
        return {
            "posture": clamp(random.gauss(0.5, 0.2)),
            "breath": clamp(random.gauss(0.3, 0.1))
        }

class RahulAI:
    def fuse(self, n, m):
        ri = clamp((n["attention"] * 0.6 + n["intent"] * 0.4 + m["posture"] * 0.2) / 1.2)
        return ri

    def interpret(self, ri):
        if ri > 0.7:
            return "focus_high", "You are highly focused. Turning lights on."
        elif ri < 0.3:
            return "low_state", "Low energy detected. Dimming lights."
        else:
            return "neutral", ""

class IoT:
    def trigger(self, url):
        if not requests:
            rkc_log("IoT", "WARN", {"msg": "requests not available"})
            return
        try:
            r = requests.get(url, timeout=3)
            rkc_log("IoT", "INFO", {"url": url, "code": r.status_code})
        except Exception as e:
            rkc_log("IoT", "ERROR", {"url": url, "err": str(e)})

class Spandan:
    def __init__(self):
        self.iot = IoT()
        self.state = {"lights": False}

    def act(self, intent):
        if intent == "focus_high" and not self.state["lights"]:
            self.iot.trigger(RELAY_ON)
            self.state["lights"] = True
        elif intent == "low_state" and self.state["lights"]:
            self.iot.trigger(RELAY_OFF)
            self.state["lights"] = False
        rkc_log("Spandan", "INFO", {"intent": intent, "state": self.state})

async def observe(runtime=60):
    nrpi = FakeNRPI()
    mipa = FakeMIPA()
    rahul = RahulAI()
    sp = Spandan()

    rkc_log("System", "INFO", {"event": "start"})
    end = time.time() + runtime
    while time.time() < end:
        n = nrpi.read()
        m = mipa.read()
        ri = rahul.fuse(n, m)
        intent, msg = rahul.interpret(ri)
        sp.act(intent)
        if msg:
            speak(msg)
        await asyncio.sleep(1)
    rkc_log("System", "INFO", {"event": "stop"})

if __name__ == "__main__":
    try:
        asyncio.run(observe(120))
    except KeyboardInterrupt:
        rkc_log("System", "WARN", {"event": "interrupted"})
