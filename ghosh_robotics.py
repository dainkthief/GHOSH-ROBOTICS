#!/usr/bin/env python3
import math, time, json, os
from dataclasses import dataclass, field
from typing import List
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window

SAVE_DIR = "/sdcard/GHOSH_Robotics"
os.makedirs(SAVE_DIR, exist_ok=True)

class RahulAI:
    def __init__(self):
        self.identity = {
            "name": "Rahul.ai",
            "framework": "GRRFP + RKC",
            "version": "2.0-LIVE",
            "status": "operational",
            "timestamp": time.ctime()
        }
    def log_identity(self):
        path = os.path.join(SAVE_DIR, "rahul_identity.json")
        with open(path, "w") as f:
            json.dump(self.identity, f, indent=2)
        print(f"[Rahul.ai] Identity logged at {path}")

rahul = RahulAI()

@dataclass
class Node:
    id: int
    mass: float = 1.0
    damping: float = 0.05
    freq: float = 1.0
    state: List[float] = field(default_factory=lambda:[0.0,0.0])
    def step(self, dt, force=0.0):
        k = (2*math.pi*self.freq)**2
        x, v = self.state
        a = (-self.damping*v - k*x + force)/self.mass
        v += a*dt; x += v*dt
        self.state = [x, v]

class GRRFPKernel:
    def __init__(self,N=6,coupling=0.8):
        self.nodes=[Node(i,freq=0.5+0.2*i) for i in range(N)]
        self.N=N; self.time=0.0
        self.adj=[[0]*N for _ in range(N)]
        for i in range(N):
            self.adj[i][(i+1)%N]=coupling; self.adj[i][(i-1)%N]=coupling
    def step(self,dt,imp=[]):
        f=[0.0]*self.N
        xs=[n.state[0] for n in self.nodes]
        for i in range(self.N):
            s=sum(self.adj[i][j]*(xs[j]-xs[i]) for j in range(self.N))
            f[i]+=s
        for i,n in enumerate(self.nodes): n.step(dt,f[i])
        self.time+=dt

class Oscillator(Widget):
    def __init__(self,kernel,**kw):
        super().__init__(**kw); self.kernel=kernel
        self.bind(size=self.update_canvas,pos=self.update_canvas)
        Clock.schedule_interval(self.tick,0.02)
    def update_canvas(self,*_):
        self.canvas.clear()
        w,h=self.width,self.height; cx,cy=self.x,self.y+h/2
        xs=[n.state[0] for n in self.kernel.nodes]
        spacing=w/(len(xs)+1)
        with self.canvas:
            Color(0.05,0.05,0.05,1); Rectangle(pos=self.pos,size=self.size)
            Color(0.4,0.4,0.4,1); Line(points=[self.x,cy,self.x+w,cy])
            for i,v in enumerate(xs):
                px=self.x+(i+1)*spacing; py=cy+v*100
                Color(0.2,0.7,0.9,1); Line(points=[px,cy,px,py],width=2)
                Color(0.9,0.3,0.2,1); Line(circle=(px,py,6),width=1.5)
    def tick(self,dt):
        self.kernel.step(dt,[]); self.update_canvas()

class GHOSHLayout(BoxLayout):
    def __init__(self,**kw):
        super().__init__(orientation='vertical',**kw)
        self.kernel=GRRFPKernel(); self.osc=Oscillator(self.kernel,size_hint=(1,0.6))
        self.add_widget(self.osc)
        bar=BoxLayout(size_hint=(1,0.1))
        bar.add_widget(Button(text='Save Logs',on_release=self.save))
        self.add_widget(bar)
        self.note=TextInput(text='GHOSH ROBOTICS\n',size_hint=(1,0.3))
        self.add_widget(self.note)
        self.vml=[]
        rahul.log_identity()
    def save(self,*_):
        path=os.path.join(SAVE_DIR,'vml_records.csv')
        with open(path,'w') as f:
            f.write('time,node,displacement\n')
            for t,n in enumerate(self.kernel.nodes):
                f.write(f"{self.kernel.time:.4f},{n.id},{n.state[0]:.6f}\n")
        self.note.text+=f"Saved logs at {path}\n"
        print(f"[VML] Saved logs at {path}")

class GHOSHApp(App):
    def build(self):
        self.title="GHOSH ROBOTICS"
        return GHOSHLayout()

if __name__=="__main__":
    GHOSHApp().run()
