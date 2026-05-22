"""
n8n Signal Bridge — ربط البوت مع n8n
_______________________________________
يشغل البوت على إشارة ويطبع JSON نظيف لـ n8n
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot.core import TradingBot
from config.settings import SYMBOLS


def run_signal(symbol="SPX", direction="put", price=None) -> dict:
    """تشغيل البوت على إشارة وإرجاع نتيجة JSON"""

    config = SYMBOLS.get(symbol)
    if not config:
        return {"status": "error", "reason": f"⚠️ {symbol} غير موجود في الإعدادات"}

    bot = TradingBot(config)

    # إشارة تجريبية — استبدلها بمصدر حقيقي لاحقاً
    signal = {
        "symbol": symbol,
        "price": price or 5840.50,
        "strike": round((price or 5840.50) / 10) * 10,
        "direction": direction,
        "confidence": 0.75,
        "expected_move_pct": 1.5,
        "days_to_expiry": 2,
        "iv": 18.5,
        "available_strikes": [5800, 5810, 5820, 5830, 5840, 5850, 5860],
        "price_data": {
            "high": 5870.00,
            "low": 5820.00,
            "close": price or 5840.50,
        },
    }

    trade = bot.process_signal(signal)

    if trade:
        return {
            "status": "signal",
            "symbol": symbol,
            "direction": direction,
            "entry": trade["entry_price"],
            "strike": trade["strike"],
            "quantity": trade["quantity"],
            "delta": trade["delta"],
            "target": trade["target"],
            "stop": trade["stop"],
            "id": trade["id"],
        }
    else:
        return {
            "status": "no_trade",
            "symbol": symbol,
            "direction": direction,
            "reason": "شروط السوق غير مناسبة حالياً",
        }


if __name__ == "__main__":
    # دعم تمرير arguments من n8n
    symbol = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    direction = sys.argv[2] if len(sys.argv) > 2 else "put"
    price = float(sys.argv[3]) if len(sys.argv) > 3 else None

    result = run_signal(symbol, direction, price)
    print(json.dumps(result, ensure_ascii=False, indent=2))
