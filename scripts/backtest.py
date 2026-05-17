"""
باك تست متقدم — اختبار الاستراتيجيات على بيانات تاريخية حقيقية
______________________________________________________________
- باك تست المؤشرات الفنية (MA, RSI, MACD, Bollinger)
- باك تست الاستراتيجيات الأساسية (شراء/بيع)
- محاكاة Iron Condor على بيانات تاريخية
- تقارير HTML تفاعلية
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy

from bot.strategy import StrategyEngine
from bot.greeks import GreeksCalculator


class MACrossoverStrategy(Strategy):
    """استراتيجية تقاطع متوسطين — بيع/شراء"""
    fast_ma = 10
    slow_ma = 30

    def init(self):
        self.fast = self.I(
            lambda x: pd.Series(x).rolling(self.fast_ma).mean(),
            self.data.Close, name=f"SMA{self.fast_ma}"
        )
        self.slow = self.I(
            lambda x: pd.Series(x).rolling(self.slow_ma).mean(),
            self.data.Close, name=f"SMA{self.slow_ma}"
        )

    def next(self):
        if not self.position:
            if self.fast[-1] > self.slow[-1] and self.fast[-2] <= self.slow[-2]:
                self.buy()
            elif self.fast[-1] < self.slow[-1] and self.fast[-2] >= self.slow[-2]:
                self.sell()
        else:
            if self.position.is_long and self.fast[-1] < self.slow[-1]:
                self.position.close()
            elif self.position.is_short and self.fast[-1] > self.slow[-1]:
                self.position.close()


class RSIStrategy(Strategy):
    """استراتيجية RSI — شراء عند ذروة البيع، بيع عند ذروة الشراء"""
    rsi_period = 14
    oversold = 30
    overbought = 70

    def init(self):
        delta = pd.Series(self.data.Close).diff()
        gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        self.rsi = self.I(lambda: 100 - (100 / (1 + rs)), name="RSI")

    def next(self):
        if not self.position:
            if self.rsi[-1] < self.oversold:
                self.buy()
            elif self.rsi[-1] > self.overbought:
                self.sell()
        else:
            if self.position.is_long and self.rsi[-1] > 50:
                self.position.close()
            elif self.position.is_short and self.rsi[-1] < 50:
                self.position.close()


def fetch_data(symbol: str, start: str, end: Optional[str] = None) -> pd.DataFrame:
    """جلب بيانات السوق — yfinance"""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start, end=end)

    if hist.empty:
        raise ValueError(f"ما لقينا بيانات لـ {symbol} من {start}")

    return hist


def run_technical_backtest(
    symbol: str = "QQQ",
    start: str = "2024-01-01",
    strategy_type: str = "macd",
    cash: float = 10000,
    optimize: bool = False,
) -> dict:
    """
    تشغيل باك تست للمؤشرات الفنية
    """
    print(f"📊 جلب بيانات {symbol} من {start}...")
    data = fetch_data(symbol, start)

    strat_map = {
        "macd": MACrossoverStrategy,
        "rsi": RSIStrategy,
    }

    strategy_class = strat_map.get(strategy_type, MACrossoverStrategy)

    print(f"⚙️ تشغيل {strategy_type} باك تست...")
    bt = Backtest(data, strategy_class, cash=cash, commission=.001)

    if optimize:
        print("🔍 تحسين المعاملات...")
        if strategy_type == "macd":
            stats = bt.optimize(
                fast_ma=range(5, 30, 5),
                slow_ma=range(20, 60, 10),
                maximize="Return [%]",
            )
        else:
            stats = bt.optimize(
                rsi_period=range(7, 21, 3),
                oversold=range(20, 40, 5),
                overbought=range(60, 80, 5),
                maximize="Return [%]",
            )
    else:
        stats = bt.run()

    # حفظ التقرير
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    plot_file = f"{reports_dir}/{symbol}_{strategy_type}_{start}.html"
    try:
        bt.plot(filename=plot_file, open_browser=False)
        print(f"📈 التقرير: {plot_file}")
    except Exception as e:
        print(f"⚠️ فشل الرسم: {e}")
        plot_file = None

    return {
        "symbol": symbol,
        "strategy": strategy_type,
        "period": f"{start} → {datetime.now().strftime('%Y-%m-%d')}",
        "return_pct": round(stats.get("Return [%]", 0), 2),
        "max_drawdown": round(stats.get("Max. Drawdown [%]", 0), 2),
        "sharpe": round(stats.get("Sharpe Ratio", 0), 2),
        "total_trades": stats.get("# Trades", 0),
        "win_rate": round(stats.get("Win Rate [%]", 0), 2),
        "avg_trade": round(stats.get("Avg. Trade [%]", 0), 2),
        "best_trade": round(stats.get("Best Trade [%]", 0), 2),
        "worst_trade": round(stats.get("Worst Trade [%]", 0), 2),
        "profit_factor": round(stats.get("Profit Factor", 0), 2),
        "sqn": round(stats.get("SQN", 0), 2),
        "plot_file": plot_file,
    }


def analyze_options_environment(
    symbol: str = "SPX",
    start: str = "2025-01-01",
) -> dict:
    """
    تحليل بيئة الأوبشن — هل Iron Condor مناسبة الآن؟
    بناءً على:
    - ATR (Average True Range) — هل السوق هادئ؟
    - RSI — هل في ذروة شراء/بيع؟
    - Bollinger Bands — هل السوق ممتد؟
    """
    data = fetch_data(symbol, start)

    # حساب ATR
    high_low = data["High"] - data["Low"]
    high_close = abs(data["High"] - data["Close"].shift())
    low_close = abs(data["Low"] - data["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean().iloc[-1]
    atr_pct = atr_14 / data["Close"].iloc[-1] * 100

    # حساب RSI
    delta = data["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_last = rsi.iloc[-1]

    # Bollinger Bands
    sma_20 = data["Close"].rolling(20).mean()
    std_20 = data["Close"].rolling(20).std()
    bb_width = ((data["Close"].iloc[-1] - sma_20.iloc[-1]) / std_20.iloc[-1])

    # هل السوق مناسب لـ Iron Condor؟
    ic_suitable = atr_pct < 1.5 and 30 < rsi_last < 70 and abs(bb_width) < 2
    iv_suitable = atr_pct > 2.0  # للتقلب العالي

    return {
        "symbol": symbol,
        "last_price": round(data["Close"].iloc[-1], 2),
        "atr_14_pct": round(atr_pct, 2),
        "rsi": round(rsi_last, 1),
        "bb_position": round(bb_width, 2),
        "iron_condor_suitable": bool(ic_suitable),
        "strangle_suitable": bool(iv_suitable),
        "recommendation": (
            "Iron Condor 🦅" if ic_suitable else
            "Strangle/Straddle" if iv_suitable else
            "انتظار فرصة أفضل"
        ),
    }


def print_results(results: dict):
    """طباعة النتائج بشكل مرتب"""
    print("\n" + "=" * 55)
    print(f"📊 {results.get('symbol', 'N/A')} | {results.get('strategy', 'N/A')}")
    print(f"📅 {results.get('period', 'N/A')}")
    print("=" * 55)
    print(f"💰 العائد:            {results.get('return_pct', 0):>8.2f}%")
    print(f"📉 أقصى خسارة:       {results.get('max_drawdown', 0):>8.2f}%")
    print(f"📈 Sharpe:            {results.get('sharpe', 0):>8.2f}")
    print(f"🔄 الصفقات:           {results.get('total_trades', 0):>8}")
    print(f"🎯 نسبة الفوز:        {results.get('win_rate', 0):>8.2f}%")
    print(f"💰 متوسط الصفقة:      {results.get('avg_trade', 0):>8.2f}%")
    print(f"🏆 أفضل صفقة:         {results.get('best_trade', 0):>8.2f}%")
    print(f"💀 أسوأ صفقة:         {results.get('worst_trade', 0):>8.2f}%")
    print(f"📊 Profit Factor:     {results.get('profit_factor', 0):>8.2f}")
    if results.get("plot_file"):
        print(f"📈 التقرير: {results['plot_file']}")
    print("=" * 55)
