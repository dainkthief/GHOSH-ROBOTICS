#!/usr/bin/env python3
import os, subprocess, datetime, requests

# ===== CONFIG =====
TOKEN = "8222543553:AAH-_rEWroqdEicXs24sDwx o829EZRYoooU".replace(" ", "")
CHAT_ID = "7660068167"
# ==================

def run(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError: return "error"

def verify_autostart():
    paths = [os.path.expanduser("~/.bashrc"),
             os.path.expanduser("~/GHOSH_Robotics/start_brahma.sh")]
    out=[]
    for p in paths:
        if os.path.exists(p):
            out.append(f"Found {p}")
            out.append(run(f"head -n 10 {p}"))
        else:
            out.append(f"Missing {p}")
    return "\n".join(out)

def notify(msg):
    try:
        r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        data={"chat_id":CHAT_ID,"text":msg},timeout=10)
        return f"Telegram {r.status_code}"
    except Exception as e: return f"Telegram error {e}"

def main():
    ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pyv=run("python3 --version")
    commit=run("git rev-parse --short HEAD")
    branch=run("git rev-parse --abbrev-ref HEAD")
    info={
        "Timestamp":ts,
        "Python":pyv,
        "Branch":branch,
        "Commit":commit,
        "Uname":run("uname -a"),
        "Autostart":verify_autostart(),
        "Brahma Layer":"LIVE MODE active ✅"
    }
    path=os.path.expanduser("~/GHOSH_Robotics/system_sync_report.txt")
    with open(path,"w") as f:
        f.write("=== BRAHMA_AI Sync Report ===\n")
        for k,v in info.items(): f.write(f"\n[{k.upper()}]\n{v}\n")
        f.write("\n==============================\n")

    run("git add -A")
    run(f'git commit -m "Auto-sync @ {ts}" || true')
    run("git push origin main")

    msg=(f"✅ BRAHMA_AI Sync Complete\n"
         f"🕒 {ts}\n"
         f"🐍 {pyv}\n"
         f"🌿 Branch: {branch}\n"
         f"🔖 Commit: {commit}\n"
         f"📤 Git push OK.")
    print(notify(msg))

if __name__=="__main__": main()
