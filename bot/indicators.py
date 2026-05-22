"""
المؤشرات الفنية — من الفديوهات
___________________________________
- فيبوناتشي (الفديو 2)
- دلتا (الفديو 4 — الأهم 🔥)
"""

import math


class TechnicalIndicators:
    """
    المؤشرات الفنية المستخلصة من الفيديوهات التدريبية
    """

    @staticmethod
    def fibonacci_levels(price_data: dict) -> dict:
        """
        حساب مستويات فيبوناتشي — من الفديو 2

        تحدد نقاط الدعم والمقاومة بناءً على حركة السعر
        """
        high = price_data.get("high", 0)
        low = price_data.get("low", 0)
        close = price_data.get("close", 0)

        if high == 0 or low == 0:
            return {}

        range_price = high - low

        return {
            "level_0": round(high, 2),         # 0% (القمة)
            "level_236": round(high - range_price * 0.236, 2),
            "level_382": round(high - range_price * 0.382, 2),
            "level_500": round(high - range_price * 0.500, 2),
            "level_618": round(high - range_price * 0.618, 2),  # 🔑 الأهم
            "level_786": round(high - range_price * 0.786, 2),
            "level_100": round(low, 2),         # 100% (القاع)
            "current_price": close,
        }

    @staticmethod
    def calculate_delta(
        underlying_price: float,
        strike: float,
        time_to_expiry: int = 1,
        volatility: float = 20,
        risk_free_rate: float = 5.0,
    ) -> float:
        """
        حساب دلتا العقد — من الفديو الرابع 🔥

        الدلتا = مقياس حساسية سعر العقد لحركة السهم
        القيمة بين 0 و 1 (للكول) أو -1 و 0 (للبوت)

        مثال: دلتا 0.17 يعني كل $1 حركة = 17 سنت تغير في العقد

        تستخدم نموذج Black-Scholes المبسط
        """
        if time_to_expiry <= 0:
            time_to_expiry = 1

        # Black-Scholes التقريبي
        # d1 = (ln(S/K) + (r + σ²/2) * T) / (σ * √T)
        s = underlying_price
        k = strike
        t = time_to_expiry / 365  # حول الأيام لسنوات
        r = risk_free_rate / 100
        sigma = volatility / 100

        if s <= 0 or k <= 0:
            return 0.5  # قيمة افتراضية

        try:
            d1 = (math.log(s / k) + (r + sigma ** 2 / 2) * t) / (
                sigma * math.sqrt(t)
            )
        except (ValueError, ZeroDivisionError):
            return 0.5

        # تقريب الدلتا باستخدام CDF
        delta = TechnicalIndicators._norm_cdf(d1)

        return round(delta, 4)

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """توزيع طبيعي تراكمي (CDF) — تقريب"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def expected_option_price(
        current_price: float,
        delta: float,
        expected_move: float,
    ) -> float:
        """
        حساب سعر العقد المتوقع بعد حركة السهم — الفديو 4

        المعادلة الذهبية:
        سعر العقد بعد الحركة = سعر العقد الحالي - (الدلتا × مقدار حركة السهم)

        مثال:
        سعر العقد = $0.25
        دلتا = 0.17
        السهم ينزل $1
        سعر العقد الجديد = 0.25 - (0.17 × 1) = $0.08
        """
        new_price = current_price - (delta * abs(expected_move))
        return max(new_price, 0.01)  # ما ينزل عن الصفر
