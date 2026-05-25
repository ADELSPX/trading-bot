"""
استراتيجيات التداول — من تحليل الفيديوهات
═══════════════════════════════════════════
- استراتيجية Put Options (الفديو 2)
- اختيار Strike بناءً على Fibonacci (الفديو 2 + 4)
- 9 استراتيجيات أوبشن كاملة
- #10: استراتيجية أبو فهد قاما (GAMMA) 🚎 — مايو 2026
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field

from .gamma_strategy import (
    GammaStrategy, GammaAnalysis, GammaEntry,
    Direction, TowerStrength, GammaTower, SupplyDemandZone,
    CandleSignal, ZoneType, ZoneTimeframe, CandleBody,
)
from .supply_demand_strategy import (
    SupplyDemandStrategy, EntrySignal, EntryDecision,
    ZoneState as SDZoneState, TrendType,
)
from .indicators import TechnicalIndicators
from config.models import TradeConfig


@dataclass
class StrategyResult:
    """نتيجة تقييم الاستراتيجية"""
    strategy_name: str
    symbol: str
    direction: str  # "call" | "put"
    strike: float
    entry_price: float
    stop_loss: float
    target_price: float
    target_pct: float
    confidence: float
    approved: bool
    reason: str
    metadata: dict = field(default_factory=dict)


class StrategyEngine:
    """
    محرك الاستراتيجيات — يقرر: هل ندخل؟ وأين نضع الحدود؟

    ### الاستراتيجيات المدعومة:
    1-4.  Single Call/Put, Debit/Vertical Spread, Credit Spread
    5-6.  Iron Condor, Butterfly
    7-8.  Strangle, Straddle
    9.    Earnings Strategy + Hedging
    10.   🆕 استراتيجية أبو فهد قاما (GAMMA) — سكالبنج يومي 🚎
    """

    def __init__(self, config: Optional[TradeConfig] = None):
        self.config = config or TradeConfig()
        self.gamma = GammaStrategy(
            symbol=self.config.symbol,
            target_profit_pct=self.config.target_profit_pct,
        )
        self.supply_demand = SupplyDemandStrategy(symbol=self.config.symbol)

    # ═══════════════════════════════════════════════════════
    # الاستراتيجيات الأساسية (1-9)
    # ═══════════════════════════════════════════════════════

    def evaluate(self, signal: dict, fib_levels: dict, delta: float) -> dict:
        """
        تقييم الإشارة وتحديد معالم الصفقة (استراتيجيات 1-9)
        """
        price = signal.get("price", 0)
        direction = signal.get("direction", "put")
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
            target_price = price * (1 - expected_move_pct / 100)

            for strike in signal.get("available_strikes", []):
                if strike >= price * 0.95:
                    recommendation["recommended_strike"] = strike
                    break

            if not recommendation["recommended_strike"]:
                recommendation["recommended_strike"] = round(price * 0.97, 1)

            move_amount = price - target_price
            current_option_price = delta * price * 0.3

            limit_price = current_option_price - (delta * move_amount)

            if limit_price > 0:
                recommendation["limit_price"] = round(limit_price, 2)
            else:
                recommendation["limit_price"] = None
                recommendation["order_type"] = "MARKET"

            recommendation["entry"] = "put"
            recommendation["target"] = target_price
            recommendation["expected_move"] = move_amount

        else:  # call
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

    # ═══════════════════════════════════════════════════════
    # 🆕 الاستراتيجية #10: قاما (GAMMA)
    # ═══════════════════════════════════════════════════════

    def evaluate_gamma(
        self,
        price_data: dict,
        candles_5m: list[dict],
        candles_15m: list[dict],
        volume_profile: Optional[dict] = None,
    ) -> StrategyResult:
        """
        تقييم استراتيجية أبو فهد قاما 🚎

        المدخلات:
        - price_data: بيانات السعر الحالية (high, low, close, ma200)
        - candles_5m: شموع فريم 5 دقائق [{open, high, low, close, timestamp}]
        - candles_15m: شموع فريم 15 دقيقة
        - volume_profile: (اختياري) Volume Profile للسيولة
        """
        analysis = self.gamma.analyze(
            price_data=price_data,
            candles_5m=candles_5m,
            candles_15m=candles_15m,
            volume_profile=volume_profile,
        )

        if not analysis.entry:
            return StrategyResult(
                strategy_name="قاما (GAMMA) 🚎",
                symbol=self.config.symbol,
                direction="none",
                strike=0,
                entry_price=analysis.current_price,
                stop_loss=0,
                target_price=0,
                target_pct=0,
                confidence=0.0,
                approved=False,
                reason="لا توجد إشارة دخول — انتظر الباص 🚎",
                metadata={"analysis": analysis},
            )

        entry = analysis.entry
        confidence = 0.7  # أساسي — يرتفع بتوافق الشروط

        # رفع الثقة حسب قوة الإشارة
        if entry.reason.count("✅") >= 3:
            confidence = 0.9
        elif entry.reason.count("✅") >= 2:
            confidence = 0.8

        # إذا البرج قوي (أحمر/أصفر) = ثقة أعلى
        if entry.tower.strength in (TowerStrength.RED, TowerStrength.YELLOW):
            confidence = min(1.0, confidence + 0.1)

        return StrategyResult(
            strategy_name="قاما (GAMMA) 🚎",
            symbol=self.config.symbol,
            direction=entry.direction.value,
            strike=entry.entry_price,
            entry_price=entry.entry_price,
            stop_loss=entry.stop_loss,
            target_price=entry.target_price,
            target_pct=entry.target_pct,
            confidence=confidence,
            approved=confidence >= 0.7,
            reason=entry.reason,
            metadata={
                "analysis": analysis,
                "tower": entry.tower,
                "flip_enabled": entry.require_flip,
                "notes": analysis.notes,
            },
        )

    # ═══════════════════════════════════════════════════════
    # 🆕 الاستراتيجية #11: العرض والطلب — أبو ليلى
    # ═══════════════════════════════════════════════════════

    def evaluate_supply_demand(
        self,
        candles: list[dict],
        current_price: float,
        swing_strength: int = 3,
    ) -> StrategyResult:
        """
        تقييم استراتيجية العرض والطلب 📊
        منهجية أبو ليلى — Abo Mazen Trade

        المدخلات:
        - candles: شموع [{open, high, low, close}]
        - current_price: السعر الحالي
        - swing_strength: قوة كشف التأرجح (افتراضي 3)
        """
        signal = self.supply_demand.decide(candles, current_price)

        if signal.decision == EntryDecision.WAIT:
            return StrategyResult(
                strategy_name="العرض والطلب 📊",
                symbol=self.config.symbol,
                direction="none",
                strike=0,
                entry_price=current_price,
                stop_loss=0,
                target_price=0,
                target_pct=0,
                confidence=0.0,
                approved=False,
                reason=signal.reason,
            )

        direction = "call" if "buy" in signal.decision.value else "put"

        return StrategyResult(
            strategy_name="العرض والطلب 📊",
            symbol=self.config.symbol,
            direction=direction,
            strike=signal.entry_price,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            target_price=signal.take_profit,
            target_pct=round(
                abs(signal.take_profit - signal.entry_price)
                / signal.entry_price * 100, 1
            ),
            confidence=signal.confidence,
            approved=signal.confidence >= 0.5,
            reason=signal.reason,
            metadata={
                "zone_type": signal.zone.zone_type.value,
                "zone_state": signal.zone.state.value,
                "score": signal.score,
                "risk_reward": signal.risk_reward,
                "w_trade": signal.w_trade is not None,
            },
        )

    # ═══════════════════════════════════════════════════════
    # تقييم كل الاستراتيجيات — اختيار الأفضل
    # ═══════════════════════════════════════════════════════

    def best_strategy(
        self,
        signal: dict,
        fib_levels: dict,
        delta: float,
        greek_data: Optional[dict] = None,
        gamma_data: Optional[dict] = None,
        supply_demand_data: Optional[dict] = None,
    ) -> StrategyResult:
        """
        تقييم كل الاستراتيجيات واختيار الأفضل

        المعيار:
        score = confidence * 10 + (max_profit / max(abs(max_loss), 1))

        تضاف استراتيجية GAMMA إذا توفرت بياناتها
        """
        results: list[StrategyResult] = []

        # استراتيجيات 1-9 (من evaluate الأساسي)
        rec = self.evaluate(signal, fib_levels, delta)

        # ... (باقي الاستراتيجيات في الإصدارات المستقبلية)
        price = signal.get("price", 0)

        # 🆕 تقييم GAMMA إذا توفرت البيانات
        if gamma_data:
            gamma_result = self.evaluate_gamma(
                price_data=gamma_data.get("price_data", {}),
                candles_5m=gamma_data.get("candles_5m", []),
                candles_15m=gamma_data.get("candles_15m", []),
                volume_profile=gamma_data.get("volume_profile"),
            )
            results.append(gamma_result)

        # 🆕 تقييم العرض والطلب إذا توفرت البيانات
        if supply_demand_data:
            sd_result = self.evaluate_supply_demand(
                candles=supply_demand_data.get("candles", []),
                current_price=supply_demand_data.get("current_price", price),
                swing_strength=supply_demand_data.get("swing_strength", 3),
            )
            results.append(sd_result)

        # إضافة تقييم أساسي
        direction = rec.get("entry", "put")
        if direction:
            results.append(StrategyResult(
                strategy_name="مفردة (Single)",
                symbol=self.config.symbol,
                direction=direction,
                strike=rec.get("recommended_strike", price),
                entry_price=price,
                stop_loss=price * 0.95,
                target_price=rec.get("target", price * 1.05),
                target_pct=5.0,
                confidence=rec.get("confidence", 0.5),
                approved=True,
                reason="إشارة أساسية من المؤشرات",
            ))

        if not results:
            return StrategyResult(
                strategy_name="لا شيء",
                symbol=self.config.symbol,
                direction="none",
                strike=0, entry_price=0, stop_loss=0,
                target_price=0, target_pct=0,
                confidence=0, approved=False,
                reason="لا توجد استراتيجية مناسبة",
            )

        # ترتيب حسب score
        def score(result: StrategyResult) -> float:
            if not result.approved:
                return -1.0
            max_loss = abs(result.entry_price - result.stop_loss) if result.stop_loss else 1
            max_profit = abs(result.target_price - result.entry_price) if result.target_price else 1
            return result.confidence * 10 + (max_profit / max(max_loss, 1))

        results.sort(key=score, reverse=True)
        return results[0]

    # ═══════════════════════════════════════════════════════
    # أدوات مساعدة
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def gamma_summary(analysis: GammaAnalysis) -> str:
        """ملخص عربي لتحليل القاما"""
        gs = GammaStrategy()
        return gs.summary(analysis)

    @staticmethod
    def get_preferred_symbols() -> list[str]:
        """أفضل 6 شركات + صندوق للمضاربة (حسب أبو فهد)"""
        return ["QQQ", "LLY", "CRWD", "COST", "ASML", "MDB"]

    @staticmethod
    def list_strategies() -> list[dict]:
        """قائمة بكل الاستراتيجيات المدعومة"""
        return [
            {"id": 1, "name": "عقود مفردة (Single Call/Put)", "type": "single", "capital": "low"},
            {"id": 2, "name": "ديبت سبريد (Debit Spread)", "type": "spread", "capital": "medium"},
            {"id": 3, "name": "كريدت سبريد (Credit Spread)", "type": "spread", "capital": "medium"},
            {"id": 4, "name": "آيرون كندور (Iron Condor) 🦅", "type": "multi", "capital": "high"},
            {"id": 5, "name": "بترفلاي (Butterfly) 🦋", "type": "multi", "capital": "medium"},
            {"id": 6, "name": "سترانجل (Strangle)", "type": "multi", "capital": "medium"},
            {"id": 7, "name": "سترادل (Straddle)", "type": "multi", "capital": "high"},
            {"id": 8, "name": "إعلانات الأرباح", "type": "event", "capital": "medium"},
            {"id": 9, "name": "تحوط (Hedging) 🛡️", "type": "hedge", "capital": "high"},
            {"id": 10, "name": "قاما أبو فهد (GAMMA) 🚎", "type": "scalping", "capital": "low", "new": True},
            {"id": 11, "name": "العرض والطلب — أبو ليلى 📊", "type": "supply_demand", "capital": "low", "new": True},
        ]
