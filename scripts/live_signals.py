"""
إشارات تداول حية — تحليل السوق وإصدار التوصيات
__________________________________________________
- جلب بيانات حية من yfinance
- تحليل فني (RSI, MACD, Bollinger, Moving Averages)
- تحليل فيبوناتشي
- تحليل بيئة الأوبشن
- إصدار توصيات مع الاستراتيجية المناسبة
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np

from bot.strategy import StrategyEngine
from bot.indicators import TechnicalIndicators
from bot.greeks import GreeksCalculator
from bot.risk import RiskManager
from bot.core import TradeConfig

# الأسهم المستهدفة
TARGET_SYMBOLS = ["SPX", "QQQ", "META", "TSLA"]


def fetch_price_data(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """جلب بيانات السعر"""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    return hist


def analyze_market(data: pd.DataFrame) -> dict:
    """تحليل السوق — المؤشرات الفنية"""
    close = data["Close"]
    high = data["High"]
    low = data["Low"]

    # RSI (14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    macd_hist = macd - signal
    macd_bullish = macd.iloc[-1] > signal.iloc[-1]

    # Moving Averages
    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else close.iloc[-1]
    sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else close.iloc[-1]
    price = close.iloc[-1]

    # Bollinger Bands
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + bb_std * 2
    bb_lower = bb_mid - bb_std * 2
    bb_position = (price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])

    # ATR
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift()),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    atr_pct = atr / price * 100

    # القرار
    signals = []
    if rsi < 30:
        signals.append("oversold")
    elif rsi > 70:
        signals.append("overbought")

    if macd_bullish:
        signals.append("macd_bullish")
    else:
        signals.append("macd_bearish")

    if price > sma_50:
        signals.append("trend_up")
    else:
        signals.append("trend_down")

    # اتجاه
    if rsi < 30 and macd_bullish:
        direction = "call"
        confidence = 0.7
    elif rsi > 70 and not macd_bullish:
        direction = "put"
        confidence = 0.7
    elif price > sma_20 and sma_20 > sma_50:
        direction = "call"
        confidence = 0.5
    elif price < sma_20 and sma_20 < sma_50:
        direction = "put"
        confidence = 0.5
    else:
        direction = "neutral"
        confidence = 0.3

    return {
        "price": round(price, 2),
        "direction": direction,
        "confidence": round(confidence, 2),
        "rsi": round(rsi, 1),
        "macd_bullish": bool(macd_bullish),
        "bb_position": round(bb_position, 2),
        "atr_pct": round(atr_pct, 2),
        "trend": "uptrend" if price > sma_50 else "downtrend",
        "signals": signals,
        "data": {
            "high": round(high.iloc[-1], 2),
            "low": round(low.iloc[-1], 2),
            "close": round(price, 2),
        },
    }


def generate_strikes(price: float, spread: float = 0.05, count: int = 6) -> list[float]:
    """توليد strikes حول السعر الحالي"""
    strikes = []
    for i in range(-count, count + 1):
        strikes.append(round(price * (1 + i * spread), 0))
    return sorted(set(s for s in strikes if s > 0))


def scan_all_symbols() -> list[dict]:
    """مسح جميع الأسهم المستهدفة"""
    results = []
    engine = StrategyEngine()

    for symbol in TARGET_SYMBOLS:
        try:
            print(f"🔍 تحليل {symbol}...")
            data = fetch_price_data(symbol)

            if data.empty:
                continue

            # تحليل السوق
            analysis = analyze_market(data)

            # توليد strikes
            strikes = generate_strikes(analysis["price"])

            # تقييم الاستراتيجيات
            strategies = engine.analyze(
                signal=analysis,
                price_data=analysis["data"],
                available_strikes=strikes,
                days_to_expiry=30,
            )

            # أفضل استراتيجية
            best = engine.best_strategy(
                signal=analysis,
                price_data=analysis["data"],
                available_strikes=strikes,
                days_to_expiry=30,
            )

            results.append({
                "symbol": symbol,
                "price": analysis["price"],
                "direction": analysis["direction"],
                "confidence": analysis["confidence"],
                "rsi": analysis["rsi"],
                "trend": analysis["trend"],
                "atr_pct": analysis["atr_pct"],
                "available_strategies": len(strategies),
                "best_strategy": best.name if best.approved else "لا يوجد",
                "best_profit": best.max_profit,
                "best_loss": best.max_loss,
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            print(f"❌ خطأ في {symbol}: {e}")

    return results


def print_signals(results: list[dict]):
    """طباعة الإشارات"""
    print("\n" + "📡 الإشارات الحية " + "=" * 40)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    for r in results:
        direction_icon = "🟢" if r["direction"] == "call" else "🔴" if r["direction"] == "put" else "🟡"
        print(f"{direction_icon} {r['symbol']} @ ${r['price']}")
        print(f"   الثقة: {r['confidence']*100:.0f}% | RSI: {r['rsi']} | الاتجاه: {r['trend']}")
        print(f"   أفضل استراتيجية: {r['best_strategy']}")
        if r['best_profit']:
            print(f"   الربح المحتمل: ${r['best_profit']:.0f}")
        print()


if __name__ == "__main__":
    print(f"🔄 فحص الأسهم المستهدفة: {', '.join(TARGET_SYMBOLS)}")

    signals = scan_all_symbols()

    print_signals(signals)

    # حفظ كـ JSON
    out_dir = "../data"
    os.makedirs(out_dir, exist_ok=True)
    out_file = f"{out_dir}/signals_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

    with open(out_file, "w") as f:
        json.dump(signals, f, indent=2, default=str)

    print(f"💾 الإشارات محفوظة: {out_file}")
