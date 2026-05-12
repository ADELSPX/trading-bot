"""
باك تست — اختبار الاستراتيجية على بيانات تاريخية
____________________________________________________
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot.strategy import StrategyEngine
from bot.indicators import TechnicalIndicators


def run_backtest():
    """
    محاكاة بسيطة — باك تست كامل لاحقاً
    """
    print("📊 Backtest — اختبار تاريخي")
    print("=" * 50)

    strategy = StrategyEngine()
    indicators = TechnicalIndicators()

    # محاكاة 10 إشارات
    test_signals = [
        {"price": 5840, "direction": "put", "confidence": 0.7,
         "expected_move_pct": 1.0, "available_strikes": [5800, 5820, 5840]},
        {"price": 5855, "direction": "put", "confidence": 0.6,
         "expected_move_pct": 0.8, "available_strikes": [5820, 5840, 5860]},
        {"price": 5830, "direction": "put", "confidence": 0.8,
         "expected_move_pct": 1.2, "available_strikes": [5780, 5800, 5820]},
    ]

    wins = 0
    losses = 0

    for i, signal in enumerate(test_signals):
        print(f"\n--- إشارة {i + 1} ---")
        fib = {"high": signal["price"] * 1.01, "low": signal["price"] * 0.99,
               "close": signal["price"]}
        fib_levels = indicators.fibonacci_levels(fib)

        delta = indicators.calculate_delta(
            underlying_price=signal["price"],
            strike=signal["available_strikes"][1] if len(signal["available_strikes"]) > 1 else signal["price"],
            time_to_expiry=2,
        )

        analysis = strategy.evaluate(signal, fib_levels, delta)

        print(f"السعر: ${signal['price']}")
        print(f"السترايك: {analysis.get('recommended_strike')}")
        print(f"الدلتا: {delta:.4f}")
        print(f"الهدف: ${analysis.get('target', 0):.2f}")

    print(f"\n✅ WIP: {wins} فوز, {losses} خسارة")
    print("باك تست كامل: قيد التطوير")


if __name__ == "__main__":
    run_backtest()
