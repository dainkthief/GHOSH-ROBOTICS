import asyncio, random, requests, json, time, os
from subprocess import call
from datetime import datetime

# ==== Core Logging ====
class RKC:
    def log(self, module, level, data):
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[RKC] {t} | {module} | {level} | {json.dumps(data)}")

# ==== Universal Circulation Governor ====
class UCG:
    def __init__(self, log): self.l = log
    def check(self, ri):
        act = "ALLOW" if ri > 0.2 else "BLOCK"
        self.l.log("UCG","INFO",{"energy":round(ri,2),"action":act})
        return act

# ==== Fake Brain Input (Simulated BCI) ====
class FakeBCI:
    def read_sample(self):
        return {
            "attention": random.random(),
            "relaxation": random.random(),
            "intent": random.random()
        }

# ==== Neural Resonant Processing ====
class NRPI:
    def __init__(self, log): self.l = log
    def process(self, s):
        if not s: return None
        ri = (s["attention"] + s["relaxation"]) / 2
        self.l.log("NRPI","TRACE",{"sample":s,"ri":ri})
        return {"ri":ri}

# ==== Decoder ====
class Decoder:
    def __init__(self, log): self.l = log
    def decode(self, f):
        ri = f["ri"]
        intent = "greet" if ri>0.6 else "lights_on" if ri>0.4 else "idle"
        self.l.log("Decoder","INFO",{"ri":ri,"intent":intent})
        return intent, ""

# ==== Rahul.ai Layer ====
class RahulAI:
    def __init__(self, log): self.l = log
    def interpret(self, intent, text):
        if intent=="greet": text="Hello there, friend."
        elif intent=="lights_on": text="Turning on lights."
        elif intent=="idle": text=""
        self.l.log("RahulAI","DEBUG",{"intent":intent,"text":text})
        return text

# ==== Spandan (Action + IoT Relay) ====
class Spandan:
    def __init__(self, log, ucg, relay_url=None):
        self.l = log; self.ucg = ucg
        self.state={"lights":False}
        self.relay_url=relay_url

    def decide(self, intent, text, ri):
        act=self.ucg.check(ri)
        if intent=="lights_on" and act=="ALLOW":
            self.state["lights"]=True
            if self.relay_url:
                try:
                    requests.get(self.relay_url,timeout=1)
                    self.l.log("IoT","INFO",{"url":self.relay_url,"result":"triggered"})
                except Exception as e:
                    self.l.log("IoT","ERROR",str(e))
        elif intent=="idle" and self.state["lights"]:
            self.state["lights"]=False
            self.l.log("IoT","INFO",{"Relay":"OFF"})
        self.l.log("Spandan","INFO",{"intent":intent,"state":self.state})
        return {"text":text,"state":self.state}

# ==== Android TTS ====
def speak(txt):
    if txt: call(["termux-tts-speak",txt])

# ==== Main Brain Loop ====
async def main():
    log=RKC(); ucg=UCG(log)
    bci=FakeBCI(); nrpi=NRPI(log)
    dec=Decoder(log); rahul=RahulAI(log)
    relay="http://192.168.0.105/relay_on"  # adjust your relay endpoint
    sp=Spandan(log,ucg,relay)

    print("=== GRRFP + Rahul.ai Unified Cognitive IoT Mode ===")
    for _ in range(30):
        s=bci.read_sample()
        f=nrpi.process(s)
        if not f: continue
        intent,text=dec.decode(f)
        msg=rahul.interpret(intent,text)
        out=sp.decide(intent,msg,f["ri"])
        if msg: speak(msg)
        await asyncio.sleep(1)
    print("=== Done ===")

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("Interrupted.")
