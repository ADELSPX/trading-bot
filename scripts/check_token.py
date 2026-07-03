#!/usr/bin/env python3
"""Check if bot token is valid"""
import json, urllib.request

with open("/root/trading-bot/scripts/telegram_bridge.py", "rb") as f:
    raw = f.read()
idx = raw.find(b"BOT_TOKEN")
region = raw[idx:idx+80]
q1 = region.find(b'"')
q2 = region.find(b'"', q1 + 1)
token = region[q1+1:q2].decode()

url = f"https://api.telegram.org/bot{token}/getMe"
req = urllib.request.Request(url)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print(json.dumps(result, ensure_ascii=False, indent=2))
