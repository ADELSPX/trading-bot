#!/usr/bin/env python3
"""
🚀 محرك الإشارات الحي — Signal Engine v1.0
يجيب السعر ← يحلل العرض/الطلب ← القاما ← يقرر CALL/PUT/WAIT ← يحفظ ← يرسل
يجري كل 30 دقيقة (أو عند الطلب)
"""

import sys, os, json, time, urllib.request
from datetime import datetime

sys.path.insert(0, '/root/trading-bot')

# --- الإعدادات ---
DATA_FILE = "/root/trading-bot/data/current_price.txt"
SIGNAL_FILE = "/root/trading-bot/data/active_signal.json"
HISTORY_FILE = "/root/trading-bot/data/signal_history.json"
BRIDGE_URL = "http://localhost:7890"

# --- جلب السعر ---
def fetch_spx():
    import yfinance as yf
    spy = yf.download("SPY", period="1d", progress=False)
    if spy.empty:
        spy = yf.download("SPY", period="2d", progress=False)
    close = spy["Close"].values.flatten()[-1]
    high = spy["High"].values.flatten()[-1]
    low = spy["Low"].values.flatten()[-1]
    spx_price = float(close) * 10
    spx_high = float(high) * 10
    spx_low = float(low) * 10
    return spx_price, spx_high, spx_low

# --- تحليل العرض والطلب ---
def analyze_supply_demand(current_price):
    from bot.supply_demand_strategy import SupplyDemandStrategy
    import yfinance as yf

    spy = yf.download("SPY", period="30d", progress=False)
    candles = []
    for i in range(len(spy)):
        candles.append({
            'open': float(spy['Open'].values.flatten()[i]) * 10,
            'high': float(spy['High'].values.flatten()[i]) * 10,
            'low': float(spy['Low'].values.flatten()[i]) * 10,
            'close': float(spy['Close'].values.flatten()[i]) * 10,
            'index': i
        })

    sd = SupplyDemandStrategy(symbol="SPX")
    sd.detect_zones(candles)
    sd.detect_trends(candles)

    # البحث عن أقرب منطقة
    nearest_zone = None
    nearest_distance = float('inf')

    for zone in sd.zones:
        zone_mid = zone.mid
        dist = abs(current_price - zone_mid) / current_price
        if dist < nearest_distance:
            nearest_distance = dist
            nearest_zone = zone

    best_signal = sd.decide(candles, current_price) if hasattr(sd, 'decide') else None
    return sd, nearest_zone, nearest_distance, best_signal

# --- تحليل القاما ---
def analyze_gamma(current_price):
    from bot.gamma_strategy import GammaStrategy, Direction, TowerStrength

    gs = GammaStrategy(symbol="SPX", target_profit_pct=30.0)

    # محاكاة شمعات 5m و 15m من الشمعة اليومية
    import yfinance as yf
    spy_5d = yf.download("SPY", period="5d", progress=False)
    candles_5m = []
    candles_15m = []

    for i in range(len(spy_5d)):
        base = {
            'open': float(spy_5d['Open'].values.flatten()[i]) * 10,
            'high': float(spy_5d['High'].values.flatten()[i]) * 10,
            'low': float(spy_5d['Low'].values.flatten()[i]) * 10,
            'close': float(spy_5d['Close'].values.flatten()[i]) * 10,
        }
        # محاكاة 3 شمعات 5m و 1 شمعة 15m من اليومية
        for j in range(3):
            candles_5m.append({**base, 'index': i*3+j})
        candles_15m.append({**base, 'index': i})

    # أبراج قاما محاكاة (بدون بيانات SEC حقيقية — استخدام مناطق عرض/طلب كتقريب)
    from bot.gamma_strategy import TowerStrength
    towers = [
        {'price': current_price * 0.985, 'strength': TowerStrength.RED},
        {'price': current_price * 0.993, 'strength': TowerStrength.YELLOW},
        {'price': current_price * 1.005, 'strength': TowerStrength.BLUE},
        {'price': current_price * 1.015, 'strength': TowerStrength.WHITE},
    ]

    analysis = gs.analyze(
        price_data={'close': current_price, 'high': current_price*1.005, 'low': current_price*0.995},
        candles_5m=candles_5m[-20:],
        candles_15m=candles_15m[-10:],
    )

    # تحديد أقرب برج
    nearest_tower_above = None
    nearest_tower_below = None
    for t in towers:
        if t['price'] > current_price:
            if nearest_tower_above is None or t['price'] < nearest_tower_above['price']:
                nearest_tower_above = t
        if t['price'] < current_price:
            if nearest_tower_below is None or t['price'] > nearest_tower_below['price']:
                nearest_tower_below = t

    return towers, nearest_tower_above, nearest_tower_below, analysis

