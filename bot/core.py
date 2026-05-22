"""
trading-bot core — المحرك الرئيسي (مُحدّث)
_______________________________________________
يدير دورة حياة الصفقة: إشارة → تحليل (9 استراتيجيات) → تنفيذ → مراقبة → إغلاق
"""

from datetime import datetime, time
from typing import Optional

from .strategy import StrategyEngine
from .indicators import TechnicalIndicators
from .greeks import GreeksCalculator
from .risk import RiskManager
from .execution import OrderExecutor
from .models import TradeConfig


class TradingBot:
    """
    المحرك الرئيسي للبوت — يدعم الاستراتيجيات المتعددة (9)
    """

    def __init__(self, config: Optional[TradeConfig] = None):
        self.config = config or TradeConfig()
        self.strategy = StrategyEngine()
        self.indicators = TechnicalIndicators()
        self.greeks = GreeksCalculator()
        self.risk = RiskManager(self.config, self.config.account_balance)
        self.executor = OrderExecutor()
        self.active_trades: list[dict] = []

    def is_market_open(self) -> bool:
        now = datetime.now().time()
        return self.config.market_open <= now <= self.config.market_close

    def process_signal(self, signal: dict) -> Optional[dict]:
        """
        معالجة إشارة تداول — pipeline كامل باستخدام 9 استراتيجيات
        """
        if not self.is_market_open():
            print("⛔ السوق مقفل — تجاهل الإشارة")
            return None

        price = signal.get("price", 0)

        # 1. فيبوناتشي
        fib_levels = self.indicators.fibonacci_levels(signal.get("price_data", {}))

        # 2. توليد strikes حول السعر
        strikes = self._generate_strikes(price)

        # 3. تحليل جميع الاستراتيجيات + اختيار الأفضل
        best = self.strategy.best_strategy(
            signal=signal,
            price_data=signal.get("price_data", {}),
            available_strikes=strikes,
            days_to_expiry=signal.get("days_to_expiry", 30),
        )

        if not best.approved:
            print(f"⛔ رفضت الصفقة: {best.reject_reason}")
            return None

        # 4. إدارة المخاطر
        risk_check = self.risk.evaluate_strategy(best, self.active_trades)

        if not risk_check.approved:
            print(f"⛔ خطر: {risk_check.reason}")
            return None

        # 5. تنفيذ جميع أرجل الاستراتيجية
        trade_legs = []
        for leg in best.legs:
            order = self.executor.place_order(
                symbol=self.config.symbol,
                strike=leg.strike,
                option_type=leg.option_type,
                quantity=leg.quantity * risk_check.quantity,
                order_type="MARKET",
            )
            trade_legs.append({
                "strike": leg.strike,
                "type": leg.option_type,
                "action": leg.action,
                "quantity": leg.quantity * risk_check.quantity,
                "filled_price": order.get("filled_price"),
            })

        max_loss = (best.max_loss or 0) * risk_check.quantity
        max_profit = (best.max_profit or 0) * risk_check.quantity

        trade = {
            "id": len(self.active_trades) + 1,
            "symbol": self.config.symbol,
            "strategy": best.name,
            "legs": trade_legs,
            "entry_time": datetime.now(),
            "entry_price": sum(l.get("filled_price", 0) for l in trade_legs),
            "max_loss": round(max_loss, 2),
            "max_profit": round(max_profit, 2) if max_profit else None,
            "break_even": best.break_even,
            "delta": round(best.total_delta, 4),
            "gamma": round(best.total_gamma, 6),
            "theta": round(best.total_theta, 6),
            "vega": round(best.total_vega, 6),
            "prob_of_profit": risk_check.prob_of_profit,
            "status": "open",
        }
        self.active_trades.append(trade)

        print(f"✅ صفقة {trade['id']}: {best.name} — {len(trade_legs)} أرجل")
        print(f"   أقصى ربح: ${trade['max_profit']} | أقصى خسارة: ${trade['max_loss']}")
        print(f"   احتمالية الربح: {trade['prob_of_profit']*100:.0f}%")

        return trade

    def monitor_positions(self):
        """مراقبة الصفقات المفتوحة"""
        for trade in self.active_trades:
            if trade["status"] != "open":
                continue

            total_pnl = 0
            for leg in trade["legs"]:
                current_price = self.executor.get_current_price(
                    trade["symbol"], leg["strike"]
                )
                entry = leg.get("filled_price", 0)
                pnl = (current_price - entry) * leg["quantity"] * 100
                if leg["action"] == "sell":
                    pnl = -pnl
                total_pnl += pnl

            if trade["max_loss"] and total_pnl <= -trade["max_loss"]:
                self.close_trade(trade["id"], "وقف خسارة ⛔")

            if trade["max_profit"] and total_pnl >= trade["max_profit"]:
                self.close_trade(trade["id"], "هدف محقق ✅")

    def close_trade(self, trade_id: int, reason: str):
        """إغلاق صفقة بالكامل — جميع الأرجل"""
        for trade in self.active_trades:
            if trade["id"] == trade_id and trade["status"] == "open":
                for leg in trade["legs"]:
                    self.executor.close_position(trade["symbol"], leg["strike"])
                trade["status"] = "closed"
                trade["closed_at"] = datetime.now()
                trade["close_reason"] = reason
                print(f"🔒 صفقة {trade_id} أغلقت: {reason}")

    def get_portfolio_summary(self) -> dict:
        """ملخص المحفظة"""
        open_trades = [t for t in self.active_trades if t["status"] == "open"]
        closed_trades = [t for t in self.active_trades if t["status"] == "closed"]

        return {
            "total_trades": len(self.active_trades),
            "open_positions": len(open_trades),
            "closed_positions": len(closed_trades),
            "strategies_used": list(set(t["strategy"] for t in self.active_trades)),
            "balance": self.config.account_balance,
            "max_position_size": self.config.max_position_size,
        }

    @staticmethod
    def _generate_strikes(price: float, spread: float = 0.03, count: int = 6) -> list[float]:
        """توليد strikes حول السعر"""
        strikes = []
        for i in range(-count, count + 1):
            strikes.append(round(price * (1 + i * spread), 0))
        return sorted(set(s for s in strikes if s > 0))
