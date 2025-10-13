#!/usr/bin/env python3
"""
grrf_compiled.py
Single-file operational integration for GRRFP + RKC + Rahul.ai
Purpose: compile identity, thesis, manifesto, and VIT engine into one Termux-friendly app.

Features:
- Loads local manifesto/thesis docx if available (optional).
- Identity layer (Rahul.ai) with JSON log.
- Vibrational Impulse Engine (pure-Python with optional numpy).
- VML (Vibrational Memory Layer) CSV logging.
- NuCell Reactor impulse scheduling.
- Simple CLI control and run modes.
- Safe fallbacks if numpy or python-docx are missing.

Usage:
    python grrf_compiled.py --duration 8 --dt 0.002 --save
"""

from __future__ import annotations
import os, sys, time, math, json, argparse
from dataclasses import dataclass, field
from typing import List, Tuple

# ---------------------------
# Optional imports with fallbacks
# ---------------------------
try:
    import numpy as np
    NP = True
except Exception:
    NP = False

try:
    from docx import Document
    DOCX = True
except Exception:
    DOCX = False

# ---------------------------
# Utility functions
# ---------------------------
def safe_makedirs(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass

def now_ts():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

# ---------------------------
# Identity Layer (Rahul.ai)
# ---------------------------
class RahulAI:
    def __init__(self):
        self.identity = {
            "name": "Rahul.ai",
            "framework": "GRRFP + RKC",
            "version": "1.0-LIVE",
            "mode": "operational",
            "started_at": now_ts()
        }
    def log_identity(self, path: str = "rahul_identity.json"):
        safe_makedirs(os.path.dirname(path) or ".")
        with open(path, "w") as f:
            json.dump(self.identity, f, indent=2)
        print(f"[Rahul.ai] Identity logged to {path}")
    def status(self):
        return f"{self.identity['name']} active under {self.identity['framework']}"

rahul = RahulAI()

# ---------------------------
# Document loader (manifesto/thesis)
# ---------------------------
def load_docx_text(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    if not DOCX:
        # fallback: try naive binary-to-text extraction for quick preview
        try:
            with open(path, "rb") as f:
                raw = f.read()
            # crude: extract ASCII/UTF-8 sequences > 40 chars
            parts = []
            cur = []
            for b in raw:
                if 32 <= b <= 126:
                    cur.append(chr(b))
                else:
                    if len(cur) > 40:
                        parts.append("".join(cur))
                    cur = []
            return "\n\n".join(parts[:8]) or ""
        except Exception:
            return ""
    try:
        doc = Document(path)
        texts = []
        for p in doc.paragraphs:
            t = p.text.strip()
            if t:
                texts.append(t)
        return "\n".join(texts)
    except Exception:
        return ""

def save_text_if_found(src_path: str, out_path: str):
    txt = load_docx_text(src_path)
    if txt:
        safe_makedirs(os.path.dirname(out_path) or ".")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"[Docs] Extracted text from {src_path} -> {out_path}")
        return True
    else:
        print(f"[Docs] No readable content at {src_path} or docx parser missing.")
        return False

# ---------------------------
# Numerical compatibility layer
# If numpy exists we use it. Otherwise use lists and math.
# ---------------------------
if NP:
    def zeros(n):
        return np.zeros(n)
    def array(x):
        return np.array(x)
    def dot(A, x):
        return A.dot(x)
else:
    def zeros(n):
        return [0.0] * n
    def array(x):
        return x[:] if isinstance(x, list) else list(x)
    def dot(A, x):
        # A is list of lists (NxN), x is list (N)
        N = len(x)
        out = [0.0] * N
        for i in range(N):
            s = 0.0
            row = A[i]
            for j in range(N):
                s += row[j] * x[j]
            out[i] = s
        return out

# ---------------------------
# Node, Network, Reactor, VML
# ---------------------------
@dataclass
class Node:
    id: int
    mass: float = 1.0
    damping: float = 0.05
    natural_freq: float = 2 * math.pi * 1.0  # rad/s
    state: List[float] = field(default_factory=lambda: [0.0, 0.0])  # [x, v]

    def acceleration(self, x, v, coupling_force=0.0, external_force=0.0):
        k = self.mass * (self.natural_freq ** 2)
        return ( - self.damping * v - k * x + coupling_force + external_force ) / self.mass

class Network:
    def __init__(self, nodes: List[Node], adjacency):
        self.nodes = nodes
        self.N = len(nodes)
        self.adjacency = adjacency  # NxN matrix (list of lists) or numpy array

    def _states_arrays(self):
        xs = [n.state[0] for n in self.nodes]
        vs = [n.state[1] for n in self.nodes]
        return xs, vs

    def step_rk4(self, dt: float, external_forces=None):
        if external_forces is None:
            ext = zeros(self.N)
        else:
            ext = external_forces
        xs, vs = self._states_arrays()
        # coupling = adjacency @ xs - sum_row * xs
        if NP:
            xs_arr = np.array(xs)
            coupling = self.adjacency.dot(xs_arr) - np.sum(self.adjacency, axis=1) * xs_arr
            coupling = coupling.tolist()
        else:
            coupling = dot(self.adjacency, xs)
            # subtract row-sum * xs
            row_sums = [sum(row) for row in self.adjacency]
            coupling = [ coupling[i] - row_sums[i] * xs[i] for i in range(self.N) ]
        # helper to compute derivatives vector
        def deriv(states_flat):
            s = list(states_flat)
            s_pairs = [ (s[2*i], s[2*i+1]) for i in range(self.N) ]
            dxdt = [v for (_, v) in s_pairs]
            dvdt = []
            for i, (x, v) in enumerate(s_pairs):
                a = self.nodes[i].acceleration(x, v, coupling_force=coupling[i], external_force=(ext[i] if i < len(ext) else 0.0))
                dvdt.append(a)
            out = []
            for i in range(self.N):
                out.append(dxdt[i]); out.append(dvdt[i])
            return out
        # flatten y0
        y0 = []
        for i in range(self.N):
            y0.append(xs[i]); y0.append(vs[i])
        # RK4 steps (pure python)
        k1 = deriv(y0)
        yk2 = [ y0[i] + 0.5 * dt * k1[i] for i in range(len(y0)) ]
        k2 = deriv(yk2)
        yk3 = [ y0[i] + 0.5 * dt * k2[i] for i in range(len(y0)) ]
        k3 = deriv(yk3)
        yk4 = [ y0[i] + dt * k3[i] for i in range(len(y0)) ]
        k4 = deriv(yk4)
        y_next = [ y0[i] + (dt/6.0)*(k1[i] + 2*k2[i] + 2*k3[i] + k4[i]) for i in range(len(y0)) ]
        # write back
        for i in range(self.N):
            self.nodes[i].state[0] = y_next[2*i]
            self.nodes[i].state[1] = y_next[2*i+1]

class NuCellReactor:
    def __init__(self):
        self.schedule: List[Tuple[float,int,float]] = []
    def add_impulse(self, t: float, node_id: int, amplitude: float):
        self.schedule.append((t, node_id, amplitude))
    def external_forces(self, t: float, N: int):
        forces = [0.0]*N
        for (ti, nid, amp) in self.schedule:
            dt = t - ti
            if abs(dt) < 0.05:
                val = amp * math.exp(- (dt ** 2) / (2 * (0.01 ** 2)))
                if 0 <= nid < N:
                    forces[nid] += val
        return forces

class VML:
    def __init__(self, sampling_dt: float = 0.001):
        self.sampling_dt = sampling_dt
        self.records: List[Tuple[float,int,float]] = []
    def record(self, t: float, nodes: List[Node]):
        for n in nodes:
            self.records.append((t, n.id, float(n.state[0])))
    def save_csv(self, path: str = "vml_records.csv"):
        safe_makedirs(os.path.dirname(path) or ".")
        with open(path, "w", encoding="utf-8") as f:
            f.write("time,node,displacement\n")
            for (t,nid,x) in self.records:
                f.write(f"{t:.6f},{nid},{x:.9f}\n")
        print(f"[VML] Saved {len(self.records)} records to {path}")

# ---------------------------
# High-level app controller
# ---------------------------
def build_default_network(N=6, coupling_k=0.8):
    nodes = []
    for i in range(N):
        nf = 2 * math.pi * (0.5 + 0.2 * i)  # rad/s
        nodes.append(Node(id=i, mass=1.0, damping=0.08, natural_freq=nf))
    # adjacency ring
    if NP:
        adj = np.zeros((N,N))
        for i in range(N):
            adj[i,(i+1)%N] = coupling_k
            adj[i,(i-1)%N] = coupling_k
    else:
        adj = [ [0.0]*N for _ in range(N) ]
        for i in range(N):
            adj[i][(i+1)%N] = coupling_k
            adj[i][(i-1)%N] = coupling_k
    return Network(nodes, adj)

def run_compiled_live(duration=8.0, dt=0.002, autosave=True, verbose=True):
    net = build_default_network()
    vml = VML(sampling_dt=dt)
    reactor = NuCellReactor()
    # schedule demo impulses
    reactor.add_impulse(0.2, 0, 5.0)
    reactor.add_impulse(1.0, 3, 3.5)

    steps = int(max(1, duration / dt))
    t = 0.0
    if verbose:
        print(f"[GRRFP] Universal Compilation — Live Resonance Start | duration={duration}s dt={dt}s")
    for s in range(steps):
        ext = reactor.external_forces(t, net.N)
        net.step_rk4(dt, external_forces=ext)
        if s % max(1, int(0.005/dt)) == 0:
            vml.record(t, net.nodes)
        t += dt
        if verbose and (s % max(1, int(0.5/dt)) == 0):
            n0 = net.nodes[0].state[0]
            print(f"t={t:.3f}s | node0={n0:.6f}")
    if autosave:
        vml.save_csv()
    if verbose:
        print("[GRRFP] Resonance complete. Universal state logged.")
    return net, vml

# ---------------------------
# CLI and orchestration
# ---------------------------
def cli_main():
    parser = argparse.ArgumentParser(prog="grrf_compiled", description="GRRFP Universal Compilation Runner")
    parser.add_argument("--duration", type=float, default=8.0, help="duration seconds")
    parser.add_argument("--dt", type=float, default=0.002, help="time step")
    parser.add_argument("--save", action="store_true", help="save extracted docs if found")
    parser.add_argument("--manifesto", default="I_Am_Rahul_ai_Manifesto.docx", help="manifesto docx path")
    parser.add_argument("--thesis", default="PhD Theses Paper by Rahul_ai.docx", help="thesis docx path")
    args = parser.parse_args()

    print("[INIT] Starting GRRFP Universal Compilation (single-file app)")
    print("[INIT] Rahul.ai status:", rahul.status())
    rahul.log_identity()

    # attempt to extract docs
    if args.save:
        save_text_if_found(args.manifesto, "manifesto_text.txt")
        save_text_if_found(args.thesis, "thesis_text.txt")
    else:
        print("[Docs] pass --save to extract manifesto/thesis if docx parser available or fallback extraction.")

    # run live engine
    try:
        net, vml = run_compiled_live(duration=args.duration, dt=args.dt, autosave=True, verbose=True)
    except KeyboardInterrupt:
        print("[GRRFP] Interrupted by user. Saving what we have.")
        # attempt to save partial VML if present
        try:
            vml.save_csv()
        except Exception:
            pass
        sys.exit(0)

    # final state summary
    try:
        final_states = [ round(n.state[0], 9) for n in net.nodes ]
        print("[FINAL] node displacements:", final_states)
    except Exception:
        pass
    print("[DONE] GRRFP Universal Compilation run finished.")

# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    cli_main()