# --- اتخاذ القرار ---
def decide_call_put(current_price, sd_analysis, gamma_analysis):
    sd, nearest_zone, zone_distance, best_signal = sd_analysis
    towers, tower_above, tower_below, gamma_result = gamma_analysis

    reasons = []
    confidence = 0.0
    direction = "WAIT"

    # 1. تحليل العرض والطلب
    if nearest_zone:
        zone_type = nearest_zone.zone_type.value if hasattr(nearest_zone.zone_type, 'value') else str(nearest_zone.zone_type)
        zone_mid = nearest_zone.mid

        if zone_type == 'demand' and current_price > zone_mid and zone_distance < 0.02:
            # فوق منطقة طلب — قريب منها — احتمال CALL
            confidence += 0.25
            reasons.append(f"منطقة طلب 🔵 {zone_distance:.1%}")

        elif zone_type == 'supply' and current_price < zone_mid and zone_distance < 0.02:
            # تحت منطقة عرض — قريب منها — احتمال PUT
            confidence += 0.25
            reasons.append(f"منطقة عرض 🔴 {zone_distance:.1%}")

    # 2. تحليل القاما — الأبراج
    if tower_above and tower_below:
        if tower_below['price'] > current_price * 0.99:  # قريب من الدعم
            confidence += 0.25
            strength_name = tower_below['strength'].name if hasattr(tower_below['strength'], 'name') else str(tower_below['strength'])
            reasons.append(f"فوق برج {strength_name} 🗼")

        if tower_above['price'] < current_price * 1.01:  # قريب من المقاومة
            confidence += 0.20
            strength_name = tower_above['strength'].name if hasattr(tower_above['strength'], 'name') else str(tower_above['strength'])
            reasons.append(f"تحت برج {strength_name} 🗼")

    # 3. الاتجاه العام
    if best_signal:
        if hasattr(best_signal, 'decision'):
            if best_signal.decision in ['BUY', 'CALL']:
                confidence += 0.15
                reasons.append(f"إشارة {best_signal.decision}")
            elif best_signal.decision in ['SELL', 'PUT']:
                confidence += 0.15
                reasons.append(f"إشارة {best_signal.decision}")

    # 4. القرار النهائي
    if confidence >= 0.35:
        if 'supply' in str(reasons) or 'تحت' in str(reasons):
            direction = "PUT"
        else:
            direction = "CALL"
    elif confidence >= 0.20:
        if 'supply' in str(reasons) and tower_above and tower_above['price'] < current_price * 1.005:
            direction = "PUT"
        elif 'demand' in str(reasons) and tower_below and tower_below['price'] > current_price * 0.995:
            direction = "CALL"
        else:
            direction = "WAIT"
    else:
        direction = "WAIT"

    return direction, confidence, reasons

# --- إرسال التنبيه ---
def send_alert(direction, price, confidence, reasons):
    # حفظ الإشارة أولاً
    signal = {
        'timestamp': datetime.now().isoformat(),
        'direction': direction,
        'price': price,
        'confidence': round(confidence, 2),
        'reasons': reasons,
        'contract': f"SPXW {datetime.now().strftime('%y%m%d')}" if direction != 'WAIT' else None,
    }

    with open(SIGNAL_FILE, 'w') as f:
        json.dump(signal, f, ensure_ascii=False, indent=2)

    # حفظ التاريخ
    history = []
    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    except:
        pass
    history.append(signal)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-50:], f, ensure_ascii=False, indent=2)

    # إرسال عبر Telegram Bridge
    if direction != 'WAIT' and confidence >= 0.20:
        try:
            msg = f"🚀 {direction} | SPX {price:.0f} | ثقة {confidence:.0%}"
            if reasons:
                msg += f"\n💡 {' | '.join(reasons[:3])}"
            body = json.dumps({
                'text': msg,
                'chat_id': 'telegram',  # يرسل للدردشة الحالية
                'parse_mode': 'HTML'
            }).encode()
            req = urllib.request.Request(BRIDGE_URL, data=body,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except:
            pass  # البريدج مش شغال

    return signal

# --- الرئيسي ---
def main():
    print(f"🔍 Signal Engine — {datetime.now().isoformat()}", flush=True)

    try:
        spx_price, spx_high, spx_low = fetch_spx()
        print(f"📊 SPX: {spx_price:.1f} (H:{spx_high:.0f} L:{spx_low:.0f})", flush=True)

        # حفظ السعر
        with open(DATA_FILE, 'w') as f:
            f.write(str(spx_price))

        # تحليل
        sd_result = analyze_supply_demand(spx_price)
        gamma_result = analyze_gamma(spx_price)

        direction, confidence, reasons = decide_call_put(spx_price, sd_result, gamma_result)

        if direction != "WAIT":
            signal = send_alert(direction, spx_price, confidence, reasons)
            print(f"🟢 إشارة: {direction} | ثقة {confidence:.0%} | {spx_price:.0f}", flush=True)
            for r in reasons:
                print(f"   • {r}", flush=True)
        else:
            print(f"⚪ انتظار — لا توجد إشارة قوية (أعلى ثقة: {confidence:.0%})", flush=True)

        # طباعة التقارير
        sd, nearest_zone, zone_dist, best_signal = sd_result
        if nearest_zone:
            print(f"   أقرب منطقة: {nearest_zone.zone_type.value.upper() if hasattr(nearest_zone.zone_type, 'value') else str(nearest_zone.zone_type).upper()} | بعد {zone_dist:.2%}", flush=True)

    except Exception as e:
        print(f"❌ خطأ: {e}", flush=True)

if __name__ == "__main__":
    main()
