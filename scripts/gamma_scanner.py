#!/usr/bin/env python3
"""
فزّاع — سكريبت تحليل مبادئ فهد (Gamma Scanner v1)
يطبق مبادئ مركز سيولة الصانع على الأسهم:
1. مراكز السيولة = استرايكات متكررة (OI عالي عبر 3+ انتهاءات من 3-6 أسابيع)
2. الاتجاه = شمعة 5 دقائق (خضراء فوق المركز = كول، حمراء تحت = بوت)
3. إشارة: Call / Put / لا صفقة

الاستخدام: python3 gamma_scanner.py [SYMBOLS]
"""
import json
import sys
import time
from datetime import datetime

import yfinance as yf

# ============ الإعدادات ============
SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "SPY", "QQQ"]
MAX_EXPIRIES = 6          # عدد الانتهاءات (أسابيع)
MIN_REPEAT = 3            # الحد الأدنى لتكرار الاسترايك (3-6 أسابيع)
OI_TOP_N = 8              # عدد أعلى استرايكات OI نعتبرها مراكز سيولة
OUTPUT = "/root/trading-bot/knowledge/analysis/gamma_scan_"


def get_option_oi(ticker_symbol):
    """جلب OI لكل استرايك عبر الانتهاءات القريبة"""
    ticker = yf.Ticker(ticker_symbol)
    try:
        expiries = list(ticker.options[:MAX_EXPIRIES])
    except Exception as e:
        print(f"  ⚠️ {ticker_symbol}: ما فيه خيارات ({e})")
        return None, []

    # strike -> {expiry: {call_oi, put_oi, total}}
    strikes = {}

    for exp in expiries:
        try:
            chain = ticker.option_chain(exp)
        except Exception as e:
            print(f"  ⚠️ {exp}: فشل ({e})")
            continue

        # تجميع OI للاسترايكات
        for _, row in chain.calls.iterrows():
            s = round(row.get("strike", 0), 0)
            oi = row.get("openInterest", 0) or 0
            if s <= 0:
                continue
            st = strikes.setdefault(s, {"expiries": {}, "total_oi": 0, "call_oi": 0, "put_oi": 0})
            st["expiries"][exp] = st["expiries"].get(exp, 0) + oi
            st["call_oi"] += oi
            st["total_oi"] += oi

        for _, row in chain.puts.iterrows():
            s = round(row.get("strike", 0), 0)
            oi = row.get("openInterest", 0) or 0
            if s <= 0:
                continue
            st = strikes.setdefault(s, {"expiries": {}, "total_oi": 0, "call_oi": 0, "put_oi": 0})
            st["expiries"][exp] = st["expiries"].get(exp, 0) + oi
            st["put_oi"] += oi
            st["total_oi"] += oi

        time.sleep(0.3)  # مهذبة مع Yahoo

    return expiries, strikes


def find_liquidity_centers(strikes, min_repeat=MIN_REPEAT):
    """مراكز السيولة = استرايكات بـ OI عالي متكرر عبر انتهاءات متعددة"""
    if not strikes:
        return []

    # عد التكرار: في كم انتهاء ظهر الاسترايك بـ OI > 0
    for s, data in strikes.items():
        data["repeat_count"] = len([e for e, oi in data["expiries"].items() if oi > 0])

    # الاسترايكات المتكررة (3+)
    repeated = {s: d for s, d in strikes.items() if d["repeat_count"] >= min_repeat}
    if not repeated:
        return []

    # رتب بـ total_oi — خذ أعلى OI_TOP_N
    top = sorted(repeated.items(), key=lambda kv: kv[1]["total_oi"], reverse=True)[:OI_TOP_N]
    return [(s, d) for s, d in top]


def get_5m_signal(ticker_symbol, current_price):
    """شمعة 5 دقائق الأخيرة: خضراء/حمراء — فوق/تحت المركز"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="2d", interval="5m")
        if hist.empty:
            return None

        last = hist.iloc[-1]
        o, c = last["Open"], last["Close"]
        green = c > o
        red = c < o
        return {
            "time": str(hist.index[-1]),
            "open": round(float(o), 2),
            "close": round(float(c), 2),
            "green": green,
            "red": red,
            "last_price": round(float(c), 2),
        }
    except Exception as e:
        print(f"  ⚠️ 5m فشل: {e}")
        return None


def decide(candle, centers):
    """القرار حسب مبادئ فهد: شمعة خضراء فوق المركز = كول، حمراء تحت = بوت"""
    if not candle or not centers:
        return "WAIT", None

    price = candle["last_price"]
    # أقرب مركز سيولة للسعر
    nearest = min(centers, key=lambda x: abs(x[0] - price))
    strike, data = nearest
    above = price > strike
    below = price < strike

    if candle["green"] and above:
        return "CALL", strike
    if candle["red"] and below:
        return "PUT", strike
    return "WAIT", strike


def scan(symbols=None, quiet=False):
    symbols = symbols or SYMBOLS
    results = []

    for sym in symbols:
        if not quiet:
            print(f"\n📊 {sym} — فحص...")
        expiries, strikes = get_option_oi(sym)
        if not strikes:
            results.append({"symbol": sym, "signal": "NO_DATA", "centers": []})
            continue

        centers = find_liquidity_centers(strikes)
        if not quiet:
            print(f"  انتهاءات: {len(expiries)} | استرايكات: {len(strikes)} | مراكز سيولة: {len(centers)}")

        # السعر الحالي (من بيانات 5m)
        candle = get_5m_signal(sym, None)
        if candle and not quiet:
            print(f"  آخر شمعة: {'🟢' if candle['green'] else '🔴'} {candle['close']} ({candle['time']})")

        signal, nearest_strike = decide(candle, centers)
        if not quiet:
            print(f"  ⚡ الإشارة: {signal}" + (f" (المركز: {nearest_strike})" if nearest_strike else ""))

        results.append({
            "symbol": sym,
            "signal": signal,
            "price": candle["last_price"] if candle else None,
            "nearest_center": nearest_strike,
            "centers": [(s, d["total_oi"], d["repeat_count"]) for s, d in centers],
            "candle": candle,
            "timestamp": datetime.now().isoformat(),
        })

    return results


def main():
    symbols = None
    quiet = False
    if len(sys.argv) > 1 and "--cron" in sys.argv:
        quiet = True
        symbols = [a for a in sys.argv[1:] if a != "--cron"] or None
    elif sys.argv[1:]:
        symbols = sys.argv[1:]

    results = scan(symbols, quiet=quiet)

    # حفظ النتائج
    import os
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    outfile = OUTPUT + datetime.now().strftime("%Y%m%d_%H%M") + ".json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # للكرون: اطبع الإشارات الفعلية فقط (صامت لو كلها WAIT — لا يزعج)
    signals = [r for r in results if r["signal"] in ("PUT", "CALL")]
    if not signals:
        return
    print("⚡ إشارات القاما اليوم:")
    for r in signals:
        price = r.get("price") or "?"
        center = r.get("nearest_center") or "?"
        print(f"  {r['symbol']}: {r['signal']} @ {price} (المركز: {center})")


if __name__ == "__main__":
    main()
