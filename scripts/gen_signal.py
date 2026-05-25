#!/usr/bin/env python3
"""توليد إشارة SPX وحفظها للمراقبة"""
import yfinance as yf, sys, json, os
sys.path.insert(0, '/root/trading-bot')

spy = yf.download('SPY', period='30d', progress=False)
c = spy['Close'].values.flatten()
spx = float(c[-1]) * 10

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
from bot.signal_builder import SignalBuilder

sd = SupplyDemandStrategy()
sd.detect_zones(candles)
sd.detect_trends(candles)
decision = sd.decide(candles, spx)
signal = SignalBuilder().build_signal(decision, spx, symbol='SPX')

if signal:
    print(f"SPX={spx:.0f} | SPY={float(c[-1]):.2f}")
    print(f"CONTRACT={signal.contract.full_symbol}")
    print(f"DIR={signal.contract.direction} | STRIKE={signal.contract.strike} | EXPIRY={signal.contract.expiry}")
    print(f"ENTRY={signal.entry_zone_low:.0f}-{signal.entry_zone_high:.0f}")
    print(f"STOP={signal.stop_loss:.0f} | T1={signal.target1:.0f} | T2={signal.target2:.0f}")
    print(f"CONF={signal.confidence:.0%} | {signal.confidence_label}")
    print(f"REASON={signal.reason}")

    # حفظ الإشارة للمراقبة التلقائية
    os.makedirs("/root/trading-bot/data", exist_ok=True)
    sig_data = {
        "entry_zone": [signal.entry_zone_low, signal.entry_zone_high],
        "stop_loss": signal.stop_loss,
        "target1": signal.target1,
        "target2": signal.target2,
        "direction": signal.contract.direction,
        "contract": signal.contract.full_symbol,
        "strike": signal.contract.strike,
        "expiry": signal.contract.expiry,
        "confidence": signal.confidence,
        "reason": signal.reason,
        "stage": "pending",
        "generated_at": signal.generated_at
    }
    with open("/root/trading-bot/data/active_signal.json", 'w') as f:
        json.dump(sig_data, f, indent=2, ensure_ascii=False)
    print("SAVED=active_signal.json ✅")
