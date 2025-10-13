# ==========================================================
#  BRAHMAFUSED UNIVERSAL NODE  |  GRRFP + Termux Integration
#  Mode: Hibernation-Adaptive (non-API fallback)
# ==========================================================

import os, json, time, datetime, subprocess, pandas as pd, requests

# ---------- CONFIG ----------
BASE = "/sdcard/BrahmaFusion"
os.makedirs(BASE, exist_ok=True)

LOG_SENSOR = os.path.join(BASE, f"sensor_{time.strftime('%Y%m%d')}.csv")
LOG_COMPARE = os.path.join(BASE, "comparison_report.csv")
LOOP = 5

# Sensors — mark unavailable as False
SENSORS = {
    "light": True,
    "accelerometer": True,
    "gyroscope": True,
    "magnetic_field": False,
    "proximity": False,
    "pressure": False
}

# Telegram optional
BOT = ""
CHAT = ""

def telegram(msg):
    if BOT and CHAT:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                          data={"chat_id": CHAT, "text": msg})
        except Exception:
            pass


# ---------- SENSOR ----------
def read_sensor(name):
    if not SENSORS[name]:
        return "HIBERNATED"
    try:
        r = subprocess.run(["termux-sensor", "-s", name, "-n", "1"],
                           capture_output=True, text=True, timeout=3)
        data = json.loads(r.stdout)
        v = data[name]["values"]
        return round(sum(v)/len(v), 3) if isinstance(v, list) else v
    except Exception:
        return "NA"


# ---------- LOGGER ----------
def log_all():
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    vals = [read_sensor(x) for x in SENSORS]
    line = f"{ts}," + ",".join(map(str, vals)) + "\n"

    if not os.path.exists(LOG_SENSOR):
        open(LOG_SENSOR, "w").write("Time," + ",".join(SENSORS.keys()) + "\n")

    with open(LOG_SENSOR, "a") as f:
        f.write(line)

    print(line.strip())
    return dict(zip(SENSORS.keys(), vals))


# ---------- MARKET ----------
def load_market(path="/sdcard/market_feed.csv"):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


# ---------- DIFFERENTIAL ----------
def compare(sensor, market):
    out = {}
    limits = {"light": 400, "accelerometer": 0.2, "gyroscope": 0.3}

    for k, v in sensor.items():
        if v in ("NA", "HIBERNATED"):
            out[k] = v
            continue
        try:
            out[k] = f"HIGH:{v}" if float(v) > limits.get(k, 9999) else f"OK:{v}"
        except Exception:
            out[k] = "NA"

    if not market.empty:
        cur = market.iloc[-1].get("price", None)
        pre = market.iloc[-2].get("price", cur)
        if cur and pre:
            delta = round((cur - pre) / pre * 100, 2)
            out["market_move_%"] = delta
            out["market_state"] = "VOLATILE" if abs(delta) > 1 else "STABLE"
    else:
        out["market_state"] = "EMPTY"

    ts = datetime.datetime.now().strftime("%H:%M:%S")
    pd.DataFrame([{"Time": ts, **out}]).to_csv(
        LOG_COMPARE, mode="a", index=False, header=not os.path.exists(LOG_COMPARE)
    )
    print("→", out)
    return out


# ---------- MAIN ----------
def main():
    print("BRAHMAFUSED NODE ACTIVE  |  HIBERNATION MODE")
    while True:
        sens = log_all()
        mkt = load_market()
        rep = compare(sens, mkt)
        if any("HIGH" in v for v in rep.values()):
            msg = f"⚠ Alert {datetime.datetime.now().strftime('%H:%M:%S')}\n" + \
                  "\n".join(f"{k}:{v}" for k, v in rep.items() if "HIGH" in v)
            telegram(msg)
            print(msg)
        time.sleep(LOOP)


if __name__ == "__main__":
    main()
