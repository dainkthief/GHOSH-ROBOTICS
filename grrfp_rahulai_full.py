#!/usr/bin/env python3
# GRRFP + Rahul.ai Unified Cognitive Pipeline (Termux Safe Version)

import asyncio, serial, json, time, uuid, requests, socket, os
from subprocess import call

def now(): return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
def clamp(v, a, b): return max(a, min(b, v))
def speak(txt): 
    try: call(["termux-tts-speak", txt])
    except: print("[WARN] TTS unavailable")

class RKC:
    def __init__(self): self.logs = []
    def log(self, src, lvl, data):
        entry = {"id": str(uuid.uuid4()), "time": now(), "src": src, "lvl": lvl, "data": data}
        self.logs.append(entry)
        print(f"[RKC] {entry['time']} | {src} | {lvl} | {data}")

class UCG:
    def __init__(self, l): self.l = l
    def check(self, energy):
        act = "ALLOW" if energy < 0.9 else "THROTTLE"
        self.l.log("UCG", "INFO", {"energy": energy, "action": act})
        return act

class OpenBCIReader:
    def __init__(self, l, port="/dev/ttyUSB0", baud=115200, host=None, port_tcp=9000):
        self.l = l; self.serial = None; self.sock = None
        try:
            if host:
                self.sock = socket.socket(); self.sock.connect((host, port_tcp))
                self.l.log("BRAINLINK", "INFO", f"TCP {host}:{port_tcp}")
            else:
                self.serial = serial.Serial(port, baud, timeout=1)
                self.l.log("BRAINLINK", "INFO", f"Serial {port}")
        except Exception as e:
            self.l.log("BRAINLINK", "ERROR", f"{e}")
    def read_sample(self):
        try:
            if self.serial:
                line = self.serial.readline().decode(errors="ignore").strip()
            elif self.sock:
                line = self.sock.recv(1024).decode(errors="ignore").strip()
            else:
                return None
            if not line: return None
            js = json.loads(line)
            ch = js.get("data", [])
            if not ch: return None
            att = clamp(abs(ch[0])/1000, 0, 1)
            relax = clamp(abs(ch[1])/1000, 0, 1)
            inten = clamp(abs(ch[2])/1000, 0, 1)
            return {"attention": att, "relaxation": relax, "intent": inten}
        except: return None

class NRPI:
    def __init__(self, l): self.l = l
    def process(self, s):
        if not s: return None
        ri = (s["attention"]*0.4 + s["intent"]*0.6) * (1 - abs(s["relaxation"]-0.5))
        self.l.log("NRPI", "TRACE", {"sample": s, "ri": ri})
        return {"ri": ri}

class Decoder:
    def __init__(self, l): self.l = l
    def decode(self, f):
        ri = f["ri"]
        if ri > 0.7: intent = "lights_on"
        elif ri > 0.45: intent = "greet"
        else: intent = "idle"
        text = {"lights_on":"Turning on lights","greet":"Hello there","idle":""}[intent]
        self.l.log("Decoder","INFO",{"ri":ri,"intent":intent})
        return intent, text

class RahulAI:
    def __init__(self, l): self.l = l
    def interpret(self, intent, text):
        if intent == "greet": text += ", friend."
        self.l.log("RahulAI","DEBUG",{"intent":intent,"text":text})
        return text

class Spandan:
    def __init__(self, l, ucg, relay=None):
        self.l = l; self.ucg = ucg; self.state = {"lights":False}; self.relay = relay
    def decide(self, intent, text, ri):
        act = self.ucg.check(ri*0.5)
        if intent == "lights_on" and act == "ALLOW":
            self.state["lights"] = True
            if self.relay:
                try:
                    requests.get(self.relay, timeout=2)
                    self.l.log("IoT","INFO",{"url":self.relay,"result":"triggered"})
                except Exception as e:
                    self.l.log("IoT","ERROR",str(e))
        if intent == "idle" and self.state["lights"]:
            self.state["lights"] = False
            self.l.log("IoT","INFO","Relay OFF")
        self.l.log("Spandan","INFO",{"intent":intent,"state":self.state})
        return {"text":text,"state":self.state}

async def main():
    log = RKC(); ucg = UCG(log)
    try: bci = OpenBCIReader(log,"/dev/ttyUSB0")
    except: bci = OpenBCIReader(log,None,host="192.168.0.101",port_tcp=9000)
    nrpi = NRPI(log); dec = Decoder(log); rahul = RahulAI(log)
    sp = Spandan(log,ucg,"http://192.168.0.105/relay_on")
    print("=== GRRFP + Rahul.ai Unified : Live Mode ===")
    for _ in range(60):
        s = bci.read_sample()
        if not s: continue
        f = nrpi.process(s)
        if not f: continue
        intent, text = dec.decode(f)
        msg = rahul.interpret(intent, text)
        out = sp.decide(intent, msg, f["ri"])
        if msg:
            speak(msg)
            log.log("OUTPUT","TEXT",out)
        await asyncio.sleep(0.5)
    print("=== Done ===")

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("Interrupted.")
