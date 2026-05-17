"""
باك تست الاستراتيجيات باستخدام backtesting.py
_______________________________________________
- اختبار المؤشرات الفنية (MA, MACD, Bollinger, RSI)
- تحسين المعاملات (Optimization)
- تقارير تفاعلية HTML
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
from typing import Optional, Callable


class TechnicalStrategy(Strategy):
    """
    استراتيجية أساسية — user-defined indicators + logic
    يورثها المستخدم عشان يضبط التاكتيك
    """

    # معلمات قابلة للتحسين
    ma_period = 20
    rsi_period = 14
    bullish_threshold = 70
    stop_loss_pct = 0.02

    def init(self):
        """
        تعريف المؤشرات — تشتغل مرة وحدة عند بداية الباك تست
        """
        import talib  # or use pandas

        # SMA
        self.sma = self.I(
            lambda x: pd.Series(x).rolling(self.ma_period).mean(),
            self.data.Close,
            name=f"SMA{self.ma_period}",
        )

        # RSI
        delta = pd.Series(self.data.Close).diff()
        gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        self.rsi = self.I(lambda: 100 - (100 / (1 + rs)), name="RSI")

    def next(self):
        """
        منطق التداول — ينادى كل شمعة
        """
        price = self.data.Close[-1]

        # شروط الدخول
        if not self.position:
            if self.rsi[-1] < self.bullish_threshold and self.data.Close[-1] > self.sma[-1]:
                self.buy(sl=price * (1 - self.stop_loss_pct))

        # شروط الخروج
        else:
            if self.rsi[-1] > 70:
                self.position.close()


def run_backtest(
    data: pd.DataFrame,
    strategy_class: type = TechnicalStrategy,
    cash: float = 10000,
    commission: float = 0.001,
    optimize_params: Optional[dict] = None,
) -> dict:
    """
    تشغيل باك تست

    Parameters:
        data: DataFrame بـ OHLCV (Open, High, Low, Close, Volume)
        strategy_class: كلاس الاستراتيجية (يورث من TechnicalStrategy)
        cash: رأس المال
        commission: نسبة العمولة (0.001 = 0.1%)
        optimize_params: معاملات للتحسين {param_name: [values]}

    Returns:
        dict: النتائج + الإحصائيات
    """
    bt = Backtest(
        data, strategy_class, cash=cash, commission=commission
    )

    if optimize_params:
        stats = bt.optimize(**optimize_params)
    else:
        stats = bt.run()

    return {
        "stats": stats,
        "equity_curve": stats._equity_curve,
        "trades": stats._trades,
        "return_pct": round(stats.get("Return [%]", 0), 2),
        "max_drawdown": round(stats.get("Max. Drawdown [%]", 0), 2),
        "sharpe": round(stats.get("Sharpe Ratio", 0), 2),
        "total_trades": stats.get("# Trades", 0),
        "win_rate": round(stats.get("Win Rate [%]", 0), 2),
        "avg_trade": round(stats.get("Avg. Trade [%]", 0), 2),
        "best_trade": round(stats.get("Best Trade [%]", 0), 2),
        "worst_trade": round(stats.get("Worst Trade [%]", 0), 2),
        "plot_file": None,
    }


def fetch_data(symbol: str, start: str, end: Optional[str] = None) -> pd.DataFrame:
    """
    جلب بيانات السوق من yfinance

    Parameters:
        symbol: رمز السهم (مثل SPY, QQQ, TSLA)
        start: تاريخ البداية (YYYY-MM-DD)
        end: تاريخ النهاية (اختياري — افتراضي: اليوم)

    Returns:
        DataFrame بـ OHLCV
    """
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start, end=end)

    if hist.empty:
        raise ValueError(f"ما لقينا بيانات لـ {symbol}")

    return hist
