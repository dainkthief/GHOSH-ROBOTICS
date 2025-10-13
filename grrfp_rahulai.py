#!/usr/bin/env python3
import asyncio, random, time, uuid
from typing import Dict, Any, List

def now_ts():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def clamp(v, a, b):
    return max(a, min(b, v))

class RKCLogger:
    def __init__(self):
        self.entries = []
    def log(self, src, lvl, data):
        e = {"id": str(uuid.uuid4()), "ts": now_ts(), "src": src, "lvl": lvl, "data": data}
        self.entries.append(e)
        print(f"[RKC] {e['ts']} | {src} | {lvl} | {data}")

class UCG:
    def __init__(self, logger):
        self.l = logger
    def evaluate(self, energy):
        action = "ALLOW" if energy < 0.9 else "THROTTLE"
        self.l.log("UCG", "INFO", {"energy": energy, "action": action})
        return action

class EEGSimulator:
    def __init__(self, seed=None):
        self.r = random.Random(seed)
    def sample(self):
        return {
            "attention": clamp(self.r.gauss(0.5, 0.18), 0, 1),
            "relaxation": clamp(self.r.gauss(0.5, 0.18), 0, 1),
            "intent": clamp(abs(self.r.gauss(0.25, 0.25)), 0, 1)
        }

class NRPI:
    def __init__(self, logger):
        self.l = logger
        self.base = {"attention": 0.5, "relaxation": 0.5, "intent": 0.2}
    def preprocess(self, s):
        r = (s["attention"]*0.4 + s["intent"]*0.6) * (1 - abs(s["relaxation"]-0.5))
        self.l.log("NRPI", "TRACE", {"sample": s, "ri": r})
        return {"resonant_impulse": r}

class Decoder:
    def __init__(self, logger):
        self.l = logger
    def decode(self, f):
        ri = f["resonant_impulse"]
        intent = "lights_on" if ri > 0.65 else "greet" if ri > 0.4 else "idle"
        text = {"lights_on": "Turning on lights", "greet": "Hello there", "idle": ""}[intent]
        self.l.log("Decoder", "INFO", {"ri": ri, "intent": intent})
        return intent, text

class RahulAI:
    def __init__(self, logger):
        self.l = logger
    def interpret(self, intent, text):
        if intent == "greet": text += ", friend."
        self.l.log("RahulAI", "DEBUG", {"intent": intent, "text": text})
        return text

class Spandan:
    def __init__(self, logger, ucg):
        self.l = logger; self.ucg = ucg; self.state = {"lights": False}
    def act(self, intent, text, ri):
        decision = self.ucg.evaluate(ri*0.5)
        if intent == "lights_on" and decision == "ALLOW":
            self.state["lights"] = True
        self.l.log("Spandan", "INFO", {"intent": intent, "state": self.state})
        return {"text": text, "state": self.state}

async def main():
    log = RKCLogger()
    ucg = UCG(log)
    eeg = EEGSimulator(42)
    nrpi = NRPI(log)
    dec = Decoder(log)
    rahul = RahulAI(log)
    sp = Spandan(log, ucg)

    print("=== GRRFP + Rahul.ai prototype ===")
    for _ in range(15):
        s = eeg.sample()
        f = nrpi.preprocess(s)
        i, t = dec.decode(f)
        msg = rahul.interpret(i, t)
        out = sp.act(i, msg, f["resonant_impulse"])
        if msg: log.log("OUTPUT", "TEXT", out)
        await asyncio.sleep(0.5)
    print("=== Done ===")

if __name__ == "__main__":
    asyncio.run(main())
