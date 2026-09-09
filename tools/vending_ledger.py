#!/usr/bin/env python3
"""
vending_ledger.py — دفتر صفقات Paper (Vending-Bench للتداول — المرحلة 1)
===============================================================
كل إشارة Gamma حقيقية = صفقة Paper مسجلة، ونراقب مصيرها آلياً:
هل التزمت بالـ stop/target؟ هل القواعد مربحة فعلاً؟

الأوامر:
  python3 tools/vending_ledger.py open      # يفتح صفقات للإشارات الجديدة (من signal_history)
  python3 tools/vending_ledger.py update    # يحدّث الصفقات المفتوحة بأسعار اليوم
  python3 tools/vending_ledger.py report    # ملخص الحالة + إحصاء الالتزام
  python3 tools/vending_ledger.py close --id N --reason expired|manual

ملاحظة: صفر LLM — بايثون + yfinance فقط. Paper فقط بلا مال حقيقي.
"""
import json, os, sys, datetime, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
LEDGER = os.path.join(DATA, "vending_trades.json")
SIG_HIST = os.path.join(DATA, "signal_history.json")

FEE = 1.0          # رسوم لكل صفقة ($)
SLIPPAGE = 0.0002  # انزلاق 0.02%
MAX_DAYS = 10      # أفق أقصى للصفقة (أيام عمل) ثم إغلاق بسعر السوق
START_CAPITAL = 100000.0  # رأس مال وهمي

def load_ledger():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER))
    return {"capital": START_CAPITAL, "trades": [], "closed": []}

def save_ledger(led):
    json.dump(led, open(LEDGER, "w"), ensure_ascii=False, indent=1)

def norm_side(s):
    s = (s or "").upper().replace("🟢", "").replace("🔴", "").strip()
    if "CALL" in s:
        return "CALL"
    if "PUT" in s:
        return "PUT"
    return s

def yf_symbol(sym):
    """تحويل الرمز لصيغة yfinance (SPX → ^SPX)."""
    s = sym.upper()
    if s in ("SPX", "SP500"):
        return "^SPX"
    return s

def fetch_price(symbol, retries=3):
    """سعر آخر إغلاق عبر yfinance (مع إعادة محاولة)."""
    import yfinance as yf
    for i in range(retries):
        try:
            t = yf.Ticker(yf_symbol(symbol))
            h = t.history(period="5d")
            if h is not None and len(h) > 0:
                return float(h["Close"].iloc[-1])
        except Exception:
            pass
        time.sleep(2)
    return None

def cmd_open():
    led = load_ledger()
    hist = json.load(open(SIG_HIST)) if os.path.exists(SIG_HIST) else []
    existing = {(t.get("symbol"), t.get("entry_time") or t.get("time")) for t in led["trades"] + led["closed"]}
    opened = 0
    for sig in hist:
        t = sig.get("time") or sig.get("entry_time") or ""
        sym = sig.get("symbol")
        side = norm_side(sig.get("direction") or sig.get("signal"))
        entry = sig.get("price")
        if not sym or not side or not entry:
            continue
        # تجاهل المكرر (نفس الرمز خلال 6 ساعات)
        recent = [x for x in led["trades"] if x.get("symbol") == sym and
                  (datetime.datetime.fromisoformat(x["opened_at"].replace("Z", "+00:00")) if x.get("opened_at") else datetime.datetime.min)]
        dup = False
        for x in led["trades"] + led["closed"]:
            if x.get("symbol") == sym and x.get("side") == side and (x.get("opened_at") or "").startswith(t[:13]):
                dup = True
                break
        if dup:
            continue
        trade = {
            "symbol": sym, "side": side,
            "entry": entry,
            "stop": sig.get("stop"),
            "target1": sig.get("target1"),
            "target2": sig.get("target2"),
            "opened_at": t or datetime.datetime.utcnow().isoformat() + "Z",
            "status": "open",
            "qty": 100,  # وحدات ثابتة (خيار SPX تقريباً)
        }
        # إن لم توجد أهداف — احسب من السعر (CALL: +1% هدف، -0.8% وقف | PUT عكسها)
        if not trade["stop"] or not trade["target1"]:
            if side == "CALL":
                trade["target1"] = entry * 1.01
                trade["stop"] = entry * 0.992
            else:
                trade["target1"] = entry * 0.99
                trade["stop"] = entry * 1.008
        led["trades"].append(trade)
        opened += 1
    save_ledger(led)
    print(f"✅ فتح {opened} صفقة جديدة — إجمالي مفتوحة: {len(led['trades'])}")

