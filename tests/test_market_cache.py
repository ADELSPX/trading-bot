#!/usr/bin/env python3
"""اختبارات قبول لكاش بيانات السوق (SELFTEST).

يشغّل سيرفر MCP الحقيقي كعملية منفصلة ويخاطبه ببروتوكول JSON-RPC كما يفعل هيرميس،
ويقيس زمن كل نداء. الفشل = exit code غير صفري.

التشغيل:
  /usr/bin/python3 /root/trading-bot/tests/test_market_cache.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

SERVER = ["/usr/bin/python3", "/root/trading-bot/mcp_server.py"]
ENV_BASE = {**os.environ, "PYTHONPATH": "/root/trading-bot"}

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")
    return bool(ok)


def call_mcp(tool: str, args: dict | None = None, env_extra: dict | None = None,
             timeout: int = 120) -> tuple[dict, float]:
    """يشغّل السيرفر ويستدعي أداة واحدة ويرجّع (النتيجة، زمن النداء بالمللي ثانية)."""
    env = {**ENV_BASE, **(env_extra or {})}
    p = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=env, cwd="/root/trading-bot")
    try:
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05"}}) + "\n")
        p.stdin.flush()
        p.stdout.readline()
        t0 = time.time()
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": tool, "arguments": args or {}}}) + "\n")
        p.stdin.flush()
        line = p.stdout.readline()
        ms = (time.time() - t0) * 1000
        resp = json.loads(line) if line.strip() else {}
        content = resp.get("result", {}).get("content", [{}])
        out = json.loads(content[0]["text"]) if content else {}
        return out, ms
    finally:
        try:
            p.stdin.close()
            p.kill()
        except Exception:
            pass


def main() -> int:
    print("=== اختبارات كاش بيانات السوق ===")
    t_start = time.time()

    # T1 — نداء أول (من الكاش أو تحديث)
    r1, ms1 = call_mcp("get_spx_price")
    check("T1 get_spx_price يرجّع سعراً", r1.get("success") and float(r1.get("price", 0)) > 0,
          f"price={r1.get('price')} status={r1.get('cache_status')} {ms1:.0f}ms")

    # T2 — نداء ثانٍ خلال الصلاحية → يجب أن يكون من الكاش وبدون شبكة
    r2, ms2 = call_mcp("get_spx_price")
    check("T2 النداء الثاني من الكاش (hit)", r2.get("cache_status") == "hit",
          f"status={r2.get('cache_status')} age_min={r2.get('age_minutes')} {ms2:.0f}ms")
    check("T2b زمن النداء من الكاش < 300ms", ms2 < 300, f"{ms2:.0f}ms")
    check("T2c السعران متطابقان (نفس المصدر المخزّن)", r1.get("price") == r2.get("price"),
          f"{r1.get('price')} == {r2.get('price')}")

    # T3 — انتهاء الصلاحية (TTL=1s) → يجب أن يحدّث من المصدر
    r3, ms3 = call_mcp("get_spx_price", env_extra={"MARKET_CACHE_TTL_OVERRIDE": "1"})
    time.sleep(2)
    r3b, ms3b = call_mcp("get_spx_price", env_extra={"MARKET_CACHE_TTL_OVERRIDE": "1"})
    check("T3 بعد انتهاء TTL → refreshed", r3b.get("cache_status") == "refreshed",
          f"status={r3b.get('cache_status')} {ms3b:.0f}ms (النداء الدافئ كان {ms3:.0f}ms)")

    # T4 — فشل المصدر + صلاحية منتهية → stale مع وسم وعمر (بلا سقوط)
    time.sleep(2)
    r4, ms4 = call_mcp("get_spx_price", env_extra={"MARKET_CACHE_TTL_OVERRIDE": "1",
                                                   "MARKET_CACHE_FORCE_FAIL": "1"})
    check("T4 فشل المصدر → stale مع وسم", r4.get("cache_status") == "stale" and bool(r4.get("stale_warning")),
          f"status={r4.get('cache_status')} warning={'نعم' if r4.get('stale_warning') else 'لا'}")
    check("T4b يظل يرجّع آخر سعر معروف", float(r4.get("price", 0)) > 0,
          f"price={r4.get('price')} age_min={r4.get('age_minutes')}")

    # T5 — الإنذارات من الكاش
    ra, msa = call_mcp("check_price_alerts")
    check("T5 check_price_alerts تنجح", ra.get("success") and ra.get("support") and ra.get("resistance"),
          f"current={ra.get('current')} support={ra.get('support')} resistance={ra.get('resistance')} "
          f"status={ra.get('cache_status')} {msa:.0f}ms")
    ra2, msa2 = call_mcp("check_price_alerts")
    check("T5b النداء الثاني للإنذارات من الكاش", ra2.get("cache_status") == "hit", f"{msa2:.0f}ms")

    # T6 — قاعدة فاضية (miss) → جلب من المصدر ثم كتابة
    tmp_db = "/root/.hermes/cache/scratch/mc_cold_test.db"
    os.makedirs(os.path.dirname(tmp_db), exist_ok=True)
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    r6, ms6 = call_mcp("get_spx_price", env_extra={"MARKET_CACHE_DB": tmp_db})
    check("T6 قاعدة فاضية → refreshed (مسار الجلب الكامل)", r6.get("cache_status") == "refreshed" and r6.get("success"),
          f"status={r6.get('cache_status')} price={r6.get('price')} {ms6:.0f}ms")

    # T7 — سجل النداءات: لا نداء شبكة في مسار الكاش
    sys.path.insert(0, "/root/trading-bot")
    import market_cache as mc  # noqa: PLC0415
    con = mc.connect()
    rows = con.execute("SELECT scope, key, ok, latency_ms, note FROM fetch_log ORDER BY id DESC LIMIT 12").fetchall()
    hits = con.execute("SELECT COUNT(*) FROM fetch_log WHERE ok=1").fetchone()[0]
    fails = con.execute("SELECT COUNT(*) FROM fetch_log WHERE ok=0").fetchone()[0]
    con.close()
    check("T7 fetch_log يسجّل النداءات", len(rows) > 0, f"نجحة={hits} فاشلة={fails}")
    check("T7b فشل المصدر مسجّل بسبب واضح",
          any((r["ok"] == 0) and (r["latency_ms"] is not None) for r in rows),
          f"آخر سبب: {[r['note'] for r in rows if r['ok'] == 0][:1]}")

    ok_all = all(ok for _, ok, _ in RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\nالنتيجة: {passed}/{len(RESULTS)} اختبار ناجح — الزمن الكلي {time.time() - t_start:.1f}s")
    print("SELFTEST:", "ALL_PASS" if ok_all else "FAILURES")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
