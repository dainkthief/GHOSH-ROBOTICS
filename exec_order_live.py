#!/data/data/com.termux/files/usr/bin/python3
import os, sys, json, time, math, requests

# --- Configuration ---
API_KEY = os.getenv("KITE_API_KEY", "1u9tjt5sxp6ewroe")
ACCESS_FILE = os.path.expanduser("~/GHOSH_TRADING/access_token.json")
API_BASE = "https://api.kite.trade"
HEADERS = {"X-Kite-Version": "3"}

EXCHANGE = "NSE"
SYMBOL = "BANKBARODA"
PRODUCT = "MIS"
ORDER_TYPE = "MARKET"

LEVERAGE = 3
SMA_WINDOW = 5
TREND_THRESHOLD = 0.0005     # 0.05%
TARGET_PROFIT = 0.0125       # 1.25%
POLL_INTERVAL = 3            # seconds
MAX_QTY = 100                # safety cap

LIVE_MODE = os.getenv("LIVE_MODE") == "1"
LIVE_CONFIRM = os.getenv("LIVE_CONFIRM") == "I_ACCEPT_RISK"

# --- Telegram Alerts ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    """Send Telegram message if credentials set."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception:
        pass

# --- Helpers ---

def load_token():
    with open(ACCESS_FILE) as f:
        return json.load(f)["access_token"]

def auth_headers():
    t = load_token()
    h = HEADERS.copy()
    h["Authorization"] = f"token {API_KEY}:{t}"
    return h

def ltp_symbol():
    """Fetch live last traded price for the symbol."""
    try:
        r = requests.get(f"{API_BASE}/quote/ltp", params={"i": f"{EXCHANGE}:{SYMBOL}"}, headers=auth_headers())
        j = r.json()
        key = f"{EXCHANGE}:{SYMBOL}"
        if j.get("status") != "success" or key not in j.get("data", {}):
            return None
        return float(j["data"][key]["last_price"])
    except Exception as e:
        print("ltp_symbol error:", e)
        send_telegram(f"ERROR fetching LTP {SYMBOL}")
        return None

def compute_order_qty(cash, price, leverage=LEVERAGE):
    """Compute order quantity based on cash and leverage."""
    if price <= 0:
        return 0
    qty = int((cash * leverage) // price)
    if qty <= 0:
        return 0
    return min(qty, MAX_QTY)

def place_market(side, qty):
    """Place a market order (paper mode if LIVE_MODE off)."""
    if qty <= 0:
        print("qty 0, skipping order")
        return None
    if not LIVE_MODE or not LIVE_CONFIRM:
        msg = f"[SIMULATED] {side} {qty} {SYMBOL}"
        print("Paper mode -", msg)
        send_telegram(msg)
        return {"status": "paper", "data": {"order_id": "SIM"}}
    payload = {
        "exchange": EXCHANGE,
        "tradingsymbol": SYMBOL,
        "transaction_type": side,
        "order_type": ORDER_TYPE,
        "quantity": qty,
        "product": PRODUCT,
        "validity": "DAY",
    }
    r = requests.post(f"{API_BASE}/orders/regular", headers=auth_headers(), data=payload)
    try:
        j = r.json()
        send_telegram(f"ORDER {side} {qty} {SYMBOL} → {j.get('status')}")
        return j
    except Exception:
        print("place_order raw:", r.text)
        send_telegram(f"ERROR placing order {side} {qty} {SYMBOL}")
        return None

def get_live_cash():
    """Return available cash balance."""
    try:
        r = requests.get(f"{API_BASE}/user/margins", headers=auth_headers())
        j = r.json()
        eq = j["data"]["equity"]
        return float(eq.get("available", {}).get("live_balance", eq.get("available", {}).get("cash", 0)))
    except Exception:
        send_telegram("ERROR fetching cash balance")
        return 0.0

def monitor_and_exit(avg_entry_price, entry_qty, entry_side):
    """Watch price until profit target reached, then exit."""
    target = avg_entry_price * (1 + TARGET_PROFIT) if entry_side == "BUY" else avg_entry_price * (1 - TARGET_PROFIT)
    print(f"monitoring {entry_side} qty={entry_qty} entry={avg_entry_price:.2f} target={target:.2f}")
    send_telegram(f"MONITOR {entry_side} {SYMBOL} target={target:.2f}")
    while True:
        time.sleep(POLL_INTERVAL)
        price = ltp_symbol()
        if not price:
            continue
        if entry_side == "BUY" and price >= target:
            msg = f"TARGET HIT {SYMBOL} {entry_side} exit @ {price:.2f}"
            print(msg)
            send_telegram(msg)
            return place_market("SELL", entry_qty)
        if entry_side == "SELL" and price <= target:
            msg = f"TARGET HIT {SYMBOL} {entry_side} exit @ {price:.2f}"
            print(msg)
            send_telegram(msg)
            return place_market("BUY", entry_qty)
        print(f"LTP {price:.2f}, waiting for target {target:.2f}")

# --- Main trading loop ---

def trade_loop(max_trades=None):
    ltp_samples = []
    trades_done = 0
    while True:
        cash = get_live_cash()
        if cash <= 0:
            print("No cash available:", cash)
            send_telegram("NO CASH available, waiting...")
            time.sleep(30)
            continue

        price = ltp_symbol()
        if not price:
            time.sleep(POLL_INTERVAL)
            continue

        ltp_samples.append(price)
        if len(ltp_samples) > SMA_WINDOW:
            ltp_samples.pop(0)

        if len(ltp_samples) < SMA_WINDOW:
            print(f"Collecting samples {len(ltp_samples)}/{SMA_WINDOW}")
            time.sleep(POLL_INTERVAL)
            continue

        sma = sum(ltp_samples) / len(ltp_samples)
        print(f"LTP={price:.2f} SMA={sma:.2f}")

        # Decide direction
        if price > sma * (1 + TREND_THRESHOLD):
            side = "BUY"
        elif price < sma * (1 - TREND_THRESHOLD):
            side = "SELL"
        else:
            print("No clear trend; waiting...")
            time.sleep(POLL_INTERVAL)
            continue

        qty = compute_order_qty(cash, price)
        if qty == 0:
            print("Computed qty 0; waiting...")
            send_telegram("QTY 0 computed; waiting...")
            time.sleep(10)
            continue

        print(f"Entry {side} {qty} @ {price:.2f}")
        send_telegram(f"ENTRY {side} {qty} @ {price:.2f}")

        order = place_market(side, qty)
        print("Order:", order)

        entry_price = price
        monitor_and_exit(entry_price, qty, side)

        trades_done += 1
        if max_trades and trades_done >= max_trades:
            print("Max trades reached.")
            send_telegram("Max trades reached; stopping loop.")
            break
        time.sleep(2)

# --- Run if called directly ---
if __name__ == "__main__":
    print("Starting auto-trade loop for", SYMBOL)
    send_telegram(f"Auto-trade loop started for {SYMBOL}")
    trade_loop()
