"""
إرسال إشارة إلى Telegram Bridge
________________________________
ينادي الـ Webhook Bridge المحلي => يرسل تلغرام فوري

الاستخدام:
  python signal_alert.py --type entry --symbol SPX --direction put --entry 7406 --target1 7392 --stop 7412
  python signal_alert.py --type update --symbol SPX --pnl "+$42"
  python signal_alert.py --type close --symbol SPX --pnl "+$140"
"""

import json
import sys
import urllib.request


def send_signal(data: dict) -> bool:
    """إرسال إشارة إلى الـ Bridge"""
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        "http://localhost:7890",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=3)
        result = json.loads(resp.read())
        return result.get("status") == "sent"
    except Exception as e:
        print(f"❌ فشل الإرسال: {e}")
        return False


# إذا شغّلته من CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="إرسال إشارة تداول فورية")
    parser.add_argument("--type", required=True, choices=["entry", "update", "close"])
    parser.add_argument("--symbol", default="SPX")
    parser.add_argument("--direction", default="put")
    parser.add_argument("--entry", type=float)
    parser.add_argument("--target1", type=float)
    parser.add_argument("--target2", type=float)
    parser.add_argument("--stop", type=float)
    parser.add_argument("--delta")
    parser.add_argument("--ror")
    parser.add_argument("--pnl")
    parser.add_argument("--suggestion")
    parser.add_argument("--exit", type=float)
    parser.add_argument("--duration")
    parser.add_argument("--reason", default="")
    parser.add_argument("--note", default="للتحليل فقط")

    args = parser.parse_args()
    data = {k: v for k, v in vars(args).items() if v is not None}

    ok = send_signal(data)
    print("✅ تم" if ok else "❌ فشل")
