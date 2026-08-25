#!/usr/bin/env python3
"""
فزّاع — حلقة التعلم الذاتي (signal_feedback.py)
يقرأ نتائج signal_evaluator (ربح/خسارة فعلية) ويضبط أوزان gamma_scanner_v2:
- كل إشارة ناجحة/خاسرة تُقارن بمكونات score وقت الإصدار
- المكون اللي كان عالي في الصفقات الرابحة → وزنه يزيد قليلاً
- المكون اللي كان عالي في الخاسرة → وزنه ينقص قليلاً
تعديل محافظ (±10% كحد أقصى) + حدود دنيا حتى لا ينهار فلتر.

التشغيل: python3 signal_feedback.py  (بعد تشغيل evaluator — مرة يومياً)
"""
import json
import os

WEIGHTS = "/root/trading-bot/knowledge/scanner_weights.json"
EVAL = "/root/trading-bot/knowledge/analysis/evaluated_signals.json"
SCANS_DIR = "/root/trading-bot/knowledge/analysis"
SEEN = "/root/trading-bot/knowledge/analysis/feedback_seen.json"

DEFAULT_WEIGHTS = {"center_strength": 1.0, "activity": 1.0,
                   "distance": 1.0, "candle_body": 0.5}
MIN_W, MAX_W, STEP = 0.4, 1.6, 0.06   # ±6% لكل تحديث


def load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def find_scan_components(key):
    """يجد مكونات score للإشارة من أقرب ملف سكانر زمنياً
    key = 'SYMBOL_YYYY-MM-DDTHH:MM_SIGNAL'"""
    import glob
    from datetime import datetime
    parts = key.split("_")
    sym, ts_str = parts[0], parts[1][:16]
    try:
        target = datetime.fromisoformat(ts_str)
    except Exception:
        return None
    best, best_diff = None, None
    for f in glob.glob(os.path.join(SCANS_DIR, "gamma_scan_*.json")):
        try:
            data = json.load(open(f))
        except Exception:
            continue
        for r in data if isinstance(data, list) else []:
            comps = (r.get("detail") or {}).get("components")
            if not comps or not r.get("timestamp"):
                continue
            if r.get("symbol") != sym or not r.get("detail", {}).get("score"):
                continue
            try:
                t = datetime.fromisoformat(r["timestamp"][:19])
            except Exception:
                continue
            diff = abs((t - target).total_seconds())
            if diff > 7200:   # أكثر من ساعتين = مو نفس الفحص
                continue
            if best_diff is None or diff < best_diff:
                best_diff, best = diff, comps
    return best


def main():
    weights = load_json(WEIGHTS, dict(DEFAULT_WEIGHTS))
    ev = load_json(EVAL, {})
    seen = load_json(SEEN, {})
    updated = 0
    for key, sig in ev.items():
        if key in seen or not sig.get("done"):
            continue
        pct = sig.get("pct_h48", sig.get("pct_h24"))
        if pct is None:
            continue
        comps = find_scan_components(key)
        seen[key] = True
        if not comps:
            continue
        win = (sig["signal"] == "CALL" and pct > 0) or (sig["signal"] == "PUT" and pct < 0)
        direction = STEP if win else -STEP
        # المكونات العالية أكثر تأثراً بالنتيجة
        strength = float(comps.get("score", 50)) / 100.0
        for comp in weights:
            influence = comps.get(comp, 50) / 100.0 * strength
            weights[comp] = round(min(MAX_W, max(MIN_W,
                          weights[comp] + direction * influence)), 3)
        updated += 1
        print(f"  {'✅' if win else '❌'} {key} ({pct:+.2f}%) → {weights}")

    json.dump(weights, open(WEIGHTS, "w"), indent=1)
    json.dump(seen, open(SEEN, "w"))
    print(f"\nأوزان محدثة ({updated} إشارة): {weights}")
    print(f"محفوظة في {WEIGHTS}")


if __name__ == "__main__":
    main()
