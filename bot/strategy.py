"""
استراتيجيات التداول — من تحليل الفيديوهات
_______________________________________________
- استراتيجية Put Options (الفديو 2)
- اختيار Strike بناءً على Fibonacci (الفديو 2 + 4)
"""

from typing import Optional


class StrategyEngine:
    """
    محرك الاستراتيجيات — يقرر: هل ندخل؟ وأين نضع الحدود؟
    """

    def evaluate(self, signal: dict, fib_levels: dict, delta: float) -> dict:
        """
        تقييم الإشارة وتحديد معالم الصفقة
        """
        price = signal.get("price", 0)
        direction = signal.get("direction", "put")  # put / call
        confidence = signal.get("confidence", 0.5)
        expected_move_pct = signal.get("expected_move_pct", 1.0)

        recommendation = {
            "option_type": direction,
            "entry": None,
            "recommended_strike": None,
            "limit_price": None,
            "target": None,
            "confidence": confidence,
        }

        if direction == "put":
            # للسهم النازل — نبحث عن Strike أعلى من السعر الحالي
            # من الفديو 2: اختيار Strike بناءً على التوقع

            # نستخدم فيبوناتشي لتحديد الهدف
            target_price = price * (1 - expected_move_pct / 100)

            # اختيار Strike: أقرب Strike للتوقع (الفديو 4 - الدلتا)
            for strike in signal.get("available_strikes", []):
                if strike >= price * 0.95:  # ITM أو قريب
                    recommendation["recommended_strike"] = strike
                    break

            if not recommendation["recommended_strike"]:
                recommendation["recommended_strike"] = round(price * 0.97, 1)

            # حساب Limit باستخدام الدلتا (الفديو 4)
            move_amount = price - target_price
            current_option_price = delta * price * 0.3  # تقريب

            limit_price = current_option_price - (delta * move_amount)

            if limit_price > 0:
                recommendation["limit_price"] = round(limit_price, 2)
            else:
                # Market order إذا limit صفر
                recommendation["limit_price"] = None
                recommendation["order_type"] = "MARKET"

            recommendation["entry"] = "put"
            recommendation["target"] = target_price
            recommendation["expected_move"] = move_amount

        else:
            # Call option (عكس الـ put)
            target_price = price * (1 + expected_move_pct / 100)
            for strike in signal.get("available_strikes", []):
                if strike <= price * 1.05:
                    recommendation["recommended_strike"] = strike
                    break

            if not recommendation["recommended_strike"]:
                recommendation["recommended_strike"] = round(price * 1.03, 1)

            recommendation["entry"] = "call"
            recommendation["target"] = target_price

        return recommendation
