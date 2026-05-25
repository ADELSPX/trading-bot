#!/usr/bin/env python3
"""
مراقب الإشارات — Signal Watcher
════════════════════════════════
يفحص السعر كل 10 دقائق:
  ١. إذا دخل منطقة الدخول ← تنبيه فوري "تفعّلت الإشارة"
  ٢. إذا وصل الهدف الأول ← "تم تحقيق الهدف الأول ✅"
  ٣. إذا وصل الهدف الثاني ← "تم تحقيق الهدف الثاني ✅"
  ٤. إذا ضرب الوقف ← "🛑 تم تفعيل الوقف"
"""
import json, sys, os, urllib.request
import yfinance as yf

SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
POSITIONS_FILE = "/root/trading-bot/data/positions.json"
BRIDGE_URL = "http://localhost:7890"

def send_alert(data: dict) -> bool:
    """إرسال تنبيه فوري للتلغرام"""
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(BRIDGE_URL, data=body,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=3)
        return json.loads(resp.read()).get("status") == "sent"
    except Exception as e:
        print(f"❌ Bridge error: {e}")
        return False

def get_spx_price() -> float:
    """جلب سعر SPX الحالي"""
    spy = yf.download('SPY', period='1d', progress=False)
    return float(str(spy['Close'].values[-1]).strip('[]')) * 10

def check_signal():
    """فحص الإشارة النشطة"""
    if not os.path.exists(SIGNAL_FILE):
        return  # لا توجد إشارة
    
    with open(SIGNAL_FILE) as f:
        signal = json.load(f)
    
    stage = signal.get("stage", "pending")
    if stage == "closed":
        return
    
    price = get_spx_price()
    entry_low = signal["entry_zone"][0]
    entry_high = signal["entry_zone"][1]
    direction = signal["direction"]
    
    # ١. تفعيل الإشارة
    if stage == "pending" and entry_low <= price <= entry_high:
        signal["stage"] = "active"
        signal["entry_price_actual"] = price
        alert = {
            "type": "entry",
            "symbol": "SPX",
            "direction": direction.lower(),
            "entry": price,
            "target1": signal["target1"],
            "target2": signal["target2"],
            "stop": signal["stop_loss"],
            "suggestion": f"🚀 تفعّلت الإشارة! السعر دخل منطقة {entry_low:.0f}-{entry_high:.0f}",
            "contract": signal.get("contract", ""),
            "note": "⚡ ادخل الآن"
        }
        if send_alert(alert):
            print(f"✅ Signal ACTIVATED at {price:.0f}")
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(signal, f, indent=2)
        return
    
    # ٢. متابعة الصفقة النشطة
    if stage == "active":
        if direction == "PUT":
            if price <= signal["target2"]:
                signal["stage"] = "target2_hit"
                alert = {"type": "close", "symbol": "SPX", "direction": "put",
                         "pnl": f"هدفين محققين", "suggestion": "🏆 تم تحقيق الهدف الثاني!",
                         "note": "🎉 مبروك"}
                send_alert(alert)
            elif price <= signal["target1"]:
                signal["stage"] = "target1_hit"
                alert = {"type": "update", "symbol": "SPX", "direction": "put",
                         "pnl": f"هدف أول محقق", "suggestion": "✅ تم تحقيق الهدف الأول",
                         "note": "اغلق جزئي أو كمل"}
                send_alert(alert)
            elif price >= signal["stop_loss"]:
                signal["stage"] = "stopped"
                alert = {"type": "close", "symbol": "SPX", "direction": "put",
                         "pnl": f"خسارة", "suggestion": "🛑 تم تفعيل الوقف",
                         "note": "الصفقة انتهت"}
                send_alert(alert)
        else:  # CALL
            if price >= signal["target2"]:
                signal["stage"] = "target2_hit"
                alert = {"type": "close", "symbol": "SPX", "direction": "call",
                         "pnl": f"هدفين محققين", "suggestion": "🏆 تم تحقيق الهدف الثاني!",
                         "note": "🎉 مبروك"}
                send_alert(alert)
            elif price >= signal["target1"]:
                signal["stage"] = "target1_hit"
                alert = {"type": "update", "symbol": "SPX", "direction": "call",
                         "pnl": f"هدف أول محقق", "suggestion": "✅ تم تحقيق الهدف الأول",
                         "note": "اغلق جزئي أو كمل"}
                send_alert(alert)
            elif price <= signal["stop_loss"]:
                signal["stage"] = "stopped"
                alert = {"type": "close", "symbol": "SPX", "direction": "call",
                         "pnl": f"خسارة", "suggestion": "🛑 تم تفعيل الوقف",
                         "note": "الصفقة انتهت"}
                send_alert(alert)
        
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(signal, f, indent=2)

if __name__ == "__main__":
    check_signal()
