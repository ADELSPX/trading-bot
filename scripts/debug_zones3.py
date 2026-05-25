#!/usr/bin/env python3
"""Debug: detailed evaluation of the closest zone"""
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

# Find closest zone
closest = min(sd.zones, key=lambda z: abs(z.mid - px))

print(f"SPX={px:.0f}")
print(f"Closest zone: {closest.zone_type.value} mid={closest.mid:.0f}")
print(f"  distal={closest.distal:.0f} proximal={closest.proximal:.0f} size={closest.size:.0f}")
print(f"  candles_inside={closest.num_candles_inside} pattern={closest.candle_pattern}")

# Manual evaluation
touches = sd._count_touches(closest, candles[-20:])
print(f"  touches in last 20 candles: {touches}")

rr = sd._calculate_rr(closest, px)
print(f"  R:R = {rr:.1f}")

exit_dist = abs(px - closest.proximal)
print(f"  exit_distance = {exit_dist:.0f}, zone_size*2 = {closest.size*2:.0f}")

has_exit = sd._has_full_candle_exit(closest, candles[-20:])
print(f"  full_candle_exit: {has_exit}")

exit_strength = sd._measure_exit_strength(closest, candles[-20:])
print(f"  exit_strength: {exit_strength}/5")

is_clean = sd._is_clean_zone(closest, candles[-20:])
print(f"  is_clean: {is_clean}")

location = sd._evaluate_location(closest, px)
print(f"  location_quality: {location}/3")

# Last 3 candles
print(f"\n  Last 3 candles:")
for c2 in candles[-3:]:
    print(f"    O={c2['open']:.0f} H={c2['high']:.0f} L={c2['low']:.0f} C={c2['close']:.0f}")
