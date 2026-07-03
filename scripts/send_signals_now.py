#!/usr/bin/env python3
"""إرسال إشارات التداول على تيلجرام"""
import sys, json, urllib.request, urllib.parse

with open("/root/trading-bot/scripts/telegram_bridge.py", "rb") as f:
    raw = f.read()

# Extract token: find BOT_TOKEN, then quotes
idx = raw.find(b"BOT_TOKEN")
region = raw[idx:idx+80]
q1 = region.find(b'"')
q2 = region.find(b'"', q1 + 1)
token = region[q1+1:q2].decode()

CHAT_ID = "15036469"

msg = ("🚀 **Signal Engine v2.0** | 25-06-2026\n\n"
       "🇺🇸 **SPX 🟢 CALL** @ 7357.5\n"
       "   ارتداد من 🟡 أصفر | بين 🟡 أصفر و 🔵 أزرق\n"
       "   📈 طلب 0.61%\n"
       "   🎯 **T1:** 7409.0 → **T2:** 7467.9 | ⛔ **Stop:** 7298.6\n\n"
       "🚗 **TSLA 🟢 CALL** @ 376.8\n"
       "   ارتداد من 🟡 أصفر | بين 🟡 أصفر و 🔵 أزرق\n"
       "   📈 عرض 1.09%\n"
       "   🎯 **T1:** 379.4 → **T2:** 382.4 | ⛔ **Stop:** 373.8\n\n"
       "📊 **QQQ 🟢 CALL** @ 712.8\n"
       "   ارتداد من 🟡 أصفر | بين 🟡 أصفر و 🔵 أزرق\n"
       "   📈 عرض 0.66%\n"
       "   🎯 **T1:** 717.8 → **T2:** 723.5 | ⛔ **Stop:** 707.1\n\n"
       "⚡ إشارات آنية — قرارك مسؤوليتك")

data = urllib.parse.urlencode({
    "chat_id": CHAT_ID,
    "text": msg,
    "parse_mode": "Markdown",
}).encode()

url = f"https://api.telegram.org/bot{token}/sendMessage"
req = urllib.request.Request(url, data=data)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read())
    print(f"✅ Telegram sent: {result.get('ok')}", flush=True)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"❌ HTTP {e.code}: {body[:300]}", flush=True)
except Exception as e:
    print(f"❌ Error: {e}", flush=True)
