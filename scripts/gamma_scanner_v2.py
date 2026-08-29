#!/usr/bin/env python3
"""
فزّاع — Gamma Scanner v2 (طبقات جودة + Score + تعلم ذاتي)
مبني على مبادئ فهد القاما:
- مركز سيولة الصانع: استرايك متكرر 3+ انتهاءات بـ OI عالي
- الاتجاه: شمعة 5 دقائق فوق/تحت المركز
- فلاتر الجودة v2:
  1. قوة المركز (نسبة OI مقابل المتوسط + هيمنة كول/بوت)
  2. نشاط المركز (تغير OI اليومي)
  3. مسافة السعر عن المركز (لا دخول لو ملامس أو بعيد جدا)
  4. فلتر الوقت (لا صفقات أول 30 دقيقة / آخر ساعة)
- Score 0-100: فوق MIN_SCORE فقط تنرسل، والباقي يُسجل كمرفوض (يتعلم منها)
- الأوزان في weights.json يتحدثها signal_feedback.py من نتائج evaluator

الاستخدام:
  python3 gamma_scanner_v2.py            # تفصيلي
  python3 gamma_scanner_v2.py --cron     # صامت — يطبع الإشارات الناجحة فقط
"""
import json
import os
import sys
import time
from datetime import datetime

import yfinance as yf

# ============ الإعدادات ============
SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "SPY", "QQQ"]
MAX_EXPIRIES = 6
MIN_REPEAT = 3
OI_TOP_N = 8
MIN_SCORE = 70          # الحد الأدنى لإصدار إشارة
WEIGHTS_FILE = "/root/trading-bot/knowledge/analysis/scanner_weights.json"
OUTPUT_DIR = "/root/trading-bot/knowledge/analysis"
REJECTED_LOG = os.path.join(OUTPUT_DIR, "rejected_signals.jsonl")

# أوزان افتراضية — تتحدث تلقائياً من signal_feedback.py
DEFAULT_WEIGHTS = {
    "center_strength": 1.0,
    "activity": 1.0,
    "distance": 1.0,
    "candle_body": 0.5,
    "gamma_exposure": 0.8,   # ★ طبقة القاما (GEX) — قامات الإغلاق كخريطة سيولة
}


def load_weights():
    try:
        return json.load(open(WEIGHTS_FILE))
    except Exception:
        return dict(DEFAULT_WEIGHTS)


def save_scan(results):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, "gamma_scan_" + datetime.now().strftime("%Y%m%d_%H%M") + ".json")
    json.dump(results, open(out, "w"), ensure_ascii=False, indent=2, default=str)


