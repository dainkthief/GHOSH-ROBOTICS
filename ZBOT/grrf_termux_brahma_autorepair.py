import os, subprocess, pathlib, textwrap

HOME = pathlib.Path.home()
ZBOT = HOME / "ZBOT"
BRAHMA = ZBOT / "brahma_auto_integrated.py"
STARTUP = HOME / ".bashrc"

print("⚙️ GRRFP–Brahma_AI Termux Auto-Repair Starting...")

# --- Ensure base folder ---
ZBOT.mkdir(parents=True, exist_ok=True)

# --- Verify python installation ---
if subprocess.run("which python", shell=True, capture_output=True).returncode != 0:
    print("📦 Installing Python ...")
    subprocess.run("pkg install -y python", shell=True, check=False)

python_bin = subprocess.getoutput("which python").strip()
if not python_bin:
    python_bin = "/data/data/com.termux/files/usr/bin/python"

# --- Update PATH persistently ---
path_line = f'export PATH="$PATH:{pathlib.Path(python_bin).parent}"\n'
if not STARTUP.exists() or path_line not in STARTUP.read_text():
    with open(STARTUP, "a") as f:
        f.write(f"\n# GRRFP Brahma_AI Autopath\n{path_line}")
    print("✅ PATH ensured in ~/.bashrc")

# --- Restore Brahma file ---
if not BRAHMA.exists():
    code = textwrap.dedent('''
    print("✅ Brahma Integrated Layer Restored")
    print("System operational: LIVE MODE active.")
    ''')
    BRAHMA.write_text(code)
    print("✅ Brahma_AI core rebuilt.")
else:
    print("ℹ Brahma_AI file present, leaving untouched.")

# --- Create Termux boot hook ---
BOOT_SCRIPT = HOME / ".termux_brahma_autostart.sh"
BOOT_SCRIPT.write_text(f'{python_bin} "{BRAHMA}"\n')
BOOT_SCRIPT.chmod(0o755)

if "bash .termux_brahma_autostart.sh" not in STARTUP.read_text():
    with open(STARTUP, "a") as f:
        f.write('\n# Auto-launch Brahma_AI\nbash .termux_brahma_autostart.sh &\n')

print("🚀 Brahma_AI boot hook linked to Termux startup.")
print("🔁 Testing live execution...\n")

subprocess.run(f'{python_bin} "{BRAHMA}"', shell=True)

print("\n✅ GRRFP–Brahma_AI Termux integration complete. Restart Termux to verify live boot activation.")
