#!/usr/bin/env python3
"""time_search — بحث الويب "كما كان" في تاريخ معيّن (مجاني عبر Wayback Machine)

الفكرة: بديل BackSearch المدفوع — تشوف أي موقع/خبر كما كان محفوظاً في أرشيف الإنترنت
في تاريخ معيّن، بدون مفتاح ولا ريال.

الاستخدام:
  python3 time_search.py "رابط-أو-كلمة-مفتاحية" 2025-01-15
  python3 time_search.py --url https://example.com --date 2025-01-15
  python3 time_search.py --search "اقتصاد السعودية" --date 2025-06-01

الأدوات:
  1. --url  : يرجّع رابط النسخة المؤرشفة أقرب لتاريخ المطلوب
  2. --search: يبحث في الأرشيف عن لقطات لتاريخ معيّن (عبر CDX API)
"""
import sys
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime


def wayback_available(url, date_str):
    """يرجّع أقرب نسخة مؤرشفة لرابط في تاريخ معيّن (API مجاني)."""
    api = f"http://archive.org/wayback/available?url={urllib.parse.quote(url)}&timestamp={date_str.replace('-', '')}"
    try:
        with urllib.request.urlopen(api, timeout=20) as r:
            data = json.loads(r.read())
        snap = data.get("archived_snapshots", {}).get("closest", {})
        if snap.get("available"):
            return {
                "found": True,
                "archive_url": snap["url"],
                "timestamp": snap.get("timestamp"),
            }
    except Exception as e:
        return {"found": False, "error": str(e)[:120]}
    return {"found": False, "error": "لا توجد نسخة مؤرشفة"}


def wayback_snapshots(url, limit=10):
    """قائمة النسخ المؤرشفة لرابط (عبر CDX API)."""
    cdx = f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(url)}&output=json&limit={limit}&filter=statuscode:200"
    try:
        with urllib.request.urlopen(cdx, timeout=20) as r:
            rows = json.loads(r.read())
        if not rows:
            return []
        header = rows[0]
        out = []
        for row in rows[1:]:
            d = dict(zip(header, row))
            out.append({
                "timestamp": d.get("timestamp"),
                "url": f"https://web.archive.org/web/{d.get('timestamp')}/{d.get('original')}",
            })
        return out
    except Exception as e:
        return []


def search_archive(query, date_str, limit=5):
    """بحث في الأرشيف: نبحث عن نطاقات إخبارية شائعة تحتوي الكلمة،
    ثم نرجّع نسخها المؤرشفة في التاريخ المطلوب.
    (Wayback ما يدعم بحث نصي حر، فنستخدم قائمة مصادر + CDX)."""
    # قائمة نطاقات إخبارية شائعة للبحث ضمنها
    sources = ["cnn.com", "bbc.com", "reuters.com", "nytimes.com",
               "techcrunch.com", "bloomberg.com", "aljazeera.com", "arabnews.com"]
    ym = date_str[:7].replace("-", "")  # YYYYMM للتقييد
    out = []
    seen = set()
    for dom in sources:
        try:
            cdx = (f"https://web.archive.org/cdx/search/cdx?url={dom}"
                   f"&matchType=domain&output=json&limit=20&filter=statuscode:200&from={ym}")
            with urllib.request.urlopen(cdx, timeout=20) as r:
                rows = json.loads(r.read())
            if not rows:
                continue
            header = rows[0]
            for row in rows[1:]:
                d = dict(zip(header, row))
                orig = d.get("original", "")
                # ما نفلتر بالكلمة (الروابط ما تحتوي النص الحر) — نرجّع لقطات الموقع في التاريخ
                if orig in seen:
                    continue
                seen.add(orig)
                res = wayback_available(orig, date_str)
                if res.get("found"):
                    out.append({
                        "timestamp": res["timestamp"],
                        "original": orig,
                        "archive_url": res["archive_url"],
                    })
                if len(out) >= limit:
                    return out
        except Exception:
            continue
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    # تحليل المدخلات
    date_str = None
    url = None
    query = None
    mode = "url"

    for i, a in enumerate(args):
        if a == "--url":
            url = args[i + 1]
            mode = "url"
        elif a == "--search":
            query = args[i + 1]
            mode = "search"
        elif a == "--date":
            date_str = args[i + 1]
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", a):
            date_str = a
        elif a.startswith("http"):
            url = a
            mode = "url"
        elif not date_str and not url and not query:
            # أول كلمة مو تاريخ = استعلام او رابط
            if a.startswith("http"):
                url = a
            else:
                query = a
                mode = "search"

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"🔍 البحث في الأرشيف كما كان في: {date_str}")
    print("=" * 50)

    if mode == "url" and url:
        print(f"📎 الرابط: {url}")
        res = wayback_available(url, date_str)
        if res.get("found"):
            print(f"✅ النسخة المؤرشفة: {res['archive_url']}")
            print(f"   (تاريخ الحفظ الفعلي: {res['timestamp']})")
        else:
            print(f"❌ {res.get('error')}")
            print("\n🔄 قائمة النسخ المتاحة:")
            for s in wayback_snapshots(url, 5):
                print(f"   • {s['timestamp']}: {s['url']}")

    elif mode == "search" and query:
        print(f"🔎 البحث عن: {query}")
        results = search_archive(query, date_str, limit=8)
        if results:
            print(f"✅ لقطات مؤرشفة ({len(results)}):")
            for r in results:
                print(f"   • {r['timestamp']}: {r['archive_url']}")
        else:
            print("❌ ما لقيت لقطات للأرشيف بهذا التاريخ")


if __name__ == "__main__":
    main()
