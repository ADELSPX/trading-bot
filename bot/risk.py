"""
إدارة المخاطر — من الفديو الثالث والرابع
______________________________________________
- تحديد حجم الصفقة
- وقف الخسارة
- إجمالي التعرض
"""

from .core import TradeConfig


class RiskManager:
    """
    إدارة المخاطر — تمنع الخسائر الكبيرة
    """

    def __init__(self, config: TradeConfig):
        self.config = config

    def evaluate(self, analysis: dict, active_trades: list) -> dict:
        """
        تقييم المخاطر للصفقة المقترحة

        الفديو الثالث: حساب تكلفة العقد
        العقد × سعر × 100
        """
        result = {
            "approved": True,
            "reason": "",
            "quantity": 1,
            "stop_loss": 0,
            "max_risk": 0,
        }

        # 1. تحقق من إجمالي التعرض
        total_exposure = sum(
            t.get("entry_price", 0) * t.get("quantity", 0) * 100
            for t in active_trades
            if t.get("status") == "open"
        )

        remaining_capacity = self.config.max_position_size - total_exposure

        if remaining_capacity <= 0:
            result["approved"] = False
            result["reason"] = "الحد الأقصى للتعرض تم الوصول إليه"
            return result

        # 2. حساب الكمية (من الفديو الثالث: حاسبة التكلفة)
        option_price = analysis.get("limit_price") or 0.50  # تخمين
        max_contracts = int(remaining_capacity / (option_price * 100))

        if max_contracts < 1:
            result["approved"] = False
            result["reason"] = "الرصيد لا يكفي لعقد واحد"
            return result

        # 3. إدارة المخاطرة: نبدأ بعقد واحد للاختبار
        result["quantity"] = min(max_contracts, 1)  # عقد واحد للمبتدئين

        # 4. وقف الخسارة (من الفديو 4: أغلق عند الهدف أو الخسارة)
        entry_cost = option_price * result["quantity"] * 100
        result["stop_loss"] = entry_cost  # 100% = خسارة العقد كامل
        result["max_risk"] = entry_cost

        return result