def log_rejected(entry):
    with open(REJECTED_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_option_oi(ticker_symbol):
    """OI لكل استرايك عبر الانتهاءات + تغير اليومي"""
    ticker = yf.Ticker(ticker_symbol)
    try:
        expiries = list(ticker.options[:MAX_EXPIRIES])
    except Exception:
        return None, [], {}

    strikes = {}
    for exp in expiries:
        try:
            chain = ticker.option_chain(exp)
        except Exception:
            continue
        for side, rows in (("call", chain.calls), ("put", chain.puts)):
            for _, row in rows.iterrows():
                s = round(float(row.get("strike", 0) or 0), 0)
                oi = float(row.get("openInterest", 0) or 0)
                vol = float(row.get("volume", 0) or 0)
                if s <= 0:
                    continue
                st = strikes.setdefault(s, {"expiries": {}, "total_oi": 0.0,
                                            "call_oi": 0.0, "put_oi": 0.0,
                                            "volume": 0.0})
                st["expiries"][exp] = st["expiries"].get(exp, 0) + oi
                st["total_oi"] += oi
                st["volume"] += vol
                if side == "call":
                    st["call_oi"] += oi
                else:
                    st["put_oi"] += oi
        time.sleep(0.25)
    return expiries, list(strikes.items()), strikes


def get_gamma_exposure(ticker_symbol):
    """★ طبقة القاما (GEX): قامات الإغلاق كخريطة سيولة الصانع.

    yfinance لا يرجع 'gamma' مباشرة لـ SPY/السائد، فنقدّر GEX من:
      net_gex(strike) ≈ (call_oi - put_oi) × underlying_price × factor
    حيث القيمة الموجبة = ضغط كول (السعر يميل للصعود نحو المركز)،
    والسالبة = ضغط بوت (يميل للهبوط). القيمة المطلقة الكبيرة = مركز سيولة قوي.
    (هذا يطابق منطق فهد: نوع السيولة من هيمنة الكول/البوت عند نفس الاسترايك)
    """
    ticker = yf.Ticker(ticker_symbol)
    try:
        expiries = list(ticker.options[:MAX_EXPIRIES])
        underlying = float(ticker.history(period="1d").iloc[-1]["Close"])
    except Exception:
        return {}
    gex = {}
    # نجمع OI الكول والبوت لكل استرايك عبر الانتهاءات
    call_oi = {}
    put_oi = {}
    for exp in expiries:
        try:
            chain = ticker.option_chain(exp)
        except Exception:
            continue
        for side, rows in (("call", chain.calls), ("put", chain.puts)):
            for _, row in rows.iterrows():
                s = round(float(row.get("strike", 0) or 0), 0)
                oi = float(row.get("openInterest", 0) or 0)
                if s <= 0 or oi <= 0:
                    continue
                if side == "call":
                    call_oi[s] = call_oi.get(s, 0.0) + oi
                else:
                    put_oi[s] = put_oi.get(s, 0.0) + oi
        time.sleep(0.2)
    # GEX تقديري: (كول - بوت) × السعر الأساسي × 100 (لكل عقد)
    for s in set(call_oi) | set(put_oi):
        net = (call_oi.get(s, 0.0) - put_oi.get(s, 0.0)) * underlying * 100
        gex[s] = gex.get(s, 0.0) + net
    return gex


def gamma_exposure_score(strike, gex_map):
    """درجة القاما للاسترايك: القيمة المطلقة الكبيرة = مركز سيولة قوي.
    نطبّع على أقصى |GEX| (50% منه = درجة كاملة).
    """
    if not gex_map:
        return 50
    vals = [abs(v) for v in gex_map.values() if v != 0]
    if not vals:
        return 50
    max_abs = max(vals)
    if max_abs <= 0:
        return 50
    this = abs(gex_map.get(strike, 0.0))
    return min(100.0, this / (max_abs * 0.5) * 100)


def find_centers(strikes_items, min_repeat=MIN_REPEAT):
    """مراكز السيولة مع قوة ونشاط"""
    centers = []
    for s, d in strikes_items:
        d["repeat_count"] = len([e for e, oi in d["expiries"].items() if oi > 0])
        if d["repeat_count"] >= min_repeat and d["total_oi"] > 0:
            centers.append((s, d))
    centers.sort(key=lambda x: x[1]["total_oi"], reverse=True)
    return centers[:OI_TOP_N]


def center_strength_score(center_data, avg_oi):
    """قوة المركز: نسبة OI للمتوسط (حتى 2x المتوسط = ممتاز)"""
    if avg_oi <= 0:
        return 50
    ratio = center_data["total_oi"] / avg_oi
    return min(100.0, ratio / 2.0 * 100)


def activity_score(center_data):
    """نشاط اليوم: حجم التداول مقارنة بـ OI (نشيط = الصانع يعدّل مركزه الآن)"""
    if center_data["total_oi"] <= 0:
        return 0
    ratio = center_data["volume"] / center_data["total_oi"]
    return min(100.0, ratio * 500)   # 20% حجم/OI = 100


def distance_score(price, strike):
    """المسافة المثالية: قريب من المركز لكن غير ملامس له (0.05% - 1.5%)"""
    if not price or not strike or strike == 0:
        return 0
    dist_pct = abs(price - strike) / strike * 100
    if dist_pct < 0.02:      # ملامس تماماً — خطر اختراق معاكس
        return 10
    if dist_pct <= 1.5:
        # كلما اقترب (بدون لمس) كان أفضل
        return 60 + 40 * (1 - dist_pct / 1.5)
    # بعيد جداً — المركز مو منطقة اللعب الحالية
    return max(0, 40 - (dist_pct - 1.5) * 15)


def candle_body_score(candle):
    """قوة الشمعة: جسم كبير = قرار واضح"""
    if not candle:
        return 0
    body = abs(candle["close"] - candle["open"])
    rng = max(candle.get("high", candle["close"]) - candle.get("low", candle["open"]), 1e-9)
    return min(100.0, body / rng * 200)


def get_5m_candle(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="2d", interval="5m")
    if hist.empty:
        return None
    last = hist.iloc[-1]
    return {
        "time": str(hist.index[-1]),
        "open": round(float(last["Open"]), 2),
        "high": round(float(last["High"]), 2),
        "low": round(float(last["Low"]), 2),
        "close": round(float(last["Close"]), 2),
        "green": bool(last["Close"] > last["Open"]),
        "red": bool(last["Close"] < last["Open"]),
        "last_price": round(float(last["Close"]), 2),
    }


def time_filter_us():
    """فلتر وقت السوق الأمريكي: لا أول 30 دقيقة ولا آخر 60 دقيقة"""
    from datetime import timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    et = now_utc - timedelta(hours=4)  # EDT صيفي
    minutes = et.hour * 60 + et.minute
    market_open = 9 * 60 + 30
    market_close = 16 * 60
    if not (market_open <= minutes < market_close):
        return False, "outside_market_hours"
    if minutes < market_open + 30:
        return False, "first_30min"
    if minutes >= market_close - 60:
        return False, "last_hour"
    return True, ""


def decide_v2(price, candle, centers, weights, avg_oi, gex_map=None):
    """القرار الكامل: اتجاه + score تفصيلي (مع طبقة القاما)"""
    time_ok, time_reason = time_filter_us()
    detail = {
        "time_ok": time_ok, "time_reason": time_reason,
        "components": {}, "nearest_center": None,
    }
    if not candle or not centers:
        detail["reason"] = "no_data"
        return "WAIT", None, detail

    nearest_strike, nd = min(centers, key=lambda x: abs(x[0] - price))
    detail["nearest_center"] = nearest_strike

    comps = {
        "center_strength": center_strength_score(nd, avg_oi),
        "activity": activity_score(nd),
        "distance": distance_score(price, nearest_strike),
        "candle_body": candle_body_score(candle),
        "gamma_exposure": gamma_exposure_score(nearest_strike, gex_map or {}),
    }
    total_w = sum(weights.get(k, DEFAULT_WEIGHTS[k]) for k in comps)
    score = int(sum(comps[k] * weights.get(k, DEFAULT_WEIGHTS[k]) for k in comps) / total_w)
    detail["components"] = {k: round(v, 1) for k, v in comps.items()}
    detail["score"] = score

    above, below = price > nearest_strike, price < nearest_strike
    if candle["green"] and above:
        direction = "CALL"
    elif candle["red"] and below:
        direction = "PUT"
    else:
        detail["reason"] = "direction_unclear"
        return "WAIT", nearest_strike, detail

    if not time_ok:
        return "WAIT", nearest_strike, detail
    if score >= MIN_SCORE:
        return direction, nearest_strike, detail
    detail["reason"] = f"score_below_{MIN_SCORE}"
    return "WAIT", nearest_strike, detail


def scan(symbols=None, quiet=False):
    symbols = symbols or SYMBOLS
    weights = load_weights()
    results = []
    for sym in symbols:
        if not quiet:
            print(f"\n📊 {sym}...")
        expiries, strikes_items, strikes_map = get_option_oi(sym)
        if not strikes_map:
            results.append({"symbol": sym, "signal": "NO_DATA"})
            continue
        centers = find_centers(strikes_items)
        all_oi = [d["total_oi"] for _, d in centers] or [0]
        avg_oi = sum(all_oi) / len(all_oi) if all_oi else 0
        candle = get_5m_candle(sym)
        price = candle["last_price"] if candle else None
        # ★ طبقة القاما (قامات الإغلاق كخريطة سيولة)
        gex_map = get_gamma_exposure(sym)
        signal, strike, detail = decide_v2(price, candle, centers, weights, avg_oi, gex_map)

        entry = {
            "symbol": sym,
            "signal": signal,
            "price": price,
            "nearest_center": strike,
            "centers": [(s, round(d["total_oi"]), d["repeat_count"],
                        round(d["call_oi"]), round(d["put_oi"])) for s, d in centers],
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        }
        results.append(entry)
        if not quiet:
            print(f"  ⚡ {signal}" + (f" | مركز: {strike} | score: {detail.get('score')} "
                  f"{detail['components']}" if strike else ""))
        # الإشارات المرفوضة تنسجل — المخ يتعلم منها لاحقاً
        if signal == "WAIT" and detail.get("score") is not None and detail["components"]:
            log_rejected({"symbol": sym, "price": price, "center": strike,
                          "score": detail["score"], "components": detail["components"],
                          "reason": detail.get("reason", detail.get("time_reason")),
                          "ts": entry["timestamp"]})
    return results


def main():
    args = sys.argv[1:]
    quiet = "--cron" in args
    symbols = [a for a in args if a != "--cron"] or None
    results = scan(symbols, quiet=quiet)
    save_scan(results)
    signals = [r for r in results if r["signal"] in ("PUT", "CALL")]
    if not signals:
        return
    print("⚡ إشارات القاما v2:")
    for r in signals:
        d = r.get("detail", {})
        print(f"  {r['symbol']}: {r['signal']} @ {r['price']} "
              f"(مركز: {r['nearest_center']} | score: {d.get('score')} | {d.get('components')})")


if __name__ == "__main__":
    main()
