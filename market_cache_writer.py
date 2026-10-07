#!/usr/bin/env python3
"""market_cache_writer.py — الكاتب الخلفي لكاش بيانات السوق.

يعمل عبر cron (no_agent → صفر توكنات) كل 5 دقائق أثناء السوق، ويكتب في
/root/.hermes/state/market_cache.db حتى تقرأ الأدوات من القاعدة بلا شبكة.

- يعتمد حارس السوق الأمريكي بتوقيت نيويورك (يتعامل مع التوقيت الصيفي).
- صامت افتراضياً (stdout فاضي = لا حدث) — يطبع فقط عند خطأ أو مع --verbose.
- --force يتجاوز حارس السوق (للاختبار).

أمثلة:
  ./.venv/bin/python3 market_cache_writer.py --symbols SPX --force --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
import time

sys.path.insert(0, "/root/trading-bot")

import market_cache as mc  # noqa: E402


def refresh_symbol(symbol: str, verbose: bool = False) -> dict:
    out: dict = {"symbol": symbol}
    t0 = time.time()

    # 1) السعر اللحظي (شمعات يوم/دقيقة → آخر صف)
    try:
        q = mc.fetch_quote_from_source(symbol)
        if not q:
            raise RuntimeError("الجالب رجّع قيمة فاضية")
        con = mc.connect()
        try:
            mc._write_quote(con, q)
            con.commit()
        finally:
            con.close()
        out["quote"] = q["price"]
        out["quote_source"] = q["source"]
        mc.log_fetch("quote", symbol, True, int((time.time() - t0) * 1000), 1, note="writer")
    except Exception as e:  # noqa: BLE001
        mc.log_fetch("quote", symbol, False, int((time.time() - t0) * 1000), 0,
                     error=f"{type(e).__name__}: {e}", note="writer")
        out["quote_error"] = f"{type(e).__name__}: {e}"

    # 2) الشمعات: 1د و5د
    for period, interval in (("1d", "1m"), ("5d", "5m")):
        try:
            n, ms = mc.refresh_candles(symbol, period, interval)
            out[f"candles_{interval}"] = n
        except Exception as e:  # noqa: BLE001
            out[f"candles_{interval}_error"] = f"{type(e).__name__}: {e}"

    # 3) الإنذارات المحسوبة من الكاش (بلا شبكة إضافية)
    try:
        con = mc.connect()
        try:
            rows = mc.read_candles(symbol, "5m", 400, con=con)
            if len(rows) >= 5:
                closes = [float(r["close"]) for r in rows]
                calc = mc.compute_alerts(closes[-1], closes)
                mc._write_alerts(con, {
                    "symbol": symbol.upper(), "computed_at": mc.now_utc(),
                    "current": round(closes[-1], 2), "support": calc["support"],
                    "resistance": calc["resistance"],
                    "alerts_json": json.dumps(calc["alerts"], ensure_ascii=False),
                    "window_desc": "آخر 20 شمعة (5 دقائق)", "source": "cache",
                })
                con.commit()
                out["alerts"] = calc["alerts"]
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        out["alerts_error"] = f"{type(e).__name__}: {e}"

    out["elapsed_ms"] = int((time.time() - t0) * 1000)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="SPX", help="رموز مفصولة بفاصلة")
    ap.add_argument("--force", action="store_true", help="تجاوز حارس وقت السوق")
    ap.add_argument("--verbose", action="store_true", help="اطبع التفاصيل")
    ap.add_argument("--prune-days", type=int, default=30)
    args = ap.parse_args()

    mc.init_db()
    if not mc.market_open() and not args.force:
        if args.verbose:
            print(f"السوق مقفل — لا تحديث ({mc.now_utc()})")
        return 0

    results = []
    failed = []
    for sym in [s.strip().upper() for s in args.symbols.split(",") if s.strip()]:
        r = refresh_symbol(sym, args.verbose)
        results.append(r)
        if "quote_error" in r and "candles_5m_error" in r:
            failed.append(sym)

    pruned = mc.prune(args.prune_days)

    if args.verbose:
        print(json.dumps({"results": results, "pruned": pruned, "market_open": mc.market_open()},
                         ensure_ascii=False, indent=1))
    if failed:
        print(f"⚠️ كاش السوق: فشل تحديث {', '.join(failed)} — راجع fetch_log في {mc.DB_PATH}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
