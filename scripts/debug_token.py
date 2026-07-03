#!/usr/bin/env python3
"""Debug: show what positions are found"""
import sys

with open("/root/trading-bot/scripts/telegram_bridge.py", "rb") as f:
    raw = f.read()

# Find BOT_TOKEN
idx = raw.find(b"BOT_TOKEN")
print(f"BOT_TOKEN at byte {idx}", flush=True)

# Show the 80 bytes starting from there
region = raw[idx:idx+80]
print(f"Region ({len(region)} bytes): {region}", flush=True)

# Find equals sign
eq = region.find(b"=")
print(f"Equals at offset {eq}", flush=True)

# Find first quote after equals
q1 = region.find(b'"', eq)
print(f"First quote at offset {q1}", flush=True)

# Find second quote after q1
q2 = region.find(b'"', q1 + 1)
print(f"Second quote at offset {q2}", flush=True)

if q1 >= 0 and q2 > q1:
    token = region[q1+1:q2]
    print(f"Token bytes ({len(token)}): {token}", flush=True)
    token_str = token.decode()
    print(f"Token string: {token_str}", flush=True)
    print(f"Token length: {len(token_str)}", flush=True)
