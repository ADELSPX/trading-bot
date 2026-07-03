#!/usr/bin/env python3 -u
"""
مراقب مستمر — Live Watcher 🔴 + IB Gateway 🤖
يراقب السعر → ينفذ تلقائياً → يتابع الأهداف
"""
import json, os, time, sys, urllib.request, urllib.error
from datetime import datetime

SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
BRIDGE_URL = "http://localhost:7890"
CHECK_INTERVAL = 30  # ثانية (أطول لتجنب Rate Limit)
YFINANCE_TIMEOUT = 8  # تايم آوت لـ yfinance

# IB Gateway
IB_ENABLED = True
IB_HOST = "127.0.0.1"
IB_PORT = 4002
IB_CLIENT_ID = 100

# ملف تتبع الصفقات
TRADES_FILE = "/root/trading-bot/data/ib_trades.json"

# Cache السعر
_PRICE_CACHE = {"price": 0, "time": 0}
_PRICE_CACHE_TTL = 60  # ثانية (نادراً ما يتغير SPX بسرعة)


def log(msg: str):
    """طباعة مع طابع زمني"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def send_alert(data: dict) -> bool:
    """إرسال تنبيه تيليجرام"""
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(BRIDGE_URL, data=body,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=3)
        return json.loads(resp.read()).get("status") == "sent"
    except:
        return False


def fetch_spx_yf() -> float | None:
    """سعر SPX من yfinance"""
    try:
        import yfinance as yf
        spy = yf.download('SPY', period='1d', progress=False, timeout=YFINANCE_TIMEOUT)
        price = float(spy['Close'].iloc[-1, 0]) * 10
        return price if price > 0 else None
    except Exception as e:
        log(f"yfinance: {e}")
        return None


def fetch_spx_web() -> float | None:
    """سعر SPX من Google Finance عبر scraping خفيف"""
    try:
        # Google Finance
        url = "https://www.google.com/finance/quote/SPY:NYSEARCA"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=5)
        html = resp.read().decode()
        # div[data-last-price] or similar
        for line in html.split('\n'):
            if 'data-last-price' in line:
                # Extract price from attribute
                start = line.find('data-last-price="') + len('data-last-price="')
                end = line.find('"', start)
                price_str = line[start:end]
                return float(price_str) * 10 if price_str else None
        return None
    except Exception as e:
        log(f"web: {e}")
        return None


def fetch_spx_yahoo_json() -> float | None:
    """Yahoo Finance JSON (قد يتعرض لـ Rate Limit)"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1m"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"] * 10
    except:
        return None


def get_spx() -> float:
    """سعر SPX — مصدر متعدد مع Cache"""
    global _PRICE_CACHE
    now = time.time()

    # Cache حديث
    if now - _PRICE_CACHE["time"] < _PRICE_CACHE_TTL and _PRICE_CACHE["price"] > 0:
        return _PRICE_CACHE["price"]

    # مصدر 1: yfinance (الأسرع والأنظف)
    price = fetch_spx_yf()
    if price:
        _PRICE_CACHE = {"price": price, "time": now}
        return price

    # مصدر 2: Yahoo JSON (سريع)
    price = fetch_spx_yahoo_json()
    if price:
        _PRICE_CACHE = {"price": price, "time": now}
        return price

    # مصدر 3: Google Finance
    price = fetch_spx_web()
    if price:
        _PRICE_CACHE = {"price": price, "time": now}
        return price

    # مصدر 4: آخر سعر
    if _PRICE_CACHE["price"] > 0:
        return _PRICE_CACHE["price"]

    raise Exception("❌ جميع مصادر الأسعار فشلت")


def ib_execute(direction: str, strike: float, expiry: str,
               action: str = "BUY", quantity: int = 1) -> dict:
    """تنفيذ أمر على IB Gateway"""
    try:
        from ib_insync import IB, Option, MarketOrder
        
        ib = IB()
        ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=10)
        
        right = "C" if direction.upper() == "CALL" else "P"
        contract = Option("SPX", expiry, strike, right, "CBOE")
        qualified = ib.qualifyContracts(contract)
        
        if not qualified:
            details = ib.reqContractDetails(contract)
            if not details:
                ib.disconnect()
                return {"error": "❌ العقد غير صالح"}
            contract = details[0].contract
        
        order = MarketOrder(action, quantity)
        trade = ib.placeOrder(contract, order)
        ib.sleep(2)
        
        result = {
            "orderId": trade.order.orderId,
            "status": trade.orderStatus.status,
            "filled": trade.orderStatus.filled,
            "remaining": trade.orderStatus.remaining,
            "avgFillPrice": trade.orderStatus.avgFillPrice,
            "contract": str(contract),
            "action": action,
            "quantity": quantity,
            "timestamp": datetime.utcnow().isoformat()
        }
        ib.disconnect()
        return result
        
    except Exception as e:
        log(f"IB فشل: {e}")
        return {"error": f"❌ IB فشل: {e}"}


def save_trade(trade_data: dict):
    """حفظ الصفقة للمتابعة"""
    os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE) as f:
                trades = json.load(f)
        except:
            pass
    trades.append(trade_data)
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)


# ═══════════════════════════════════
# البداية
# ═══════════════════════════════════
log(f"🔴 Live Watcher + IB Gateway — كل {CHECK_INTERVAL} ثواني")
log(f"📡 منصة: Interactive Brokers (Paper) — DUR156031")

# جلب السعر الأولي
try:
    initial = get_spx()
    log(f"💰 السعر الحالي: SPX {initial:.0f}")
