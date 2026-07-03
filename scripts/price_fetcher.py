#!/usr/bin/env python3
"""Price Fetcher — يجيب السعر كل 30 ثانية ويحفظه"""
import time, json, subprocess, sys
from datetime import datetime

PRICE_FILE = "/root/trading-bot/data/current_price.txt"
SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
PYTHON = "/root/trading-bot/.venv/bin/python"

# كود جلب السعر (نمرره عبر stdin مو -c)
FETCH_CODE = """import yfinance as yf
s = yf.download('SPY', period='1d', progress=False)
print(s['Close'].values[-1] * 10)
"""

print(f"💰 Price Fetcher — كل 30 ثانية", flush=True)

while True:
    try:
        result = subprocess.run(
            [PYTHON], input=FETCH_CODE,
            capture_output=True, text=True, timeout=15
        )
        price = float(result.stdout.strip().strip('[]'))
        
        with open(PRICE_FILE, 'w') as f:
            f.write(str(price))
        
        # فحص الإشارة
        try:
            import json as _json
            with open(SIGNAL_FILE) as f:
                sig = _json.load(f)
            stage = sig.get('stage', 'pending')
            entry_low = sig['entry_zone'][0]
            entry_high = sig['entry_zone'][1]
            
            status = "⏳"
            if stage == "pending" and entry_low <= price <= entry_high:
                status = "🔥 داخل المنطقة!"
            elif stage == "active":
                status = "📊 نشط"
            elif stage in ("closed", "stopped", "target1_hit", "target2_hit"):
                status = f"✅ {stage}"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] SPX: {price:.0f} | {status} | Zone: {entry_low:.0f}-{entry_high:.0f}", flush=True)
        except:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] SPX: {price:.0f} | ⚠️ لا توجد إشارة", flush=True)
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ خطأ: {e}", flush=True)
    
    time.sleep(30)