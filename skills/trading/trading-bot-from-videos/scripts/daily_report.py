#!/usr/bin/env python3
"""
تقرير التداول اليومي — تحليل SPY بالاستراتيجيات الثلاثة
═══════════════════════════════════════════════════════════
الاستخدام: python3 daily_report.py [--symbol SPY] [--save]

يقوم بـ:
  1. جلب بيانات SPY من yfinance (90 يوم)
  2. تحليل العرض والطلب (أبو ليلى) — اكتشاف المناطق + تقييم ٨ معايير
  3. تحليل القاما (أبو فهد) — استخراج الأبراج + إشارة الدخول
  4. طباعة تقرير عربي موجز

للتشغيل في cron: استخدم venv python
  /root/trading-bot/venv/bin/python /root/trading-bot/scripts/daily_report.py --save
"""

import sys, os, json, math, traceback, argparse
from datetime import datetime, date

sys.path.insert(0, '/root/trading-bot')


def fetch_spy_data():
    """جلب بيانات SPY من yfinance أو تحميلها من ملف محفوظ"""
    # المحاولة 1: ملف محفوظ أحدث من 24 ساعة
    data_path = '/root/trading-bot/data/spy_daily.json'
    if os.path.exists(data_path):
        mtime = os.path.getmtime(data_path)
        age_hours = (datetime.now().timestamp() - mtime) / 3600
        if age_hours < 24:
            with open(data_path) as f:
                saved = json.load(f)
            return saved['candles'], saved['current_price'], True

    # المحاولة 2: yfinance مباشر
    try:
        import yfinance as yf
        spy = yf.download('SPY', period='90d', progress=False, auto_adjust=True)
        if spy is not None and len(spy) > 0:
            candles = []
            for i in range(len(spy)):
                candles.append({
                    'open': float(spy['Open'].iloc[i]),
                    'high': float(spy['High'].iloc[i]),
                    'low': float(spy['Low'].iloc[i]),
                    'close': float(spy['Close'].iloc[i]),
                    'volume': float(spy['Volume'].iloc[i]) if 'Volume' in spy.columns else 0,
                })
            current_price = float(spy['Close'].iloc[-1])
            # حفظ للمرات القادمة
            os.makedirs('/root/trading-bot/data', exist_ok=True)
            with open(data_path, 'w') as f:
                json.dump({'candles': candles, 'current_price': current_price}, f)
            return candles, current_price, True
    except Exception as e:
        print(f"⚠️ yfinance فشل: {e}")

    # المحاولة 3: أي ملف محفوظ (حتى لو قديم)
    if os.path.exists(data_path):
        with open(data_path) as f:
            saved = json.load(f)
        return saved['candles'], saved['current_price'], True

    return [], 0, False


def simulate_intraday(daily_candles):
    """محاكاة شموع 5m و 15m من الشموع اليومية"""
    if not daily_candles:
        return [], []

    last = daily_candles[-1]
    daily_range = last['high'] - last['low']

    candles_15m = []
    for i in range(4):
        is_green = last['close'] > last['open']
        base = last['low'] + daily_range * i / 4
        candles_15m.append({
            'open': round(base, 2),
            'high': round(base + daily_range / 4 * 0.7, 2) if is_green else round(base + daily_range / 4 * 0.3, 2),
            'low': round(base - daily_range / 4 * 0.15, 2),
            'close': round(base + daily_range / 4 * 0.5, 2) if is_green else round(base + daily_range / 4 * 0.2, 2),
            'timestamp': i * 900,
        })

    candles_5m = []
    for c15 in candles_15m:
        for j in range(3):
            step = (c15['close'] - c15['open']) / 3
            candles_5m.append({
                'open': round(c15['open'] + step * j, 2),
                'high': round(max(c15['open'], c15['close']) + daily_range * 0.02, 2),
                'low': round(min(c15['open'], c15['close']) - daily_range * 0.02, 2),
                'close': round(c15['open'] + step * (j + 1), 2),
                'timestamp': c15['timestamp'] + j * 300,
            })

    return candles_5m, candles_15m


