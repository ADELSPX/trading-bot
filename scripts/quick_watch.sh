#!/bin/bash
# مراقب سريع — يفحص كل 5 ثواني ويحفظ السعر لملف
# الـ Python cron job يقرأ الملف ويحلل

SIGNAL_FILE="/root/trading-bot/data/active_signal.json"
PRICE_FILE="/root/trading-bot/data/current_price.txt"
BRIDGE_URL="http://localhost:7890"
VENV="/root/trading-bot/venv/bin/python3"

while true; do
    # جلب السعر
    PRICE=$(echo 'import yfinance as yf; s = yf.download("SPY", period="1d", progress=False); print(s["Close"].values[-1] * 10)' | timeout 10 $VENV 2>/dev/null)
    
    if [ -n "$PRICE" ]; then
        echo "$PRICE" > "$PRICE_FILE"
        echo "[$(date +%H:%M:%S)] SPX: $PRICE"
        
        # فحص الإشارة النشطة
        if [ -f "$SIGNAL_FILE" ]; then
            # نستعمل python لفحص المراحل
            echo "
import json
with open('$SIGNAL_FILE') as f:
    s = json.load(f)
price = $PRICE
entry_low = s['entry_zone'][0]
entry_high = s['entry_zone'][1]
stage = s.get('stage','pending')

if stage == 'pending' and entry_low <= price <= entry_high:
    print(f'🚀 ACTIVATED! Price={price:.0f} in zone {entry_low:.0f}-{entry_high:.0f}')
elif stage == 'active':
    direction = s['direction']
    if direction == 'PUT':
        if price <= s['target2']: print('🏆 T2 HIT!')
        elif price <= s['target1']: print('✅ T1 HIT!')
        elif price >= s['stop_loss']: print('🛑 STOPPED!')
    else:
        if price >= s['target2']: print('🏆 T2 HIT!')
        elif price >= s['target1']: print('✅ T1 HIT!')
        elif price <= s['stop_loss']: print('🛑 STOPPED!')
" | timeout 5 $VENV 2>/dev/null
        fi
    fi
    
    sleep 5
done