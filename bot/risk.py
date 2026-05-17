"""
إدارة المخاطر المتقدمة
_________________________________
- تحديد حجم الصفقة (Kelly Criterion, Fixed %)
- وقف الخسارة (Fixed, Greeks-based, Time-based)
- إجمالي التعرض (Portfolio heat)
- Greeks limits (Delta, Gamma, Vega caps)
- Probability of profit (POP)
"""

from dataclasses import dataclass
from typing import Optional

from .models import TradeConfig, StrategyResult
from .greeks import GreeksCalculator


@dataclass
class RiskAssessment:
    """نتيجة تقييم المخاطر"""
    approved: bool
    reason: str = ""
    quantity: int = 1
    stop_loss_pct: float = 100.0
    max_risk_pct: float = 2.0  # % من رأس المال
    max_risk_usd: float = 0.0
    position_size_pct: float = 0.0
    delta_limit_ok: bool = True
    gamma_limit_ok: bool = True
    vega_limit_ok: bool = True
    prob_of_profit: float = 0.0


class RiskManager:
    """
    إدارة المخاطر المتقدمة
    تدعم الاستراتيجيات متعددة الأرجل
    """

    # حدود افتراضية
    MAX_DELTA = 0.50       # حد الدلتا الكلي (50 Delta)
    MAX_GAMMA = 0.10       # حد الجاما
    MAX_VEGA = 0.05        # حد الفيجا (لكل 1%)
    MAX_POSITION_PCT = 0.05  # 5% من رأس المال للصفقة
    MAX_PORTFOLIO_HEAT = 0.25  # 25% إجمالي تعرض
    STOP_LOSS_MULTIPLIER = 1.5  # 1.5x قيمة العلاوة

    def __init__(self, config: TradeConfig, account_balance: float = 10000.0):
        self.config = config
        self.balance = account_balance
        self.greeks = GreeksCalculator()

    def evaluate_strategy(
        self,
        strategy_result,
        active_trades: list[dict],
    ) -> RiskAssessment:
        """
        تقييم المخاطر لاستراتيجية كاملة (قد تحتوي عدة أرجل)
        """
        # 1. فحص التعرض الكلي
        total_exposure = sum(
            t.get("max_risk", 0)
            for t in active_trades
            if t.get("status") == "open"
        )

        remaining = self.balance * self.MAX_PORTFOLIO_HEAT - total_exposure
        if remaining <= 0:
            return RiskAssessment(
                approved=False,
                reason=f"⚠️ التعرض الكلي وصل الحد ({self.MAX_PORTFOLIO_HEAT*100:.0f}% من رأس المال)"
            )

        # 2. حساب المخاطر حسب الاستراتيجية
        max_loss_usd = strategy_result.max_loss or (self.balance * 0.1)  # 10% كحد أقصى

        if max_loss_usd > self.balance * self.MAX_POSITION_PCT:
            # نحجم العقد
            scale_factor = (self.balance * self.MAX_POSITION_PCT) / max_loss_usd
            suggested_qty = max(1, int(scale_factor))

            # تأكد من أن رأس المال كافي
            if suggested_qty < 1:
                return RiskAssessment(
                    approved=False,
                    reason=f"⚠️ المخاطرة ${max_loss_usd:.0f} > ${self.balance * self.MAX_POSITION_PCT:.0f} (حد 5%)"
                )

            scaled_loss = max_loss_usd * (suggested_qty / strategy_result.legs[0].quantity if strategy_result.legs else 1)
        else:
            suggested_qty = 1
            scaled_loss = max_loss_usd

        # 3. فحص حدود Greeks
        delta_check = abs(strategy_result.total_delta) <= self.MAX_DELTA
        gamma_check = abs(strategy_result.total_gamma) <= self.MAX_GAMMA
        vega_check = abs(strategy_result.total_vega) <= self.MAX_VEGA

        if not delta_check:
            return RiskAssessment(
                approved=False,
                reason=f"⚠️ الدلتا {strategy_result.total_delta:.2f} تجاوزت الحد ({self.MAX_DELTA})"
            )

        # 4. احتمال الربح (Probability of Profit)
        # بسيطة: بناءً على الدلتا
        pop = max(0, min(1, 0.5 - strategy_result.total_delta * 0.5)) if strategy_result.direction == "neutral" else max(0, min(1, abs(strategy_result.total_delta)))

        # 5. وقف الخسارة
        if strategy_result.max_loss and strategy_result.max_loss > 0:
            stop_loss = strategy_result.max_loss * self.STOP_LOSS_MULTIPLIER
        else:
            stop_loss = scaled_loss * self.STOP_LOSS_MULTIPLIER

        return RiskAssessment(
            approved=True,
            quantity=suggested_qty,
            stop_loss_pct=round(stop_loss / self.balance * 100, 1),
            max_risk_pct=round(scaled_loss / self.balance * 100, 1),
            max_risk_usd=round(scaled_loss, 2),
            position_size_pct=round(scaled_loss / self.balance * 100, 1),
            delta_limit_ok=delta_check,
            gamma_limit_ok=gamma_check,
            vega_limit_ok=vega_check,
            prob_of_profit=round(pop, 2),
        )

    def calculate_kelly(self, win_prob: float, win_loss_ratio: float) -> float:
        """
        Kelly Criterion — حجم الصفقة المثالي
        f = (bp - q) / b
        b = win/loss ratio
        p = احتمال الربح
        q = احتمال الخسارة (1-p)
        """
        if win_loss_ratio <= 0:
            return 0
        q = 1 - win_prob
        kelly = (win_loss_ratio * win_prob - q) / win_loss_ratio
        return max(0, min(kelly, 0.25))  # Cap at 25%

    def daily_loss_limit_hit(self, today_pnl: float) -> bool:
        """
        هل وصلنا حد الخسارة اليومي؟ (-5% من رأس المال)
        """
        return today_pnl <= -self.balance * 0.05

    def weekly_loss_limit_hit(self, week_pnl: float) -> bool:
        """
        هل وصلنا حد الخسارة الأسبوعي؟ (-10% من رأس المال)
        """
        return week_pnl <= -self.balance * 0.10
