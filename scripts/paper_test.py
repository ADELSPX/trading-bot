#!/usr/bin/env python3
"""
فزّاع — سجل اختبار إشارات القاما (Paper Log)
يسجل إشارات السكربت وينفذ اختبار وهمي عبر الجسر
"""
import json
import os
import time
from datetime import datetime

import urllib.request

BRIDGE = "http://127.0.0.1:8795"
BRIDGE_KEY = "fazza-bridge-2026"
LOG_FILE = "/root/trading-bot/knowledge/analysis/signal_test_log.jsonl"


def bridge(method, path, payload=None):
    req = urllib.request.Request(
        f"{BRIDGE}{path}",
        data=json.dumps(payload).encode() if payload else None,
        headers={"X-API-Key": BRIDGE_KEY, "Content-Type": "application/json"},
        method=method,
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def load_log():
    entries = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    return entries


def log_entry(entry):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    print("📋 سجل اختبار إشارات القاما")
    print("=" * 50)

    # اتصال الجسر
    try:
        status = bridge("GET", "/health")
        print(f"🔗 الجسر: {'متصل ✅' if status.get('ok') else 'مشكلة'}")
        if not status.get("connected"):
            print("   ⚠️ IBKR غير متصل — أحاول الاتصال...")
            bridge("GET", "/connect")
    except Exception as e:
        print(f"❌ الجسر ما يرد: {e}")
        return

    # إشارات اليوم (من الفحص الأخير)
    scan_dir = "/root/trading-bot/knowledge/analysis"
    scans = sorted([f for f in os.listdir(scan_dir) if f.startswith("gamma_scan_")])
    if not scans:
        print("❌ لا يوجد فحص سابق — شغّل gamma_scanner أولاً")
        return

    latest = os.path.join(scan_dir, scans[-1])
    with open(latest, encoding="utf-8") as f:
        results = json.load(f)
    print(f"📊 أحدث فحص: {scans[-1]}")

    # نفذ الإشارات الواضحة (CALL → BUY، PUT → SELL)
    log = load_log()
    done = set(e.get("signal_ref") for e in log)

    for r in results:
        sym = r["symbol"]
        signal = r["signal"]
        ref = f"{sym}_{r.get('timestamp', '')[:10]}"

        if signal not in ("CALL", "PUT"):
            print(f"  ⏸ {sym}: WAIT — ما ننفذ")
            continue
        if ref in done:
            print(f"  ⏭ {sym}: مسجلة مسبقاً")
            continue

        # التنفيذ الورقي: CALL = شراء، PUT = بيع (أو عقد وهمي)
        action = "BUY" if signal == "CALL" else "SELL"
        qty = 1

        # للبيع: نتأكد عندنا السهم أو نشتري أولاً (في الـ Paper)
        if action == "SELL":
            # نشوف المحفظة — إذا ما عندنا السهم نشتري أولاً (عشان نقدر نبيع)
            port = bridge("GET", "/portfolio")
            have = any(p["symbol"] == sym for p in port.get("positions", []))
            if not have:
                print(f"  ℹ️ {sym}: ما عندنا سهم للبيع — أشتري أولاً (اختبار)")
                bridge("POST", "/order", {"symbol": sym, "action": "BUY", "qty": qty})
                time.sleep(3)

        order = bridge("POST", "/order", {"symbol": sym, "action": action, "qty": qty})
        print(f"  {'🟢' if signal=='CALL' else '🔴'} {sym}: {action} {qty} → {order.get('status')} @ {order.get('avgPrice')}")

        entry = {
            "signal_ref": ref,
            "symbol": sym,
            "signal": signal,
            "action": action,
            "qty": qty,
            "status": order.get("status"),
            "fill_price": order.get("avgPrice"),
            "signal_price": r.get("price"),
            "center": r.get("nearest_center"),
            "executed_at": datetime.now().isoformat(),
        }
        log_entry(entry)
        time.sleep(3)

    # ملخص
    print("\n" + "=" * 50)
    print(f"📒 إجمالي الصفقات المسجلة: {len(load_log())}")
    print(f"💾 السجل: {LOG_FILE}")


if __name__ == "__main__":
    main()
