#!/usr/bin/env python3
"""
فزّاع — مقيّم إشارات القاما (Signal Evaluator)
درس الـ 225 Backtest: أي استراتيجية تُختار على بيانات ماضية قد تكون صدفة.
الحل: التحقق الخارجي بالوقت الحقيقي —
1. كل إشارة تنحفظ عند إصدارها (مع سعر الدخول)
2. بعد 24 ساعة و48 ساعة: نقيس النتيجة فعلياً (ربح/خسارة)
3. تقرير دوري: نسبة النجاح الفعلية — مو المزعومة

الاستخدام:
  python3 signal_evaluator.py --record   # يسجل نتائج الإشارات القديمة غير المقيمة (بعد التشغيل اليومي)
  python3 signal_evaluator.py --report   # تقرير النجاح الفعلي
"""
import json
import os
import sys
from datetime import datetime, timedelta
from glob import glob

import yfinance as yf

SCAN_DIR = "/root/trading-bot/knowledge/analysis"
STATE = "/root/trading-bot/knowledge/analysis/evaluated_signals.json"
HORIZONS_H = [24, 48]   # نقاط التقييم بالساعات


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {}


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w"), ensure_ascii=False, indent=1)


def collect_signals():
    """يجمع كل الإشارات CALL/PUT من ملفات السكانر غير المقيمة"""
    st = load_state()
    new = []
    for f in sorted(glob(os.path.join(SCAN_DIR, "gamma_scan_*.json"))):
        try:
            data = json.load(open(f))
        except Exception:
            continue
        ts = data[0].get("timestamp", "") if data else ""
        if not ts:
            continue
        for r in data:
            sig = r.get("signal")
            if sig not in ("CALL", "PUT"):
                continue
            key = f"{r['symbol']}_{ts[:16]}_{sig}"
            if key in st:
                continue
            new.append({
                "key": key,
                "symbol": r["symbol"],
                "signal": sig,
                "price": r.get("price"),
                "nearest_center": r.get("nearest_center"),
                "time": ts,
            })
    return new


def price_at(symbol, when_iso):
    """سعر الإغلاق الأقرب لوقت معين عبر yfinance"""
    t = datetime.fromisoformat(when_iso)
    tk = yf.Ticker(symbol)
    hist = tk.history(start=(t - timedelta(days=5)).strftime("%Y-%m-%d"),
                      end=(t + timedelta(days=2)).strftime("%Y-%m-%d"),
                      interval="1h")
    if hist.empty:
        return None
    target = t
    diffs = [abs((i.to_pydatetime() - target.replace(tzinfo=i.tz)).total_seconds()) for i in hist.index]
    i = diffs.index(min(diffs))
    return float(hist["Close"].iloc[i])


def evaluate():
    """قيّم الإشارات المستحقة (مرّ عليها 24/48 ساعة)"""
    st = load_state()
    now = datetime.now()
    results = []
    for key, s in list(st.items()):
        if s.get("done"):
            continue
        issued = datetime.fromisoformat(s["time"])
        for h in HORIZONS_H:
            tag = f"h{h}"
            if tag in s or now < issued + timedelta(hours=h):
                continue
            p = price_at(s["symbol"], s["time"])  # نفس اللحظة تقريباً = سعر الإغلاق المستهدف
            # السعر بعد h ساعة من وقت الإصدار
            p_after = None
            tk = yf.Ticker(s["symbol"])
            hist = tk.history(start=issued.strftime("%Y-%m-%d"), end=(now + timedelta(days=1)).strftime("%Y-%m-%d"), interval="1h")
            if not hist.empty:
                tgt = issued + timedelta(hours=h)
                diffs = [abs((i.to_pydatetime() - tgt.replace(tzinfo=i.tz)).total_seconds()) for i in hist.index]
                j = diffs.index(min(diffs))
                if diffs[j] < 3600 * 6:  # لا نقيس لو البعد كبير (إجازة سوق)
                    p_after = float(hist["Close"].iloc[j])
            entry = s.get("entry_price") or p
            if entry and p_after:
                direction = 1 if s["signal"] == "CALL" else -1
                s[f"pct_{tag}"] = round(direction * (p_after / entry - 1) * 100, 2)
            s[tag] = True
        if all(f"h{h}" in s for h in HORIZONS_H) and any("pct_" in k for k in s):
            wins = [s[k] for k in ("pct_h24", "pct_h48") if k in s]
            s["win"] = all(w > 0 for w in wins) if wins else None
        if all(f"h{h}" in s for h in HORIZONS_H):
            s["done"] = True
            results.append(s)
    save_state(st)
    return results


def report():
    st = load_state()
    done = [s for s in st.values() if s.get("done")]
    if not done:
        print("لا توجد إشارات مكتملة التقييم بعد — تحتاج 48 ساعة من التشغيل")
        return
    wins24 = [s for s in done if s.get("pct_h24") is not None and s["pct_h24"] > 0]
    with24 = [s for s in done if s.get("pct_h24") is not None]
    wins48 = [s for s in done if s.get("pct_h48") is not None and s["pct_h48"] > 0]
    with48 = [s for s in done if s.get("pct_h48") is not None]
    avg24 = sum(s["pct_h24"] for s in with24) / len(with24) if with24 else 0
    print(f"📊 تقرير إشارات القاما — النجاح الفعلي (خارج العينة، بالوقت الحقيقي)")
    print(f"إجمالي الإشارات المكتملة: {len(done)}")
    if with24:
        print(f"نجاح 24 ساعة: {len(wins24)}/{len(with24)} = {100*len(wins24)/len(with24):.0f}% | متوسط الحركة: {avg24:+.2f}%")
    if with48:
        print(f"نجاح 48 ساعة: {len(wins48)}/{len(with48)} = {100*len(wins48)/len(with48):.0f}%")
    # حسب الرمز
    by_sym = {}
    for s in done:
        by_sym.setdefault(s["symbol"], []).append(s)
    for sym, lst in sorted(by_sym.items()):
        w = [s for s in lst if s.get("pct_h24") is not None and s["pct_h24"] > 0]
        n = [s for s in lst if s.get("pct_h24") is not None]
        if n:
            print(f"  {sym}: {len(w)}/{len(n)} ({100*len(w)/len(n):.0f}%)")


def record():
    st = load_state()
    new = collect_signals()
    added = 0
    for s in new:
        if s["key"] not in st:
            # احفظ سعر الدخول لحظة التسجيل إن لم يوجد
            st[s["key"]] = {"symbol": s["symbol"], "signal": s["signal"],
                            "time": s["time"], "entry_price": s.get("price")}
            added += 1
    save_state(st)
    ev = evaluate()
    print(f"مسجلة جديدة: {added} | مكتملة التقييم الآن: {len(ev)}")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        record()
