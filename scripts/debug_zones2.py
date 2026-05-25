#!/usr/bin/env python3
"""Debug: evaluate closest zones"""
import yfinance as yf, sys
sys.path.insert(0, '/root/trading-bot')

spy = yf.download('SPY', period='30d', progress=False)
c = spy['Close'].values.flatten()
px = float(c[-1]) * 10

candles = []
for i in range(len(c)):
    candles.append({
        'open': float(spy['Open'].iloc[i]) * 10,
        'high': float(spy['High'].iloc[i]) * 10,
        'low': float(spy['Low'].iloc[i]) * 10,
        'close': float(c[i]) * 10,
        'index': i
    })

from bot.supply_demand_strategy import SupplyDemandStrategy
sd = SupplyDemandStrategy()
sd.detect_zones(candles)
sd.detect_trends(candles)

print(f"SPX={px:.0f}\n")
for z in sorted(sd.zones, key=lambda z: abs(z.mid - px)):
    dist = abs(px - z.mid) / px * 100
    score = sd.evaluate_zone(z, px, candles[-20:])
    proximity = 1.0 / (1.0 + dist * 100)
    final = (score/8 * 0.5) + (proximity * 0.5)
    print(f"  {z.zone_type.value:6s} | mid={z.mid:.0f} | dist={dist:.1f}% | score={score}/8 | prox={proximity:.2f} | final={final:.2f}")
