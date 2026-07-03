#!/usr/bin/env python3
"""
🚀 Signal Engine v2.0 — مثل FAHAD_GAMMA
يدعم SPX + TSLA + QQQ
يرسل إشارات حية على تيلجرام
"""

import sys, os, json, time, urllib.request
from datetime import datetime

sys.path.insert(0, '/root/trading-bot')

DATA_FILE = "/root/trading-bot/data/current_price.txt"
SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
HISTORY_FILE = "/root/trading-bot/data/signal_history.json"
BRIDGE_URL = "http://localhost:7890"

SYMBOLS = {
    "SPX": {"yf": "SPY", "multiplier": 10},
    "TSLA": {"yf": "TSLA", "multiplier": 1},
    "QQQ": {"yf": "QQQ", "multiplier": 1},
}

def fetch_price(symbol_key):
    """جلب سعر الرمز"""
    import yfinance as yf
    info = SYMBOLS[symbol_key]
    yf_symbol = info["yf"]
    mult = info["multiplier"]

    data = yf.download(yf_symbol, period="1d", progress=False)
    if data.empty:
        data = yf.download(yf_symbol, period="2d", progress=False)
    
    close = float(data["Close"].values.flatten()[-1]) * mult
    high = float(data["High"].values.flatten()[-1]) * mult
    low = float(data["Low"].values.flatten()[-1]) * mult
    return close, high, low

def get_candles(yf_symbol, period="3mo", mult=10):
    """جلب شموع للتحليل"""
    import yfinance as yf
    data = yf.download(yf_symbol, period=period, progress=False)
    candles = []
    for i in range(len(data)):
        candles.append({
            'open': float(data['Open'].values.flatten()[i]) * mult,
            'high': float(data['High'].values.flatten()[i]) * mult,
            'low': float(data['Low'].values.flatten()[i]) * mult,
            'close': float(data['Close'].values.flatten()[i]) * mult,
            'index': i
        })
    return candles

def detect_towers(current_price):
    """محاكاة أبراج القاما (بدون بيانات SEC حقيقية)"""
    return [
        {'price': current_price * 0.985, 'label': '🟤 أحمر', 'strength': 'RED'},
        {'price': current_price * 0.993, 'label': '🟡 أصفر', 'strength': 'YELLOW'},
        {'price': current_price * 1.005, 'label': '🔵 أزرق', 'strength': 'BLUE'},
        {'price': current_price * 1.015, 'label': '⚪ أبيض', 'strength': 'WHITE'},
    ]

