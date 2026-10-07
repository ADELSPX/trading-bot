#!/usr/bin/env python3
"""cache_report.py — تقرير حالة كاش بيانات السوق (دليل قابل للتحقق)."""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, "/root/trading-bot")
import market_cache as mc  # noqa: E402


def main() -> int:
    con = mc.connect()
    size = os.path.getsize(mc.DB_PATH) / 1024 if os.path.exists(mc.DB_PATH) else 0
    print(f"القاعدة: {mc.DB_PATH}  ({size:.0f} KB)")
    print(f"السوق مفتوح الآن: {mc.market_open()}   (نيويورك: {mc.now_utc()})")
    for t in ("quotes", "candles", "option_chains", "alerts"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n}")
    print("\nنداءات المصدر المسجّلة (fetch_log):")
    for r in con.execute("SELECT scope, key, ok, latency_ms, rows, note FROM fetch_log ORDER BY id DESC LIMIT 10"):
        print(f"  {'✔' if r['ok'] else '✘'} {r['scope']:12s} {r['key']:12s} {r['latency_ms'] or 0:6d}ms rows={r['rows']} {r['note'] or ''}")
    ok = con.execute("SELECT COUNT(*), AVG(latency_ms) FROM fetch_log WHERE ok=1").fetchone()
    bad = con.execute("SELECT COUNT(*) FROM fetch_log WHERE ok=0").fetchone()[0]
    print(f"\nإجمالي: نجح {ok[0]} (وسيط {ok[1] or 0:.0f}ms) — فشل {bad}")
    print("آخر سعر مخزّن:")
    for r in con.execute("SELECT symbol, price, prev_close, source, fetched_at FROM quotes"):
        print(" ", dict(r))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
