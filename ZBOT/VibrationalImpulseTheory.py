
import math, numpy as np, matplotlib.pyplot as plt
print("🔬 Vibrational Impulse Theory (VIT) simulation running...")
t = np.linspace(0, 5, 1000)
x = np.sin(2*math.pi*2*t)*np.exp(-0.1*t)
plt.plot(t, x)
plt.title("Vibrational Impulse Damped Sine")
plt.xlabel("Time (s)")
plt.ylabel("Amplitude")
plt.tight_layout()
plt.savefig("vit_output.png")
print("✅ Simulation complete → vit_output.png saved.")