except:
    log("⚠️ لم نتمكن من جلب السعر الأولي")

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
    except Exception as e:
        log(f"⚠️ سعر فشل: {e}")
        time.sleep(CHECK_INTERVAL)
        continue

    entry_low = signal.get("entry_zone", [0, 0])[0]
    entry_high = signal.get("entry_zone", [0, 0])[1]
    direction = signal.get("direction", "PUT")
    strike = signal.get("strike", 0)
    expiry = signal.get("expiry", "")
    stop_loss = signal.get("stop_loss", 0)
    target1 = signal.get("target1", 0)
    target2 = signal.get("target2", 0)

    changed = False

    # ═══════════════════════════════════════
    # 1️⃣ تفعيل — السعر في منطقة الدخول
    # ═══════════════════════════════════════
    if stage == "pending":
        if entry_low <= price <= entry_high:
            signal["stage"] = "active"
            signal["entry_price_actual"] = price

            alert = {
                "type": "entry", "symbol": "SPX",
                "direction": direction.lower(),
                "entry": price,
                "target1": target1,
                "stop": stop_loss,
                "suggestion": f"🚀 تفعّلت! السعر {price:.0f} في المنطقة"
            }

            # تنفيذ على IB
            if IB_ENABLED and strike and expiry:
                log(f"🤖 تنفيذ {direction} {strike} {expiry} على IB...")
                ib_result = ib_execute(
                    direction=direction,
                    strike=strike,
                    expiry=expiry,
                    action="BUY",
                    quantity=1
                )
                if "error" not in ib_result:
                    msg = f"✅ أمر #{ib_result['orderId']} — {ib_result['status']}"
                    alert["ib_order"] = msg
                    signal["ib_order_id"] = ib_result["orderId"]
                    signal["ib_status"] = ib_result["status"]
                    save_trade({
                        "type": "entry", "price": price,
                        "strike": strike, "expiry": expiry,
                        "direction": direction, "ib_result": ib_result
                    })
                    log(f"✅ IB نفذ: {msg}")
                else:
                    alert["ib_error"] = ib_result["error"]
                    log(f"❌ IB: {ib_result['error']}")

            send_alert(alert)
            log(f"🚀 ACTIVATED @ {price:.0f}")
            changed = True
        else:
            # عرض الحالة كل 30 ثانية بدون سبام
            log(f"⏳ انتظار منطقة الدخول {entry_low:.0f}-{entry_high:.0f} | السعر {price:.0f}")

    # ═══════════════════════════════════════
    # 2️⃣ متابعة — PUT
    # ═══════════════════════════════════════
    elif stage == "active":
        if direction == "PUT":
            if price <= target2:
                signal["stage"] = "target2_hit"
                if IB_ENABLED:
                    ib_execute(direction, strike, expiry, "SELL", 1)
                send_alert({
                    "type": "close", "symbol": "SPX", "direction": "put",
                    "pnl": "هدفين", "suggestion": "🏆 الهدف الثاني تحقق!"
                })
                log(f"🏆 T2 @ {price:.0f}")
                changed = True
            elif price <= target1 and last_stage != "target1_hit":
                signal["stage"] = "target1_hit"
                send_alert({
                    "type": "update", "symbol": "SPX", "direction": "put",
                    "pnl": "هدف أول", "suggestion": "✅ الهدف الأول تحقق!"
                })
                log(f"✅ T1 @ {price:.0f}")
                changed = True
            elif price >= stop_loss:
                signal["stage"] = "stopped"
                if IB_ENABLED:
                    ib_execute(direction, strike, expiry, "SELL", 1)
                send_alert({
                    "type": "close", "symbol": "SPX", "direction": "put",
                    "pnl": "خسارة", "suggestion": "🛑 وقف خسارة!"
                })
                log(f"🛑 SL @ {price:.0f}")
                changed = True

        # ═══════════════════════════════════════
        # 3️⃣ متابعة — CALL
        # ═══════════════════════════════════════
        else:  # CALL
            if price >= target2:
                signal["stage"] = "target2_hit"
                if IB_ENABLED:
                    ib_execute(direction, strike, expiry, "SELL", 1)
                send_alert({
                    "type": "close", "symbol": "SPX", "direction": "call",
                    "pnl": "هدفين", "suggestion": "🏆 الهدف الثاني تحقق!"
                })
                log(f"🏆 T2 @ {price:.0f}")
                changed = True
            elif price >= target1 and last_stage != "target1_hit":
                signal["stage"] = "target1_hit"
                send_alert({
                    "type": "update", "symbol": "SPX", "direction": "call",
                    "pnl": "هدف أول", "suggestion": "✅ الهدف الأول تحقق!"
                })
                log(f"✅ T1 @ {price:.0f}")
                changed = True
            elif price <= stop_loss:
                signal["stage"] = "stopped"
                if IB_ENABLED:
                    ib_execute(direction, strike, expiry, "SELL", 1)
                send_alert({
                    "type": "close", "symbol": "SPX", "direction": "call",
                    "pnl": "خسارة", "suggestion": "🛑 وقف خسارة!"
                })
                log(f"🛑 SL @ {price:.0f}")
                changed = True

    if changed:
        signal["updated_at"] = datetime.now().isoformat()
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(signal, f, indent=2)
        log(f"💾 حالة الإشارة → {signal['stage']}")

    last_stage = signal["stage"]
    time.sleep(CHECK_INTERVAL)
