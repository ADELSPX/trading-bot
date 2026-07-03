#!/usr/bin/env python3
"""Dump byte-by-byte around the BOT_TOKEN line"""
with open("/root/trading-bot/scripts/telegram_bridge.py", "rb") as f:
    raw = f.read()
idx = raw.find(b"BOT_TOKEN")
region = raw[idx:idx+80]
print(f"hex: {region.hex()}")
# character dump
for i, b in enumerate(region):
    ch = chr(b) if 32 <= b < 127 else f"\\x{b:02x}"
    print(f"{i:3d}: {b:3d} 0x{b:02x} {ch}")
