#!/usr/bin/env python3
"""Send test ping to Telegram - direct approach"""
import sys
import json
import urllib.request
import urllib.parse

# Read .env file as raw bytes
with open("/root/fazza-recovery/config/.env", "rb") as f:
    raw = f.read()

# Find token by scanning lines
lines = raw.split(b"\n")
token = None
for line in lines:
    if line.startswith(b"TELEGRAM_BOT_TOKEN="):
        token = line.split(b"=", 1)[1].strip().decode().strip('"').strip("'")
        break

if not token:
    # fallback to telegram_bridge.py
    with open("/root/trading-bot/scripts/telegram_bridge.py", "rb") as f:
        raw2 = f.read()
    for line in raw2.split(b"\n"):
        if b"BOT_TOKEN" in line and b"8474" in line:
            token = line.split(b"=", 1)[1].strip().decode().strip('"').strip("'")
            break

if not token:
    print("FAIL: could not read token")
    sys.exit(1)

print(f"Token ok (len={len(token)})", flush=True)

CHAT_ID = "15036469"
msg = "Test ping from Signal Engine v2 cron"

data = urllib.parse.urlencode({
    "chat_id": CHAT_ID,
    "text": msg,
    "parse_mode": "Markdown",
}).encode()

url = f"https://api.telegram.org/bot{token}/sendMessage"
req = urllib.request.Request(url, data=data)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print(f"Telegram API ok={result.get('ok')}", flush=True)
