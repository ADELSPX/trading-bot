#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار آلي أوفلاين لـ watchlist.py + وسائط gamma_scanner_v2.py.

التشغيل:
  .venv/bin/python3 scripts/test_watchlist_scan.py
  .venv/bin/python3 scripts/test_watchlist_scan.py --live   # اختبار حي اختياري (SPY فقط)

لا يفتح شبكة إلا عند وسم --live، ولا يشغّل مسحاً كاملاً.
في النهاية يطبع: RESULT pass=N/N  ثم يخرج 0 عند النجاح و1 عند الفشل.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import watchlist
import gamma_scanner_v2 as gs

WATCHLIST_FILE = watchlist.WATCHLIST_PATH

_checks = []


def check(name, cond):
    _checks.append((name, bool(cond)))
    if not cond:
        print(f"FAIL: {name}", file=sys.stderr)


def test_load_counts():
    with open(WATCHLIST_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    loaded = watchlist.load_fahad()
    check("ملف فهد قابل للقراءة", loaded is not None)
    if loaded is None:
        return
    symbols, sector_of, yahoo_map, meta = loaded
    check("عدد الرموز = 40", len(symbols) == 40)
    check("total المعلَن مطابق", raw.get("total") == len(symbols))
    check("لا تكرار في الرموز", len(symbols) == len(set(symbols)))
    check("لكل رمز قطاع", all(s in sector_of for s in symbols))
    check("SELFTEST_MARKER موجود",
          getattr(watchlist, "SELFTEST_MARKER", None) == "SELFTEST: OK")


def test_sector_filter():
    semi = watchlist.symbols_by_sector(["أشباه الموصلات"])
    check("فلتر أشباه الموصلات = 6", len(semi) == 6)
    check("NVDA في أشباه الموصلات", "NVDA" in semi)
    space = watchlist.symbols_by_sector(["الفضاء"])
    check("فلتر الفضاء = 2", len(space) == 2)
    both = watchlist.symbols_by_sector(["أشباه الموصلات", "الفضاء"])
    check("فلتر قطاعين = 8", len(both) == 8)


def test_to_yahoo():
    loaded = watchlist.load_fahad()
    ymap = loaded[2] if loaded else {}
    check("SPX -> ^SPX", watchlist.to_yahoo("SPX", ymap) == "^SPX")
    check("NDX -> ^NDX", watchlist.to_yahoo("NDX", ymap) == "^NDX")
    check("GOLD -> GLD", watchlist.to_yahoo("GOLD", ymap) == "GLD")
    check("AAPL كما هو", watchlist.to_yahoo("AAPL", ymap) == "AAPL")


def test_limit_offset():
    full = gs.select_symbols(gs._parse_args([]))[0]
    check("بلا وسائط = 40", len(full) == 40)
    l3 = gs.select_symbols(gs._parse_args(["--limit", "3"]))[0]
    check("--limit 3 = 3", len(l3) == 3)
    check("--limit 3 نفس الترتيب", l3 == full[:3])
    l3o2 = gs.select_symbols(gs._parse_args(["--limit", "3", "--offset", "2"]))[0]
    check("--limit 3 --offset 2 = الرموز 3-5", l3o2 == full[2:5])


def test_explicit_and_positional():
    exp = gs.select_symbols(gs._parse_args(["--symbols", "AAPL,NVDA"]))[0]
    check("--symbols صريح", exp == ["AAPL", "NVDA"])
    pos = gs.select_symbols(gs._parse_args(["AAPL", "NVDA"]))[0]
    check("المسار القديم الموضعي = --symbols", pos == ["AAPL", "NVDA"])
    sec = gs.select_symbols(gs._parse_args(["--sectors", "الفضاء"]))[0]
    check("--sectors الفضاء = 2", sec == ["SPCX", "RKLB"])


def test_failure_path():
    check("ملف مفقود -> None", watchlist.load_fahad("/no/such/watchlist.json") is None)
    original = gs.load_fahad
    try:
        gs.load_fahad = lambda *a, **k: None
        syms, ymap = gs.select_symbols(gs._parse_args([]))
        check("فشل القراءة -> LEGACY_SYMBOLS", syms == watchlist.LEGACY_SYMBOLS)
    finally:
        gs.load_fahad = original


def test_list_no_network():
    import socket

    real_socket = socket.socket

    def _blocked(*a, **k):
        raise AssertionError("محاولة شبكة داخل --list")

    buf = io.StringIO()
    old_argv, old_stdout = sys.argv, sys.stdout
    try:
        socket.socket = _blocked
        sys.argv = ["gamma_scanner_v2.py", "--list"]
        sys.stdout = buf
        gs.main()
    finally:
        socket.socket = real_socket
        sys.argv, sys.stdout = old_argv, old_stdout
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    check("--list لا يفتح شبكة ويعمل", len(lines) >= 1)
    syms = lines[0].split(",") if lines else []
    check("--list يعرض 40 رمزاً", len(syms) == 40)
    check("--list الترتيب صحيح", syms[:5] == ["SPX", "SPY", "NDX", "QQQ", "GOLD"])


def main():
    test_load_counts()
    test_sector_filter()
    test_to_yahoo()
    test_limit_offset()
    test_explicit_and_positional()
    test_failure_path()
    test_list_no_network()

    total = len(_checks)
    passed = sum(1 for _, ok in _checks if ok)
    print(f"RESULT pass={passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    if "--live" in sys.argv[1:]:
        results = gs.scan(["SPY"], quiet=True)
        print("LIVE:", [(r["symbol"], r["signal"]) for r in results])
    sys.exit(main())