def analyze_symbol(symbol_key):
    """تحليل رمز كامل ← إشارة"""
    try:
        price, high, low = fetch_price(symbol_key)
        info = SYMBOLS[symbol_key]
        
        # تحليل العرض والطلب
        from bot.supply_demand_strategy import SupplyDemandStrategy
        candles = get_candles(info["yf"], "3mo", info["multiplier"])
        
        sd = SupplyDemandStrategy(symbol=symbol_key)
        sd.detect_zones(candles)
        sd.detect_trends(candles)
        
        # أقرب منطقة
        nearest_zone = None
        nearest_dist = float('inf')
        for zone in sd.zones:
            dist = abs(price - zone.mid) / price
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_zone = zone
        
        # أبراج القاما
        towers = detect_towers(price)
        tower_above = None
        tower_below = None
        for t in towers:
            if t['price'] > price and (tower_above is None or t['price'] < tower_above['price']):
                tower_above = t
            if t['price'] < price and (tower_below is None or t['price'] > tower_below['price']):
                tower_below = t
        
        # --- شجرة قرار أنماط القاما الـ 22 ---
        reasons = []
        direction = "WAIT"
        confidence = 0.0
        
        # نمط 16: عند البرج الأحمر — CALL
        if tower_below and tower_below['strength'] == 'RED':
            dist_to_red = (price - tower_below['price']) / tower_below['price']
            if dist_to_red < 0.015:
                confidence += 0.35
                reasons.append(f"عند البرج {tower_below['label']}")
        
        # نمط 12: عند الأصفر كارتداد — CALL
        if tower_below and tower_below['strength'] == 'YELLOW':
            dist_to_yellow = (price - tower_below['price']) / tower_below['price']
            if dist_to_yellow < 0.01:
                confidence += 0.25
                reasons.append(f"ارتداد من {tower_below['label']}")
        
        # نمط 10: بين أصفر وأزرق صاعد — CALL
        if tower_below and tower_above:
            if tower_below['strength'] == 'YELLOW' and tower_above['strength'] == 'BLUE':
                confidence += 0.15
                reasons.append(f"بين {tower_below['label']} و {tower_above['label']}")
        
        # نمط 13: عند الأصفر كمقاومة — PUT
        if tower_above and tower_above['strength'] == 'YELLOW':
            dist_above = (tower_above['price'] - price) / price
            if dist_above < 0.01:
                confidence += 0.25
                reasons.append(f"مقاومة {tower_above['label']}")
        
        # نمط 16/17: عند الأحمر
        if tower_below and tower_below['strength'] == 'RED':
            confidence += 0.20
        
        # مناطق العرض والطلب
        if nearest_zone:
            zone_type = nearest_zone.zone_type.value if hasattr(nearest_zone.zone_type, 'value') else str(nearest_zone.zone_type)
            zt = "🟢 طلب" if zone_type == 'demand' else "🔴 عرض"
            reasons.append(f"{zt} {nearest_dist:.2%}")
            
            if zone_type == 'demand' and nearest_dist < 0.02:
                confidence += 0.15
            elif zone_type == 'supply' and nearest_dist < 0.02:
                confidence += 0.15
        
        # القرار النهائي
        if confidence >= 0.40:
            dir_hints = sum(1 for r in reasons if 'مقاومة' in r or 'عرض' in r)
            call_hints = sum(1 for r in reasons if 'CALL' in r or 'طلب' in r or 'ارتداد' in r or 'أحمر' in r)
            
            if dir_hints > call_hints:
                direction = "PUT 🔴"
            else:
                direction = "CALL 🟢"
        elif confidence >= 0.25:
            if 'مقاومة' in str(reasons):
                direction = "PUT 🔴"
            else:
                direction = "CALL 🟢"
        
        # حساب الهدف والوقف
        target1 = None
        target2 = None
        stop = None
        if direction != "WAIT":
            if "PUT" in direction:
                stop = price * 1.008
                target1 = price * 0.993
                target2 = price * 0.985
            else:
                stop = price * 0.992
                target1 = price * 1.007
                target2 = price * 1.015
        
        return {
            'symbol': symbol_key,
            'price': round(price, 1),
            'direction': direction,
            'confidence': round(confidence, 2),
            'reasons': reasons,
            'target1': round(target1, 1) if target1 else None,
            'target2': round(target2, 1) if target2 else None,
            'stop': round(stop, 1) if stop else None,
            'timestamp': datetime.now().strftime('%H:%M'),
        }
    except Exception as e:
        return {'symbol': symbol_key, 'direction': 'ERROR', 'error': str(e)}

def send_telegram(text):
    """إرسال نص لتيلجرام عبر Bridge"""
    try:
        body = json.dumps({'text': text, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(BRIDGE_URL, data=body,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except:
        return False

def main():
    print(f"🔍 Signal Engine v2.0 — {datetime.now().isoformat()}", flush=True)
    
    signals = []
    for sym in ["SPX", "TSLA", "QQQ"]:
        result = analyze_symbol(sym)
        signals.append(result)
        print(f"\n{'='*40}", flush=True)
        print(f"📊 {result['symbol']} | {result.get('direction','?')} | {result.get('price','?')}", flush=True)
        if 'error' in result:
            print(f"❌ {result['error']}", flush=True)
        else:
            for r in result.get('reasons', []):
                print(f"   • {r}", flush=True)
            if result.get('direction') != 'WAIT':
                print(f"   🎯 T1: {result['target1']} | T2: {result['target2']} | ⛔ {result['stop']}", flush=True)
    
    # إرسال إذا فيه إشارات نشطة — بصيغة JSON اللي يفهمها Telegram Bridge
    active_signals = [s for s in signals if s['direction'] not in ['WAIT', 'ERROR']]
    if active_signals:
        all_sent = True
        for s in active_signals:
            dir_clean = s['direction'].replace(' 🟢', '').replace(' 🔴', '').strip()
            zone_type = "طلب" if any('طلب' in r for r in s.get('reasons',[])) else "عرض"
            bridge_msg = {
                'type': 'entry',
                'symbol': s['symbol'],
                'direction': dir_clean,
                'entry': s['price'],
                'signal_type': f'مضاربة سريعة | {zone_type}',
                'target1': s['target1'],
                'target2': s['target2'],
                'stop': s['stop'],
                'note': 'Signal Engine v2.0 | ' + ' | '.join(s.get('reasons',[])[:2])
            }
            try:
                body = json.dumps(bridge_msg).encode()
                req = urllib.request.Request(BRIDGE_URL, data=body,
                    headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                print(f"   ❌ فشل إرسال {s['symbol']}: {e}", flush=True)
                all_sent = False
        print(f"\n📨 تيلجرام: {'تم ✅' if all_sent else 'بعضها فشل ❌'}", flush=True)
    
    # حفظ للسجل
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
    except:
        pass

if __name__ == "__main__":
    main()
