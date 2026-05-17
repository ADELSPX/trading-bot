"""
استراتيجيات التداول — 9 استراتيجيات أوبشن من تحليل 30 فيديو
_________________________________________________________
1. Put Call مفردة (Simple)
2. Debit Spread (Call/Put)
3. Credit Spread (Call/Put)
4. Iron Condor 🦅
5. Butterfly 🦋
6. Strangle
7. Straddle
8. Earnings (إعلانات أرباح)
9. Hedging (تحوط)
"""

from typing import Optional, Literal

DAYS_IN_YEAR = 365
DEFAULT_IV = 0.20
DEFAULT_RATE = 0.05

from .greeks import GreeksCalculator
from .models import Leg, StrategyResult


# إعدادات افتراضية

class StrategyEngine:
    """
    محرك الاستراتيجيات الذكي
    يختار أفضل استراتيجية بناءً على إشارة الدخول
    """

    def __init__(self):
        self.greeks = GreeksCalculator()

    def analyze(
        self,
        signal: dict,
        price_data: dict,
        available_strikes: list[float],
        days_to_expiry: int = 30,
    ) -> list[StrategyResult]:
        """
        تحليل الإشارة وتقديم جميع الاستراتيجيات المناسبة
        """
        price = signal.get("price", 0)
        direction = signal.get("direction", "neutral")
        confidence = signal.get("confidence", 0.5)
        expected_move_pct = signal.get("expected_move_pct", 1.0)

        results = []

        # جمع الـ strikes المتاحة
        strikes = sorted(set(available_strikes))
        atm_strike = min(strikes, key=lambda x: abs(x - price)) if strikes else price

        # 1. استراتيجية مفردة
        if direction in ("put", "call"):
            results.append(self._simple_option(
                price, direction, strikes, atm_strike, days_to_expiry, confidence
            ))

        # 2. Debit Spread (مناسب للاتجاه القوي)
        if direction in ("put", "call") and len(strikes) >= 2:
            results.append(self._debit_spread(
                price, direction, strikes, atm_strike, days_to_expiry, confidence
            ))

        # 3. Credit Spread (مناسب للاتجاه الضعيف)
        if direction in ("put", "call") and len(strikes) >= 2:
            results.append(self._credit_spread(
                price, direction, strikes, atm_strike, days_to_expiry, confidence
            ))

        # 4. Iron Condor (محايد — تقلب منخفض)
        if len(strikes) >= 4 and direction == "neutral":
            results.append(self._iron_condor(
                price, strikes, days_to_expiry, confidence
            ))

        # 5. Butterfly (محايد — target محدد)
        if len(strikes) >= 3:
            results.append(self._butterfly(
                price, strikes, atm_strike, days_to_expiry, confidence
            ))

        # 6. Strangle (تقلب عالي — توقع حركة كبيرة)
        if len(strikes) >= 2:
            results.append(self._strangle(
                price, strikes, days_to_expiry, confidence, direction
            ))

        # 7. Straddle (تقلب عالي جداً)
        results.append(self._straddle(
            price, atm_strike, days_to_expiry, confidence
        ))

        # 8. Earnings (قبل إعلان الأرباح)
        if signal.get("earnings_play", False):
            results.append(self._earnings_play(
                price, days_to_expiry, expected_move_pct
            ))

        # 9. Hedging (حماية محفظة)
        results.append(self._hedging(
            price, strikes, direction, confidence
        ))

        return results

    def best_strategy(
        self,
        signal: dict,
        price_data: dict,
        available_strikes: list[float],
        days_to_expiry: int = 30,
    ) -> StrategyResult:
        """
        اختيار أفضل استراتيجية تلقائياً
        """
        results = self.analyze(signal, price_data, available_strikes, days_to_expiry)

        if not results:
            return StrategyResult(
                name="none",
                explanation="ما في استراتيجية مناسبة",
                approved=False,
                reject_reason="ما فيه استراتيجية مناسبة للإشارة"
            )

        # نفضل: أعلى ربح/خسارة ratio + أعلى ثقة + أقل مخاطرة
        best = max(results, key=lambda r: (
            r.confidence * 10 +
            (r.max_profit or 0) / max(abs(r.max_loss or 1), 1)  # profit/risk ratio
        ))

        best.approved = best.confidence >= 0.3 and (best.max_profit or 0) > 0
        if not best.approved:
            best.reject_reason = f"الثقة {best.confidence} أقل من الحد الأدنى"

        return best

    # ========== كل استراتيجية ==========

    def _simple_option(
        self, price: float, direction: str, strikes: list[float],
        atm_strike: float, days: int, confidence: float
    ) -> StrategyResult:
        """عقد مفرد — Put أو Call"""
        if direction == "put":
            strike = max(s for s in strikes if s <= price) if any(s <= price for s in strikes) else strikes[0]
            action = "buy"
        else:
            strike = min(s for s in strikes if s >= price) if any(s >= price for s in strikes) else strikes[-1]
            action = "buy"

        g = self.greeks.calculate_all(price, strike, days, DEFAULT_RATE, DEFAULT_IV, direction)
        premium = g["price"]
        max_loss = premium * 100  # قيمة العقد كامل
        max_profit = None  # غير محدود نظرياً

        leg_type: Literal["call", "put"] = direction  # type: ignore
        return StrategyResult(
            name=f"{direction.upper()} Simple",
            legs=[Leg(strike=strike, option_type=leg_type, action=action)],
            max_loss=round(max_loss, 2),
            max_profit=None,
            break_even=[strike + premium if direction == "call" else strike - premium],
            total_delta=g["delta"],
            total_gamma=g["gamma"],
            total_theta=g["theta"],
            total_vega=g["vega"],
            total_premium=-premium,
            confidence=confidence,
            direction=direction,
            explanation=f"عقد {direction} على سترايك {strike}، علاوة ${premium}",
            approved=True,
        )

    def _debit_spread(
        self, price: float, direction: str, strikes: list[float],
        atm_strike: float, days: int, confidence: float
    ) -> StrategyResult:
        """
        Debit Spread = شراء عقد + بيع عقد أغلى (نفس الاتجاه)
        مثال Bull Call Spread: شراء Call سترايك منخفض + بيع Call سترايك أعلى
        """
        if direction == "put":
            # Bear Put Spread
            long_strike = max(s for s in strikes if s <= price) or strikes[0]
            short_strike = min(s for s in strikes if s < long_strike) or strikes[0]
            if short_strike >= long_strike:
                return self._empty("Debit Spread", "ما فيه strikes مناسبة")
            leg_type = "put"
        else:
            # Bull Call Spread
            long_strike = min(s for s in strikes if s >= price) or strikes[-1]
            short_strike = min(s for s in strikes if s > long_strike) or strikes[-1]
            if short_strike <= long_strike:
                return self._empty("Debit Spread", "ما فيه strikes مناسبة")
            leg_type = "call"

        g_long = self.greeks.calculate_all(price, long_strike, days, DEFAULT_RATE, DEFAULT_IV, leg_type)
        g_short = self.greeks.calculate_all(price, short_strike, days, DEFAULT_RATE, DEFAULT_IV, leg_type)

        net_debit = g_long["price"] - g_short["price"]
        spread_width = abs(short_strike - long_strike)
        max_profit = (spread_width - net_debit) * 100
        max_loss = net_debit * 100

        return StrategyResult(
            name=f"{'Bull Call' if direction == 'call' else 'Bear Put'} Spread",
            legs=[
                Leg(strike=long_strike, option_type=leg_type, action="buy"),
                Leg(strike=short_strike, option_type=leg_type, action="sell"),
            ],
            max_loss=round(max_loss, 2),
            max_profit=round(max_profit, 2),
            break_even=[long_strike + net_debit if leg_type == "call" else long_strike - net_debit],
            total_delta=g_long["delta"] - g_short["delta"],
            total_gamma=g_long["gamma"] - g_short["gamma"],
            total_theta=g_long["theta"] - g_short["theta"],
            total_vega=g_long["vega"] - g_short["vega"],
            total_premium=-net_debit,
            confidence=confidence * 0.9,
            direction=direction,
            explanation=f"Spread {long_strike}/{short_strike}، صافي علاوة ${net_debit:.2f}، أقصى ربح ${max_profit:.0f}",
            approved=True,
        )

    def _credit_spread(
        self, price: float, direction: str, strikes: list[float],
        atm_strike: float, days: int, confidence: float
    ) -> StrategyResult:
        """
        Credit Spread = بيع عقد + شراء عقد للحماية (عكس debit)
        """
        if direction == "put":
            # Bull Put Spread
            short_strike = max(s for s in strikes if s <= price) or strikes[0]
            long_strike = min(s for s in strikes if s < short_strike) or strikes[0]
            if long_strike >= short_strike:
                return self._empty("Credit Spread", "ما فيه strikes مناسبة")
            leg_type = "put"
        else:
            # Bear Call Spread
            short_strike = min(s for s in strikes if s >= price) or strikes[-1]
            long_strike = min(s for s in strikes if s > short_strike) or strikes[-1]
            if long_strike <= short_strike:
                return self._empty("Credit Spread", "ما فيه strikes مناسبة")
            leg_type = "call"

        g_short = self.greeks.calculate_all(price, short_strike, days, DEFAULT_RATE, DEFAULT_IV, leg_type)
        g_long = self.greeks.calculate_all(price, long_strike, days, DEFAULT_RATE, DEFAULT_IV, leg_type)

        net_credit = g_short["price"] - g_long["price"]
        spread_width = abs(long_strike - short_strike)
        max_profit = net_credit * 100
        max_loss = (spread_width - net_credit) * 100

        return StrategyResult(
            name=f"{'Bull Put' if direction == 'put' else 'Bear Call'} Credit Spread",
            legs=[
                Leg(strike=short_strike, option_type=leg_type, action="sell"),
                Leg(strike=long_strike, option_type=leg_type, action="buy"),
            ],
            max_loss=round(max_loss, 2),
            max_profit=round(max_profit, 2),
            break_even=[short_strike - net_credit if leg_type == "put" else short_strike + net_credit],
            total_delta=g_short["delta"] - g_long["delta"],
            total_gamma=g_short["gamma"] - g_long["gamma"],
            total_theta=g_short["theta"] - g_long["theta"],
            total_vega=g_short["vega"] - g_long["vega"],
            total_premium=net_credit,
            confidence=confidence * 0.85,
            direction=direction,
            explanation=f"Credit Spread {short_strike}/{long_strike}، صافي علاوة ${net_credit:.2f} (دخل)",
            approved=True,
        )

    def _iron_condor(
        self, price: float, strikes: list[float],
        days: int, confidence: float
    ) -> StrategyResult:
        """
        Iron Condor 🦅
        بيع Put Spread (تحت) + بيع Call Spread (فوق)
        أرباح: السوق يبقى بين strike الوسطى
        """
        if len(strikes) < 4:
            return self._empty("Iron Condor", "يحتاج 4 strikes على الأقل")

        # نختار strikes حول السعر
        mid = len(strikes) // 2
        lower_put_s = strikes[max(0, mid - 2)]
        lower_put_b = strikes[max(0, mid - 3)]
        upper_call_s = strikes[min(len(strikes) - 1, mid + 1)]
        upper_call_b = strikes[min(len(strikes) - 1, mid + 2)]

        if not (lower_put_b < lower_put_s < price < upper_call_s < upper_call_b):
            return self._empty("Iron Condor", "strikes ما تغطي السعر الحالي")

        g_put_s = self.greeks.calculate_all(price, lower_put_s, days, DEFAULT_RATE, DEFAULT_IV, "put")
        g_put_b = self.greeks.calculate_all(price, lower_put_b, days, DEFAULT_RATE, DEFAULT_IV, "put")
        g_call_s = self.greeks.calculate_all(price, upper_call_s, days, DEFAULT_RATE, DEFAULT_IV, "call")
        g_call_b = self.greeks.calculate_all(price, upper_call_b, days, DEFAULT_RATE, DEFAULT_IV, "call")

        net_credit = (g_put_s["price"] - g_put_b["price"]) + (g_call_s["price"] - g_call_b["price"])
        max_profit = net_credit * 100

        # أقصى خسارة = أكبر عرض spread
        put_width = lower_put_s - lower_put_b
        call_width = upper_call_b - upper_call_s
        max_width = max(put_width, call_width)
        max_loss = (max_width - net_credit) * 100

        if max_loss <= 0:
            return self._empty("Iron Condor", "ما فيه ربح متوقع")

        return StrategyResult(
            name="Iron Condor 🦅",
            legs=[
                Leg(strike=lower_put_s, option_type="put", action="sell"),
                Leg(strike=lower_put_b, option_type="put", action="buy"),
                Leg(strike=upper_call_s, option_type="call", action="sell"),
                Leg(strike=upper_call_b, option_type="call", action="buy"),
            ],
            max_loss=round(max_loss, 2),
            max_profit=round(max_profit, 2),
            break_even=[lower_put_s - net_credit, upper_call_s + net_credit],
            total_delta=g_put_s["delta"] - g_put_b["delta"] + g_call_s["delta"] - g_call_b["delta"],
            total_gamma=g_put_s["gamma"] - g_put_b["gamma"] + g_call_s["gamma"] - g_call_b["gamma"],
            total_theta=g_put_s["theta"] - g_put_b["theta"] + g_call_s["theta"] - g_call_b["theta"],
            total_vega=g_put_s["vega"] - g_put_b["vega"] + g_call_s["vega"] - g_call_b["vega"],
            total_premium=net_credit,
            confidence=confidence * 0.75,
            direction="neutral",
            explanation=f"Iron Condor {lower_put_b}/{lower_put_s}/{upper_call_s}/{upper_call_b}، علاوة ${net_credit:.2f}",
            approved=True,
        )

    def _butterfly(
        self, price: float, strikes: list[float],
        atm_strike: float, days: int, confidence: float
    ) -> StrategyResult:
        """
        Butterfly 🦋
        شراء 1 عقد تحت + بيع 2 عقد ATM + شراء 1 عقد فوق
        أرباح: السعر بالضبط عند الـ ATM لحظة الانتهاء
        """
        if len(strikes) < 3:
            return self._empty("Butterfly", "يحتاج 3 strikes على الأقل")

        # نختار: short = أقرب strike للسعر
        short_k = atm_strike
        idx = strikes.index(short_k) if short_k in strikes else len(strikes) // 2
        if idx < 1 or idx >= len(strikes) - 1:
            return self._empty("Butterfly", "ما فيه strikes كافية حول السعر")

        lower_k = strikes[idx - 1]
        upper_k = strikes[idx + 1]

        g_lower = self.greeks.calculate_all(price, lower_k, days, DEFAULT_RATE, DEFAULT_IV, "call")
        g_mid = self.greeks.calculate_all(price, short_k, days, DEFAULT_RATE, DEFAULT_IV, "call")
        g_upper = self.greeks.calculate_all(price, upper_k, days, DEFAULT_RATE, DEFAULT_IV, "call")

        net_debit = g_lower["price"] + g_upper["price"] - 2 * g_mid["price"]
        spread_width = short_k - lower_k
        max_profit = (spread_width - net_debit) * 100
        max_loss = net_debit * 100

        return StrategyResult(
            name="Butterfly 🦋",
            legs=[
                Leg(strike=lower_k, option_type="call", action="buy"),
                Leg(strike=short_k, option_type="call", action="sell", quantity=2),
                Leg(strike=upper_k, option_type="call", action="buy"),
            ],
            max_loss=round(max_loss, 2),
            max_profit=round(max_profit, 2),
            break_even=[lower_k + net_debit, upper_k - net_debit],
            total_delta=g_lower["delta"] + g_upper["delta"] - 2 * g_mid["delta"],
            total_gamma=g_lower["gamma"] + g_upper["gamma"] - 2 * g_mid["gamma"],
            total_theta=g_lower["theta"] + g_upper["theta"] - 2 * g_mid["theta"],
            total_vega=g_lower["vega"] + g_upper["vega"] - 2 * g_mid["vega"],
            total_premium=-net_debit,
            confidence=confidence * 0.6,
            direction="neutral",
            explanation=f"Butterfly {lower_k}/{short_k}/{upper_k}، صافي علاوة ${net_debit:.2f}",
            approved=True,
        )

    def _strangle(
        self, price: float, strikes: list[float],
        days: int, confidence: float, direction: str = "neutral"
    ) -> StrategyResult:
        """
        Strangle = شراء Put (تحت) + شراء Call (فوق)
        أرباح: حركة كبيرة بأي اتجاه
        """
        below_strikes = [s for s in strikes if s <= price * 0.97]
        above_strikes = [s for s in strikes if s >= price * 1.03]
        put_k = min(below_strikes) if below_strikes else strikes[0]
        call_k = min(above_strikes) if above_strikes else strikes[-1]

        if put_k >= call_k:
            put_k = strikes[0]
            call_k = strikes[-1]

        g_put = self.greeks.calculate_all(price, put_k, days, DEFAULT_RATE, DEFAULT_IV, "put")
        g_call = self.greeks.calculate_all(price, call_k, days, DEFAULT_RATE, DEFAULT_IV, "call")

        total_cost = (g_put["price"] + g_call["price"]) * 100

        return StrategyResult(
            name="Strangle",
            legs=[
                Leg(strike=put_k, option_type="put", action="buy"),
                Leg(strike=call_k, option_type="call", action="buy"),
            ],
            max_loss=round(total_cost, 2),
            max_profit=None,  # غير محدود
            break_even=[put_k - (total_cost / 100), call_k + (total_cost / 100)],
            total_delta=g_put["delta"] + g_call["delta"],
            total_gamma=g_put["gamma"] + g_call["gamma"],
            total_theta=g_put["theta"] + g_call["theta"],
            total_vega=g_put["vega"] + g_call["vega"],
            total_premium=-total_cost / 100,
            confidence=confidence * 0.5,
            direction="neutral",
            explanation=f"Strangle {put_k}/{call_k}، تكلفة ${total_cost:.0f}",
            approved=True,
        )

    def _straddle(
        self, price: float, atm_strike: float,
        days: int, confidence: float
    ) -> StrategyResult:
        """
        Straddle = شراء Call ATM + شراء Put ATM
        أرباح: حركة كبيرة بأي اتجاه (أغلى من Strangle)
        """
        g_call = self.greeks.calculate_all(price, atm_strike, days, DEFAULT_RATE, DEFAULT_IV, "call")
        g_put = self.greeks.calculate_all(price, atm_strike, days, DEFAULT_RATE, DEFAULT_IV, "put")

        total_cost = (g_call["price"] + g_put["price"]) * 100

        return StrategyResult(
            name="Straddle",
            legs=[
                Leg(strike=atm_strike, option_type="call", action="buy"),
                Leg(strike=atm_strike, option_type="put", action="buy"),
            ],
            max_loss=round(total_cost, 2),
            max_profit=None,
            break_even=[atm_strike - (total_cost / 100), atm_strike + (total_cost / 100)],
            total_delta=g_call["delta"] + g_put["delta"],
            total_gamma=g_call["gamma"] + g_put["gamma"],
            total_theta=g_call["theta"] + g_put["theta"],
            total_vega=g_call["vega"] + g_put["vega"],
            total_premium=-total_cost / 100,
            confidence=confidence * 0.4,
            direction="neutral",
            explanation=f"Straddle ATM {atm_strike}، تكلفة ${total_cost:.0f}",
            approved=True,
        )

    def _earnings_play(
        self, price: float, days: int, expected_move: float
    ) -> StrategyResult:
        """
        Earnings Play = قبل إعلان الأرباح
        Straddle مع IV مرتفع
        """
        g_call = self.greeks.calculate_all(price, price, days, DEFAULT_RATE, 0.40, "call")
        g_put = self.greeks.calculate_all(price, price, days, DEFAULT_RATE, 0.40, "put")

        total_cost = (g_call["price"] + g_put["price"]) * 100

        return StrategyResult(
            name="Earnings Straddle 📊",
            legs=[
                Leg(strike=price, option_type="call", action="buy"),
                Leg(strike=price, option_type="put", action="buy"),
            ],
            max_loss=round(total_cost, 2),
            max_profit=None,
            break_even=[price - (total_cost / 100), price + (total_cost / 100)],
            total_delta=g_call["delta"] + g_put["delta"],
            total_gamma=g_call["gamma"] + g_put["gamma"],
            total_theta=g_call["theta"] + g_put["theta"],
            total_vega=g_call["vega"] + g_put["vega"],
            total_premium=-total_cost / 100,
            confidence=0.4,
            direction="neutral",
            explanation=f"Earnings Straddle على {price}، IV=40%",
            approved=True,
        )

    def _hedging(
        self, price: float, strikes: list[float],
        direction: str, confidence: float
    ) -> StrategyResult:
        """
        Hedging = شراء Put للحماية (للمحفظة الطويلة)
        """
        strike = strikes[0] if strikes else price * 0.9
        g = self.greeks.calculate_all(price, strike, 60, DEFAULT_RATE, DEFAULT_IV, "put")

        premium = g["price"]

        return StrategyResult(
            name="Hedge Protection 🛡️",
            legs=[Leg(strike=strike, option_type="put", action="buy")],
            max_loss=round(premium * 100, 2),
            max_profit=None,
            break_even=[strike - premium],
            total_delta=g["delta"],
            total_gamma=g["gamma"],
            total_theta=g["theta"],
            total_vega=g["vega"],
            total_premium=-premium,
            confidence=0.5,
            direction="bearish",
            explanation=f"Hedge: شراء Put {strike} لحماية المحفظة، تكلفة ${premium:.2f}",
            approved=True,
        )

    def _empty(self, name: str, reason: str) -> StrategyResult:
        """استراتيجية فاشلة"""
        return StrategyResult(
            name=name,
            approved=False,
            reject_reason=reason,
            explanation=reason,
        )
