#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فزّاع — قائمة مراقبة فهد (Gamma Fahad watchlist)

يقرأ ملف knowledge/watchlist_fahad.json (40 رمزاً في 15 قطاعاً) ويوفّر:
  - load_fahad(path)          -> (symbols, sector_of, yahoo_map, meta) أو None عند الفشل
  - symbols_by_sector(list)   -> فلترة الرموز بأسماء القطاعات العربية (تطابق تام أو احتواء)
  - to_yahoo(sym, yahoo_map)  -> رمز ياهو المقابل (SPX→^SPX، NDX→^NDX، GOLD→GLD)

عند فشل القراءة أو نقص الملف ترجع load_fahad القيمة None ويتطبع المستدعي
القائمة القديمة LEGACY_SYMBOLS — سلوك آمن بلا انفجار.
"""
import json

WATCHLIST_PATH = "/root/trading-bot/knowledge/watchlist_fahad.json"

LEGACY_SYMBOLS = ["AAPL", "NVDA", "TSLA", "META", "SPY", "QQQ"]

DEFAULT_YAHOO_MAP = {"SPX": "^SPX", "NDX": "^NDX", "GOLD": "GLD"}


def load_fahad(path=WATCHLIST_PATH):
    """يحمّل قائمة فهد.

    يرجّع رباعية (symbols, sector_of, yahoo_map, meta):
      symbols    : قائمة الرموز بترتيب القطاعات ثم الرموز داخلها، بلا تكرار
      sector_of  : قاموس الرمز -> اسم القطاع العربي
      yahoo_map  : قاموس رموز ياهو الخاصة (SPX/NDX/GOLD)
      meta       : بقية بيانات الملف (source/purpose/total/...)
    وعند أي فشل يرجع None.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        sectors = data.get("sectors")
        if not isinstance(sectors, dict) or not sectors:
            return None
        symbols = []
        sector_of = {}
        for sector, syms in sectors.items():
            if not isinstance(syms, list):
                continue
            for sym in syms:
                sym = str(sym).strip().upper()
                if not sym or sym in sector_of:
                    continue
                symbols.append(sym)
                sector_of[sym] = sector
        if not symbols:
            return None
        yahoo_map = {k: v for k, v in (data.get("yahoo_map") or {}).items()
                     if not str(k).startswith("_")}
        meta = {k: v for k, v in data.items() if k not in ("sectors", "yahoo_map")}
        return symbols, sector_of, yahoo_map, meta
    except Exception:
        return None


def symbols_by_sector(sectors):
    """يرجّع رموز القطاعات المطلوبة (مطابقة تامة أو احتواء بالاسم العربي).

    مثال: symbols_by_sector(["أشباه الموصلات"]) -> 6 رموز.
    """
    loaded = load_fahad()
    if loaded is None:
        return []
    symbols, sector_of, _yahoo_map, _meta = loaded
    wanted = [str(s).strip() for s in (sectors or []) if str(s).strip()]
    if not wanted:
        return list(symbols)
    out = []
    for sym in symbols:
        sec = sector_of.get(sym, "")
        if any(sec == w or w in sec or sec in w for w in wanted):
            out.append(sym)
    return out


def to_yahoo(sym, yahoo_map=None):
    """يرجّع رمز ياهو المناسب (SPX→^SPX، NDX→^NDX، GOLD→GLD)، وإلا الرمز كما هو."""
    if yahoo_map and sym in yahoo_map:
        return yahoo_map[sym]
    return DEFAULT_YAHOO_MAP.get(sym, sym)


SELFTEST_MARKER = "SELFTEST: OK"