def main():
    parser = argparse.ArgumentParser(description='تقرير التداول اليومي')
    parser.add_argument('--symbol', default='SPY', help='رمز السهم (افتراضي: SPY)')
    parser.add_argument('--save', action='store_true', help='حفظ التقرير كـ JSON')
    args = parser.parse_args()

    today = date.today().strftime('%Y-%m-%d')
    print("=" * 60)
    print(f"  📊 تقرير التداول اليومي — {args.symbol}")
    print(f"  {today}")
    print("=" * 60)

    # ── جلب البيانات ──
    candles, current_price, ok = fetch_spy_data()
    if not ok:
        print("❌ تعذر جلب البيانات. الخروج.")
        return 1

    print(f"\n📈 {args.symbol}: ${current_price:.2f} | {len(candles)} شمعة")

    # مؤشرات سريعة
    ma50 = sum(c['close'] for c in candles[-50:]) / min(50, len(candles)) if len(candles) >= 5 else current_price
    ma200 = sum(c['close'] for c in candles[-200:]) / min(200, len(candles)) if len(candles) >= 5 else current_price
    print(f"   MA50: ${ma50:.2f} | MA200: ${ma200:.2f}")

    # ── العرض والطلب ──
    print("\n" + "=" * 60)
    print("  🔍 تحليل العرض والطلب — أبو ليلى")
    print("=" * 60)

    sd_decision = "neutral"
    sd_reason = ""
    sd_signal = None
    sd_demand_fresh = []
    sd_supply_fresh = []

    try:
        from bot.supply_demand_strategy import SupplyDemandStrategy, EntryDecision
        sd = SupplyDemandStrategy(symbol=args.symbol)
        sd.detect_zones(candles)
        sd.detect_trends(candles)

        for z in sd.zones:
            recent = candles[-20:] if len(candles) >= 20 else candles
            score = sd.evaluate_zone(z, current_price, recent)
            info = {
                'type': 'طلب' if z.zone_type.value == 'demand' else 'عرض',
                'state': z.state.value,
                'proximal': round(z.proximal, 2),
                'distal': round(z.distal, 2),
                'score': score,
            }
            if z.zone_type.value == 'demand' and z.state.value == 'fresh':
                sd_demand_fresh.append(info)
            elif z.zone_type.value == 'supply' and z.state.value == 'fresh':
                sd_supply_fresh.append(info)

        signal = sd.decide(candles, current_price)
        sd_signal = signal
        if signal.decision in (EntryDecision.BUY, EntryDecision.FLIP_BUY):
            sd_decision = "call"
        elif signal.decision in (EntryDecision.SELL, EntryDecision.FLIP_SELL):
            sd_decision = "put"
        sd_reason = signal.reason

        print(f"   مناطق طلب فريش: {len(sd_demand_fresh)}")
        for dz in sorted(sd_demand_fresh, key=lambda x: x['score'], reverse=True)[:3]:
            print(f"     ${dz['proximal']:.2f}–${dz['distal']:.2f} (Score: {dz['score']}/8)")
        print(f"   مناطق عرض فريش: {len(sd_supply_fresh)}")
        for sz in sorted(sd_supply_fresh, key=lambda x: x['score'], reverse=True)[:3]:
            print(f"     ${sz['proximal']:.2f}–${sz['distal']:.2f} (Score: {sz['score']}/8)")
        print(f"   القرار: {sd_decision.upper()} — {sd_reason}")
    except Exception as e:
        print(f"   ❌ فشل: {e}")

    # ── القاما ──
    print("\n" + "=" * 60)
    print("  ⚡ تحليل القاما — أبو فهد")
    print("=" * 60)

    gamma_direction = "neutral"
    gamma_reason = ""
    gamma_towers = []
    gamma_flip_points = []
    gamma_walls = []

    try:
        from bot.gamma_strategy import GammaStrategy, TowerStrength
        gs = GammaStrategy(symbol=args.symbol, target_profit_pct=30.0)

        # منحنى قاما تقريبي من Volume Profile
        price_levels = {}
        for c in candles:
            p = round(c['close'] / 5) * 5
            price_levels[p] = price_levels.get(p, 0) + c.get('volume', 30_000_000)

        max_oi = max(price_levels.values(), default=1)
        gamma_curve = []
        for price in sorted(price_levels.keys()):
            raw = price_levels[price]
            gamma_curve.append({
                'price': float(price),
                'gamma': round(raw / max_oi if price < current_price else -raw / max_oi, 4),
                'open_interest': raw,
            })

        towers = gs.extract_towers_from_gamma_curve(gamma_curve, current_price)
        candles_5m, candles_15m = simulate_intraday(candles)

        price_data = {
            'close': current_price,
            'high': max(c['high'] for c in candles[-10:]),
            'low': min(c['low'] for c in candles[-10:]),
            'ma200': ma200,
            'ma50': ma50,
        }

        analysis = gs.analyze(price_data, candles_5m, candles_15m)

        for t in analysis.towers:
            info = {'price': t.price, 'strength': t.strength.value, 'has_bus': t.has_bus, 'desc': t.description}
            gamma_towers.append(info)
            if t.strength == TowerStrength.RED:
                gamma_flip_points.append(info)
            elif t.strength in (TowerStrength.YELLOW, TowerStrength.BLUE):
                gamma_walls.append(info)

        print(f"   Flip Points 🔴: {len(gamma_flip_points)}")
        for fp in gamma_flip_points:
            print(f"     ${fp['price']:.2f} {'🚎' if fp['has_bus'] else ''}")
        print(f"   Gamma Walls 🟡🔵: {len(gamma_walls)}")
        for gw in gamma_walls[:3]:
            print(f"     ${gw['price']:.2f} ({gw['strength']}) {'🚎' if gw['has_bus'] else ''}")

        if analysis.entry:
            gamma_direction = analysis.entry.direction.value
            gamma_reason = analysis.entry.reason
            print(f"   إشارة: {gamma_direction.upper()} — {gamma_reason}")
            print(f"   دخول: ${analysis.entry.entry_price:.2f} | وقف: ${analysis.entry.stop_loss:.2f}")
        else:
            print(f"   ⏸️ لا توجد إشارة دخول")
    except Exception as e:
        print(f"   ❌ فشل: {e}")

    # ── التوصية ──
    print("\n" + "━" * 50)
    print("  🎯 توصية اليوم:")
    print("━" * 50)

    if sd_decision != "neutral" and sd_signal and sd_signal.confidence >= 0.5:
        d = "شراء CALL 🟢" if sd_decision == "call" else "بيع PUT 🔴"
        print(f"  الاستراتيجية: العرض والطلب (أبو ليلى) 📊")
        print(f"  الاتجاه: {d} | الثقة: {sd_signal.confidence:.0%}")
        print(f"  السبب: {sd_reason}")
        if sd_signal.entry_price > 0:
            print(f"  الدخول: ${sd_signal.entry_price:.2f} | الوقف: ${sd_signal.stop_loss:.2f} | R:R={sd_signal.risk_reward:.1f}:1")
    elif gamma_direction != "neutral":
        d = "شراء CALL 🟢" if gamma_direction == "call" else "بيع PUT 🔴"
        print(f"  الاستراتيجية: القاما (أبو فهد) 🚎")
        print(f"  الاتجاه: {d}")
        print(f"  السبب: {gamma_reason}")
    else:
        print(f"  الاستراتيجية: محايد — انتظار ⏸️")
        print(f"  لا توجد إشارة تداول واضحة")

    print("\n  ⚠️ تنبيهات:")
    warnings = []
    if current_price < ma200:
        warnings.append(f"السعر تحت MA200 (${ma200:.2f})")
    if current_price < ma50:
        warnings.append(f"السعر تحت MA50 (${ma50:.2f})")
    if sd_decision == "neutral" and gamma_direction == "neutral":
        warnings.append("لا توجد إشارات — التزم بالانتظار")
    for w in warnings:
        print(f"     • {w}")
    if not warnings:
        print(f"     ✅ لا توجد تنبيهات")

    # ── حفظ ──
    if args.save:
        os.makedirs('/root/trading-bot/reports', exist_ok=True)
        summary = {
            'date': today,
            'symbol': args.symbol,
            'current_price': current_price,
            'ma50': round(ma50, 2),
            'ma200': round(ma200, 2),
            'sd_decision': sd_decision,
            'sd_demand_fresh': len(sd_demand_fresh),
            'sd_supply_fresh': len(sd_supply_fresh),
            'gamma_flip_points': len(gamma_flip_points),
            'gamma_walls': len(gamma_walls),
            'gamma_direction': gamma_direction,
        }
        path = f'/root/trading-bot/reports/daily-{today}.json'
        with open(path, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n💾 تم الحفظ: {path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