def cmd_update():
    led = load_ledger()
    still_open = []
    closed_now = []
    for t in led["trades"]:
        px = fetch_price(t["symbol"])
        if px is None:
            still_open.append(t)
            print(f"⚠️ {t['symbol']}: ما جاب سعر")
            continue
        side = t["side"]
        # تطبيق الانزلاق
        px_slip = px * (1 - SLIPPAGE) if side == "CALL" else px * (1 + SLIPPAGE)
        stop = t["stop"]; tgt = t["target1"]
        result = None
        # CALL: ربح إذا السعر >= هدف، خسارة إذا <= وقف
        if side == "CALL":
            if px_slip >= tgt:
                result = "win"
            elif px_slip <= stop:
                result = "loss"
        else:
            if px_slip <= tgt:
                result = "win"
            elif px_slip >= stop:
                result = "loss"
        # انتهاء الأفق الزمني
        try:
            opened = datetime.datetime.fromisoformat(t["opened_at"].replace("Z", "+00:00"))
            age_days = (datetime.datetime.utcnow() - opened).days
        except Exception:
            age_days = 0
        if result is None and age_days >= MAX_DAYS:
            # إغلاق بسعر السوق (بدون انزلاق للخروج — محافظ)
            pnl = (px - t["entry"]) * t["qty"] if side == "CALL" else (t["entry"] - px) * t["qty"]
            t.update({"exit": px, "closed_at": datetime.datetime.utcnow().isoformat() + "Z",
                      "pnl": round(pnl - FEE, 2), "result": "expired"})
            closed_now.append(t)
            continue
        if result:
            pnl = (tgt - t["entry"]) * t["qty"] - FEE if result == "win" else (stop - t["entry"]) * t["qty"] - FEE
            if side == "PUT":
                pnl = (t["entry"] - tgt) * t["qty"] - FEE if result == "win" else (t["entry"] - stop) * t["qty"] - FEE
            t.update({"exit": tgt if result == "win" else stop,
                      "closed_at": datetime.datetime.utcnow().isoformat() + "Z",
                      "pnl": round(pnl, 2), "result": result})
            closed_now.append(t)
            print(f"📊 {t['symbol']} {side}: {result.upper()} — PnL ${pnl:,.2f} (دخل {t['entry']} → {tgt if result=='win' else stop})")
        else:
            still_open.append(t)
    led["trades"] = still_open
    led["closed"].extend(closed_now)
    # تحديث رأس المال
    led["capital"] = START_CAPITAL + sum(c["pnl"] for c in led["closed"])
    save_ledger(led)
    print(f"✅ التحديث: {len(closed_now)} صفقة أُغلقت، {len(still_open)} مفتوحة، الرصيد ${led['capital']:,.2f}")

def cmd_report():
    led = load_ledger()
    closed = led["closed"]
    wins = [c for c in closed if c.get("result") == "win"]
    losses = [c for c in closed if c.get("result") == "loss"]
    total_pnl = sum(c.get("pnl", 0) for c in closed)
    print(f"=== دفتر Vending — الرصيد ${led['capital']:,.2f} (بداية $100,000) ===")
    print(f"صفقات مغلقة: {len(closed)} | رابحة: {len(wins)} | خاسرة: {len(losses)} | منتهية: {len([c for c in closed if c.get('result')=='expired'])}")
    if closed:
        print(f"Win rate: {len(wins)/len(closed)*100:.0f}% | إجمالي PnL: ${total_pnl:,.2f}")
    print(f"مفتوحة حالياً: {len(led['trades'])}")
    for t in led["trades"][-5:]:
        print(f"  ⏳ {t['symbol']} {t['side']} @ {t['entry']} (stop {t['stop']} / هدف {t['target1']})")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "open":
        cmd_open()
    elif cmd == "update":
        cmd_update()
    elif cmd == "report":
        cmd_report()
    else:
        print(__doc__)
