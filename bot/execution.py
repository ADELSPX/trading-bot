"""
تنفيذ الأوامر — واجهة للوسطاء
__________________________________
مبدئياً: محاكي (Paper Trading)
لاحقاً: Interactive Brokers API (دراية جلوبل ما يدعم API)
"""

from typing import Optional


class OrderExecutor:
    """
    تنفيذ الأوامر — Market / Limit (من الفديو الخامس)
    """

    def __init__(self, broker: str = "simulator"):
        self.broker = broker
        self.orders: list = []
        self.positions: dict = {}

    def place_order(
        self,
        symbol: str,
        strike: float,
        option_type: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
    ) -> dict:
        """
        تنفيذ أمر — Market أو Limit (الفديو 5)

        Market: تنفيذ فوري بالسعر الحالي
        Limit: تنفيذ بسعر محدد (فوق/تحت السوق)
        """
        order = {
            "id": len(self.orders) + 1,
            "symbol": symbol,
            "strike": strike,
            "type": option_type,
            "quantity": quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "status": "pending",
            "filled_price": None,
        }

        if self.broker == "simulator":
            # محاكي — نستخدم سعر افتراضي
            if order_type == "MARKET":
                order["filled_price"] = self._simulate_market_price(strike)
            else:
                order["filled_price"] = limit_price or self._simulate_market_price(strike)

            order["status"] = "filled"
            self._update_position(symbol, strike, quantity, order["filled_price"])

        elif self.broker == "ibkr":
            # Interactive Brokers — مستقبلاً
            order["status"] = "pending_ibkr"
            print("⚠️ تكامل Interactive Brokers قيد التطوير")

        self.orders.append(order)
        return order

    def close_position(self, symbol: str, strike: float):
        """إغلاق صفقة (عكس التنفيذ)"""
        key = f"{symbol}_{strike}"
        if key in self.positions:
            self.positions.pop(key)
            print(f"🔒 Position {symbol} {strike} closed")

    def get_current_price(self, symbol: str, strike: float) -> float:
        """سعر العقد الحالي (محاكي)"""
        key = f"{symbol}_{strike}"
        if key in self.positions:
            return self.positions[key]["current_price"]
        return 0.0

    def _simulate_market_price(self, strike: float) -> float:
        """محاكي سعر السوق"""
        import random
        return round(strike * 0.01 * (0.8 + random.random() * 0.4), 2)

    def _update_position(self, symbol: str, strike: float, qty: int, price: float):
        """تحديث المركز المفتوح"""
        key = f"{symbol}_{strike}"
        self.positions[key] = {
            "symbol": symbol,
            "strike": strike,
            "quantity": qty,
            "entry_price": price,
            "current_price": price,
        }
