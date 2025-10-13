#!/usr/bin/env python3
# GRRFP + Rahul.ai — EEG + IoT Integration Prototype
import asyncio, serial, json, time, uuid, requests

def now(): return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
def clamp(v,a,b): return max(a, min(b, v))

class RKC:
    def __init__(self): self.logs=[]
    def log(self,src,lvl,data):
        e={"id":str(uuid.uuid4()),"ts":now(),"src":src,"lvl":lvl,"data":data}
        self.logs.append(e)
        print(f"[RKC] {e['ts']} | {src} | {lvl} | {data}")

class UCG:
    def __init__(self,logger): self.l=logger
    def check(self,energy):
        act="ALLOW" if energy<0.9 else "THROTTLE"
        self.l.log("UCG","INFO",{"energy":energy,"action":act})
        return act

class OpenBCIReader:
    def __init__(self,port="/dev/ttyUSB0",baud=115200):
        self.ser=serial.Serial(port,baud,timeout=1)
    def read_sample(self):
        line=self.ser.readline().decode(errors="ignore").strip()
        if not line: return None
        try:
            js=json.loads(line)
            ch=js.get("data",[])
            if not ch: return None
            att=clamp(abs(ch[0])/1000.0,0,1)
            relax=clamp(abs(ch[1])/1000.0,0,1)
            inten=clamp(abs(ch[2])/1000.0,0,1)
            return {"attention":att,"relaxation":relax,"intent":inten}
        except: return None

class NRPI:
    def __init__(self,logger): self.l=logger
    def process(self,sample):
        if not sample: return None
        ri=(sample["attention"]*0.4+sample["intent"]*0.6)*(1-abs(sample["relaxation"]-0.5))
        self.l.log("NRPI","TRACE",{"sample":sample,"ri":ri})
        return {"ri":ri}

class Decoder:
    def __init__(self,logger): self.l=logger
    def decode(self,frame):
        ri=frame["ri"]
        if ri>0.7: intent="lights_on"
        elif ri>0.45: intent="greet"
        else: intent="idle"
        text={"lights_on":"Turning on lights","greet":"Hello there","idle":""}[intent]
        self.l.log("Decoder","INFO",{"ri":ri,"intent":intent})
        return intent,text

class RahulAI:
    def __init__(self,logger): self.l=logger
    def interpret(self,intent,text):
        if intent=="greet": text+=", friend."
        self.l.log("RahulAI","DEBUG",{"intent":intent,"text":text})
        return text

class Spandan:
    def __init__(self,logger,ucg,relay_url=None):
        self.l=logger; self.ucg=ucg; self.state={"lights":False}
        self.relay_url=relay_url
    def decide(self,intent,text,ri):
        act=self.ucg.check(ri*0.5)
        if intent=="lights_on" and act=="ALLOW":
            self.state["lights"]=True
            if self.relay_url:
                try:
                    requests.get(self.relay_url,timeout=2)
                    self.l.log("IoT","INFO",{"url":self.relay_url,"result":"triggered"})
                except Exception as e:
                    self.l.log("IoT","ERROR",str(e))
        self.l.log("Spandan","INFO",{"intent":intent,"state":self.state})
        return {"text":text,"state":self.state}

async def main():
    log=RKC(); ucg=UCG(log)
    bci=OpenBCIReader("/dev/ttyUSB0")
    nrpi=NRPI(log); dec=Decoder(log); rahul=RahulAI(log)
    relay="http://192.168.0.105/relay_on"  # your ESP/IoT endpoint here
    sp=Spandan(log,ucg,relay)
    print("=== GRRFP+Rahul.ai : OpenBCI + IoT Live ===")

    for _ in range(60):  # ~30 sec run
        s=bci.read_sample()
        if not s: continue
        f=nrpi.process(s)
        if not f: continue
        intent,text=dec.decode(f)
        msg=rahul.interpret(intent,text)
        out=sp.decide(intent,msg,f["ri"])
        if msg: log.log("OUTPUT","TEXT",out)
        await asyncio.sleep(0.5)
    print("=== Done ===")

if __name__=="__main__":
    asyncio.run(main())
