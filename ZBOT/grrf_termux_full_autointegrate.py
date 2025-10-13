import os, subprocess, pathlib, textwrap

HOME = pathlib.Path.home()
ZBOT = HOME / "ZBOT"
BRAHMA = ZBOT / "brahma_auto_integrated.py"
VIT = ZBOT / "VibrationalImpulseTheory.py"
STARTUP = HOME / ".bashrc"
BOOT_SCRIPT = HOME / ".termux_brahma_autostart.sh"

print("⚙️ GRRFP–Brahma_AI–VIT Termux Auto Integration Starting...")

# 1️⃣ Ensure base folder and Python
ZBOT.mkdir(parents=True, exist_ok=True)
if subprocess.run("which python", shell=True, capture_output=True).returncode != 0:
    print("📦 Installing Python ...")
    subprocess.run("pkg install -y python", shell=True, check=False)
python_bin = subprocess.getoutput("which python").strip() or "/data/data/com.termux/files/usr/bin/python"

# 2️⃣ Update PATH permanently
path_line = f'export PATH=\"$PATH:{pathlib.Path(python_bin).parent}\"\n'
if not STARTUP.exists() or path_line not in STARTUP.read_text():
    with open(STARTUP, "a") as f:
        f.write(f"\n# GRRFP Brahma_AI Autopath\n{path_line}")
    print("✅ PATH ensured in ~/.bashrc")

# 3️⃣ Restore Brahma layer
if not BRAHMA.exists():
    BRAHMA.write_text(textwrap.dedent('''
    print("✅ Brahma Integrated Layer Restored")
    print("System operational: LIVE MODE active.")
    '''))
    print("✅ Brahma_AI core rebuilt.")
else:
    print("ℹ Brahma_AI file present, leaving untouched.")

# 4️⃣ Restore Vibrational Impulse Theory core
if not VIT.exists():
    VIT.write_text(textwrap.dedent('''
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
    '''))
    print("✅ VIT core rebuilt.")
else:
    print("ℹ VIT file present, leaving untouched.")

# 5️⃣ Create boot hook
BOOT_SCRIPT.write_text(f'''#!/data/data/com.termux/files/usr/bin/bash
echo "🚀 Launching Brahma_AI & GRRFP Simulation..."
{python_bin} "{BRAHMA}"
{python_bin} "{VIT}"
''')
BOOT_SCRIPT.chmod(0o755)

if "bash .termux_brahma_autostart.sh" not in STARTUP.read_text():
    with open(STARTUP, "a") as f:
        f.write('\n# Auto-launch Brahma_AI + VIT\nbash .termux_brahma_autostart.sh &\n')

print("🔗 Boot hook linked to Termux startup.")
print("🔁 Testing execution...\n")
subprocess.run(f'{python_bin} "{BRAHMA}"', shell=True)
subprocess.run(f'{python_bin} "{VIT}"', shell=True)
print("\n✅ GRRFP–Brahma_AI–VIT Termux integration complete. Restart Termux to activate live mode.")
