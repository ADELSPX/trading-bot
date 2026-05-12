"""
إشارات تداول حية — Phase 1
________________________________
يجلب الإشارات من مصدر البيانات ويغذي البوت
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot.core import TradingBot
from config.settings import SYMBOLS


def process_mock_signal():
    """
    إشارة تجريبية — استبدلها بمصدر بيانات حقيقي لاحقاً
    """
    return {
        "symbol": "SPX",
        "price": 5840.50,
        "direction": "put",
        "confidence": 0.75,
        "expected_move_pct": 1.5,
        "days_to_expiry": 2,
        "iv": 18.5,
        "available_strikes": [5800, 5810, 5820, 5830, 5840, 5850, 5860],
        "price_data": {
            "high": 5870.00,
            "low": 5820.00,
            "close": 5840.50,
        },
    }


def main():
    print("🤖 Trading Bot — Phase 1: Live Signals")
    print("=" * 50)

    config = SYMBOLS.get("SPX")
    bot = TradingBot(config)

    signal = process_mock_signal()
    print(f"\n📡 إشارة: {signal['symbol']} {signal['direction']}")
    print(f"💰 السعر: ${signal['price']}")
    print(f"🎯 الثقة: {signal['confidence'] * 100:.0f}%")
    print(f"📈 التوقع: {signal['expected_move_pct']}%")

    trade = bot.process_signal(signal)

    if trade:
        print(f"\n✅ صفقة مفتوحة!")
        print(f"   Strike: {trade['strike']}")
        print(f"   الكمية: {trade['quantity']}")
        print(f"   الدلتا: {trade['delta']}")
        print(f"   دخلت: {trade['entered_at']}")
    else:
        print("\n⛔ لم ندخل — شروط السوق غير مناسبة")


if __name__ == "__main__":
    main()
