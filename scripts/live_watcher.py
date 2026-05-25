#!/usr/bin/env python3
"""
مراقب مستمر — Live Watcher 🔴
يراقب السعر كل 5 ثواني بدل 10 دقائق
يشغّل كخدمة خلفية 24/7
"""
import json, os, time, urllib.request
import yfinance as yf
from datetime import datetime

SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
BRIDGE_URL = "http://localhost:7890"
CHECK_INTERVAL = 5  # ثواني

def send_alert(data: dict) -> bool:
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(BRIDGE_URL, data=body,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=3)
        return json.loads(resp.read()).get("status") == "sent"
    except:
        return False

def get_spx() -> float:
    spy = yf.download('SPY', period='1d', progress=False)
    close_vals = spy['Close'].values
    return float(close_vals[-1]) * 10

print(f"🔴 Live Watcher — كل {CHECK_INTERVAL} ثواني")
print(f"📡 {datetime.now().strftime('%H:%M:%S')}")

last_stage = None
while True:
    if not os.path.exists(SIGNAL_FILE):
        time.sleep(CHECK_INTERVAL)
        continue

    with open(SIGNAL_FILE) as f:
        signal = json.load(f)

    stage = signal.get("stage", "pending")
    if stage == "closed":
        time.sleep(CHECK_INTERVAL)
        continue

    try:
        price = get_spx()
    except:
        time.sleep(CHECK_INTERVAL)
        continue

    entry_low = signal["entry_zone"][0]
    entry_high = signal["entry_zone"][1]
    direction = signal["direction"]

    changed = False

    # تفعيل
    if stage == "pending" and entry_low <= price <= entry_high:
        signal["stage"] = "active"
        signal["entry_price_actual"] = price
        alert = {"type": "entry", "symbol": "SPX", "direction": direction.lower(),
                 "entry": price, "target1": signal["target1"], "stop": signal["stop_loss"],
                 "suggestion": f"🚀 تفعّلت! ادخل الآن — السعر {price:.0f} في المنطقة"}
        send_alert(alert)
        print(f"🚀 ACTIVATED @ {price:.0f} {datetime.now().strftime('%H:%M:%S')}")
        changed = True

    # متابعة
    elif stage == "active":
        if direction == "PUT":
            if price <= signal["target2"]:
                signal["stage"] = "target2_hit"
                send_alert({"type": "close", "symbol": "SPX", "direction": "put",
                           "pnl": "هدفين", "suggestion": "🏆 الهدف الثاني تحقق!"})
                changed = True
            elif price <= signal["target1"] and last_stage != "target1_hit":
                signal["stage"] = "target1_hit"
                send_alert({"type": "update", "symbol": "SPX", "direction": "put",
                           "pnl": "هدف أول", "suggestion": "✅ الهدف الأول تحقق!"})
                print(f"✅ T1 @ {price:.0f}")
                changed = True
            elif price >= signal["stop_loss"]:
                signal["stage"] = "stopped"
                send_alert({"type": "close", "symbol": "SPX", "direction": "put",
                           "pnl": "خسارة", "suggestion": "🛑 وقف خسارة!"})
                changed = True
        else:  # CALL
            if price >= signal["target2"]:
                signal["stage"] = "target2_hit"
                send_alert({"type": "close", "symbol": "SPX", "direction": "call",
                           "pnl": "هدفين", "suggestion": "🏆 الهدف الثاني تحقق!"})
                changed = True
            elif price >= signal["target1"] and last_stage != "target1_hit":
                signal["stage"] = "target1_hit"
                send_alert({"type": "update", "symbol": "SPX", "direction": "call",
                           "pnl": "هدف أول", "suggestion": "✅ الهدف الأول تحقق!"})
                changed = True
            elif price <= signal["stop_loss"]:
                signal["stage"] = "stopped"
                send_alert({"type": "close", "symbol": "SPX", "direction": "call",
                           "pnl": "خسارة", "suggestion": "🛑 وقف خسارة!"})
                changed = True

    if changed:
        signal["updated_at"] = datetime.now().isoformat()
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(signal, f, indent=2)

    last_stage = signal["stage"]
    time.sleep(CHECK_INTERVAL)
