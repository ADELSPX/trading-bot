"""
trading-bot core — المحرك الرئيسي
_______________________________________________
يدير دورة حياة الصفقة: إشارة → تحليل → تنفيذ → مراقبة → إغلاق
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional
from .strategy import StrategyEngine
from .indicators import TechnicalIndicators
from .risk import RiskManager
from .execution import OrderExecutor


@dataclass
class TradeConfig:
    """إعدادات التداول الأساسية"""
    symbol: str = "SPX"
    max_position_size: float = 1000.0  # الحد الأقصى للصفقة بالدولار
    target_profit_pct: float = 50.0    # الهدف % (نصف قيمة العقد)
    stop_loss_pct: float = 100.0       # وقف الخسارة % (خسارة كاملة)
    market_open: time = time(9, 30)    # افتتاح السوق (Eastern)
    market_close: time = time(16, 0)   # إغلاق السوق


class TradingBot:
    """
    المحرك الرئيسي للبوت
    - يستقبل الإشارات
    - يحلل باستخدام الاستراتيجيات
    - يدير المخاطر
    - ينفذ الأوامر
    """

    def __init__(self, config: TradeConfig = None):
        self.config = config or TradeConfig()
        self.strategy = StrategyEngine()
        self.indicators = TechnicalIndicators()
        self.risk = RiskManager(self.config)
        self.executor = OrderExecutor()
        self.active_trades: list = []

    def is_market_open(self) -> bool:
        """تحقق من وقت السوق — من الفديو الخامس"""
        now = datetime.now().time()
        return self.config.market_open <= now <= self.config.market_close

    def process_signal(self, signal: dict) -> Optional[dict]:
        """
        معالجة إشارة تداول — pipeline كامل
        """
        # 1. تحقق من وقت السوق
        if not self.is_market_open():
            print("⛔ السوق مقفل — تجاهل الإشارة")
            return None

        # 2. تحليل فيبوناتشي
        fib_levels = self.indicators.fibonacci_levels(signal.get("price_data", {}))

        # 3. حساب الدلتا (من الفديو الرابع)
        delta = self.indicators.calculate_delta(
            underlying_price=signal.get("price"),
            strike=signal.get("strike"),
            time_to_expiry=signal.get("days_to_expiry", 1),
            volatility=signal.get("iv", 20),
        )

        # 4. تقييم الاستراتيجية
        analysis = self.strategy.evaluate(
            signal=signal,
            fib_levels=fib_levels,
            delta=delta,
        )

        # 5. إدارة المخاطر
        risk_check = self.risk.evaluate(analysis, self.active_trades)

        if not risk_check["approved"]:
            print(f"⛔ رفضت الصفقة: {risk_check['reason']}")
            return None

        # 6. تنفيذ الأمر
        order = self.executor.place_order(
            symbol=self.config.symbol,
            strike=analysis["recommended_strike"],
            option_type=analysis["option_type"],
            quantity=risk_check["quantity"],
            order_type="LIMIT" if analysis.get("limit_price") else "MARKET",
            limit_price=analysis.get("limit_price"),
        )

        trade = {
            "id": len(self.active_trades) + 1,
            "symbol": self.config.symbol,
            "strike": analysis["recommended_strike"],
            "entry_price": order.get("filled_price"),
            "quantity": risk_check["quantity"],
            "delta": delta,
            "target": analysis["target"],
            "stop": risk_check["stop_loss"],
            "entered_at": datetime.now(),
            "status": "open",
        }
        self.active_trades.append(trade)

        print(f"✅ صفقة {trade['id']}: {trade['strike']} put × {trade['quantity']}")
        return trade

    def monitor_positions(self):
        """مراقبة الصفقات المفتوحة — P&L لحظة بلحظة"""
        for trade in self.active_trades:
            if trade["status"] != "open":
                continue

            current_price = self.executor.get_current_price(
                trade["symbol"], trade["strike"]
            )

            # معادلة الدلتا: حساب السعر المتوقع
            price_change = (current_price - trade["entry_price"])
            expected_move = price_change / trade["delta"]

            ply = (current_price - trade["entry_price"]) * trade["quantity"] * 100

            print(f"📊 صفقة {trade['id']}: P&L = ${ply:.2f}")

            # Check target
            if ply >= trade["target"]:
                self.close_trade(trade["id"], "هدف محقق ✅")
            elif ply <= -abs(trade["stop"]):
                self.close_trade(trade["id"], "وقف خسارة ⛔")

    def close_trade(self, trade_id: int, reason: str):
        """إغلاق صفقة — من الفديو الثالث"""
        for trade in self.active_trades:
            if trade["id"] == trade_id and trade["status"] == "open":
                self.executor.close_position(trade["symbol"], trade["strike"])
                trade["status"] = "closed"
                trade["closed_at"] = datetime.now()
                trade["close_reason"] = reason
                print(f"🔒 صفقة {trade_id} أغلقت: {reason}")
