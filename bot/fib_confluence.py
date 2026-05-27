"""
توافق فيبوناتشي — Fibonacci Confluence
═══════════════════════════════════════
منهجية سامي ضيف الله WH SPX — مايو 2026

"القوة تأتي من التوافق. فيبوناتشي أقوى عندما يتوافق مستوى مع منطقة عرض/طلب،
أو متوسط متحرك، أو شمعة انعكاسية."

المستويات المدعومة:
  - ارتداد:   23.6% / 38.2% / 50% / 61.8% / 78.6%
  - امتداد:   127.2% / 161.8% / 261.8%
  - النسبة الذهبية: 61.8% هي الأهم
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class FibLevel(Enum):
    """مستويات فيبوناتشي"""
    LEVEL_236 = (0.236, "23.6%", 0.3)   # ضعيف
    LEVEL_382 = (0.382, "38.2%", 0.5)   # متوسط
    LEVEL_500 = (0.500, "50%", 0.6)     # مهم — ليس فيبوناتشي رسمي لكنه الأهم عملياً
    LEVEL_618 = (0.618, "61.8%", 0.9)   # 🔑 النسبة الذهبية — الأقوى
    LEVEL_786 = (0.786, "78.6%", 0.4)   # متوسط
    EXT_1272 = (1.272, "127.2%", 0.5)   # امتداد
    EXT_1618 = (1.618, "161.8%", 0.7)   # امتداد ذهبي
    EXT_2618 = (2.618, "261.8%", 0.4)   # امتداد بعيد

    def __init__(self, ratio: float, label: str, weight: float):
        self.ratio = ratio
        self.label = label
        self.weight = weight


class ConfluenceType(Enum):
    """نوع التوافق"""
    SUPPLY_DEMAND = "supply_demand"   # مع منطقة عرض/طلب
    MOVING_AVERAGE = "moving_average"  # مع متوسط متحرك
    SWING_LEVEL = "swing_level"       # مع قمة/قاع سابق
    ROUND_NUMBER = "round_number"     # مع رقم دائري
    REVERSAL_CANDLE = "reversal_candle"  # مع شمعة انعكاسية
    TRENDLINE = "trendline"           # مع خط اتجاه


@dataclass
class FibLevelResult:
    """نتيجة مستوى فيبوناتشي واحد"""
    level: FibLevel
    price: float                     # سعر المستوى
    ratio: float                     # النسبة (0-2.618)
    label: str                       # التسمية
    base_weight: float               # الوزن الأساسي
    conflations: list[Confluence] = field(default_factory=list)
    total_weight: float = 0          # الوزن الكلي بعد التوافقات

    @property
    def is_strong(self) -> bool:
        """هل المستوى قوي (وزن ≥ 1.0)؟"""
        return self.total_weight >= 1.0

    @property
    def is_golden(self) -> bool:
        """هل هو المستوى الذهبي (61.8%)؟"""
        return self.level == FibLevel.LEVEL_618


@dataclass
class Confluence:
    """توافق واحد"""
    type: ConfluenceType
    matched_price: float             # السعر المتوافق
    distance_pct: float              # نسبة البعد عن مستوى فيبوناتشي
    bonus_weight: float = 0.2        # وزن إضافي
    description: str = ""


@dataclass
class FibConfluenceReport:
    """تقرير توافق فيبوناتشي كامل"""
    swing_high: float                # القمة المستخدمة
    swing_low: float                 # القاع المستخدم
    levels: list[FibLevelResult] = field(default_factory=list)
    best_support: Optional[FibLevelResult] = None   # أفضل دعم (تحت السعر)
    best_resistance: Optional[FibLevelResult] = None # أفضل مقاومة (فوق السعر)
    current_price: float = 0

    @property
    def strongest_level(self) -> FibLevelResult | None:
        """أقوى مستوى فيبوناتشي (أعلى وزن)"""
        if not self.levels:
            return None
        return max(self.levels, key=lambda l: l.total_weight)

    @property
    def golden_level(self) -> FibLevelResult | None:
        """المستوى الذهبي 61.8%"""
        for l in self.levels:
            if l.is_golden:
                return l
        return None


class FibConfluence:
    """
    محرك توافق فيبوناتشي

    يحسب مستويات فيبوناتشي ويقيس قوتها من خلال التوافقات مع:
    - مناطق العرض والطلب
    - المتوسطات المتحركة
    - القمم والقيعان السابقة
    - الأرقام الدائرية
    - شموع انعكاسية

    الاستخدام:
        fib = FibConfluence()
        report = fib.analyze(candles, swing_high, swing_low, current_price,
                            supply_zones=..., demand_zones=...,
                            moving_averages={...})
    """

    # نسبة التفاوت المسموح للتوافق (±0.5%)
    CONFLUENCE_TOLERANCE = 0.005

    # جميع مستويات فيبوناتشي المدعومة
    ALL_LEVELS = [
        FibLevel.LEVEL_236,
        FibLevel.LEVEL_382,
        FibLevel.LEVEL_500,
        FibLevel.LEVEL_618,
        FibLevel.LEVEL_786,
        FibLevel.EXT_1272,
        FibLevel.EXT_1618,
        FibLevel.EXT_2618,
    ]

    RETRACEMENT_LEVELS = [
        FibLevel.LEVEL_236, FibLevel.LEVEL_382,
        FibLevel.LEVEL_500, FibLevel.LEVEL_618, FibLevel.LEVEL_786,
    ]

    EXTENSION_LEVELS = [
        FibLevel.EXT_1272, FibLevel.EXT_1618, FibLevel.EXT_2618,
    ]

    def analyze(
        self,
        candles: list[dict],
        swing_high: float,
        swing_low: float,
        current_price: float,
        supply_zones: Optional[list] = None,
        demand_zones: Optional[list] = None,
        moving_averages: Optional[dict[str, float]] = None,
        trendlines: Optional[list[dict]] = None,
    ) -> FibConfluenceReport:
        """
        تحليل توافق فيبوناتشي الكامل

        المدخلات:
        - candles: شموع
        - swing_high, swing_low: القمة والقاع لرسم فيبوناتشي
        - current_price: السعر الحالي
        - supply_zones: مناطق العرض
        - demand_zones: مناطق الطلب
        - moving_averages: {'ma50': 7450, 'ma200': 7200}
        - trendlines: [{'price': 7500, 'type': 'support'}, ...]

        المخرجات:
        - FibConfluenceReport مع كل المستويات + التوافقات
        """
        diff = swing_high - swing_low
        if diff <= 0:
            return FibConfluenceReport(
                swing_high=swing_high, swing_low=swing_low,
                current_price=current_price,
            )

        levels: list[FibLevelResult] = []

        for level in self.ALL_LEVELS:
            ratio = level.ratio
            base_weight = level.weight

            # حساب سعر المستوى
            # للارتداد: من القمة نازل
            # للامتداد: من القاع طالع
            if ratio <= 1.0:
                price = swing_high - diff * ratio
            else:
                # الامتداد: يتجاوز القمة (لأعلى) أو القاع (لأسفل)
                price = swing_low + diff * ratio

            # كشف التوافقات
            conflations = self._find_conflations(
                price=price,
                current_price=current_price,
                candles=candles,
                supply_zones=supply_zones,
                demand_zones=demand_zones,
                moving_averages=moving_averages,
                trendlines=trendlines,
            )

            # حساب الوزن الكلي
            total_weight = base_weight + sum(c.bonus_weight for c in conflations)

            levels.append(FibLevelResult(
                level=level,
                price=round(price, 1),
                ratio=ratio,
                label=level.label,
                base_weight=base_weight,
                conflations=conflations,
                total_weight=round(total_weight, 2),
            ))

        # تحديد أفضل دعم ومقاومة
        supports = [l for l in levels if l.price < current_price]
        resistances = [l for l in levels if l.price > current_price]

        best_support = max(supports, key=lambda l: l.total_weight) if supports else None
        best_resistance = max(resistances, key=lambda l: l.total_weight) if resistances else None

        return FibConfluenceReport(
            swing_high=swing_high,
            swing_low=swing_low,
            levels=levels,
            best_support=best_support,
            best_resistance=best_resistance,
            current_price=current_price,
        )

    def find_entry_from_confluence(
        self,
        report: FibConfluenceReport,
        bias: str = "call",  # "call" or "put"
    ) -> Optional[dict]:
        """
        إيجاد نقطة دخول بناءً على توافق فيبوناتشي

        للـ CALL: نبحث عن أفضل مستوى دعم (تحت السعر) متوافق
        للـ PUT: نبحث عن أفضل مستوى مقاومة (فوق السعر) متوافق

        المخرج: None أو {
            'entry': float, 'stop': float, 'target': float,
            'confidence': float, 'level': FibLevelResult, 'reason': str
        }
        """
        if bias == "call":
            target_level = report.best_support
            if not target_level or not target_level.is_strong:
                return None

            # الهدف = أقرب مستوى مقاومة قوي
            target = report.best_resistance.price if report.best_resistance else target_level.price * 1.02
            stop = target_level.price * 0.995

            return {
                "entry": target_level.price,
                "stop": stop,
                "target": target,
                "confidence": min(1.0, target_level.total_weight / 2),
                "level": target_level,
                "reason": f"دعم فيبوناتشي {target_level.label} متوافق ({target_level.total_weight:.1f} وزن)",
            }

        else:  # put
            target_level = report.best_resistance
            if not target_level or not target_level.is_strong:
                return None

            target = report.best_support.price if report.best_support else target_level.price * 0.98
            stop = target_level.price * 1.005

            return {
                "entry": target_level.price,
                "stop": stop,
                "target": target,
                "confidence": min(1.0, target_level.total_weight / 2),
                "level": target_level,
                "reason": f"مقاومة فيبوناتشي {target_level.label} متوافقة ({target_level.total_weight:.1f} وزن)",
            }

    # ═══════════════════════════════════════════════════
    # كشف التوافقات
    # ═══════════════════════════════════════════════════

    def _find_conflations(
        self,
        price: float,
        current_price: float,
        candles: list[dict],
        supply_zones: Optional[list],
        demand_zones: Optional[list],
        moving_averages: Optional[dict[str, float]],
        trendlines: Optional[list[dict]],
    ) -> list[Confluence]:
        """كشف جميع التوافقات لمستوى فيبوناتشي واحد"""
        conflations: list[Confluence] = []

        # ١. توافق مع مناطق العرض/الطلب
        if supply_zones:
            for zone in supply_zones:
                zone_mid = getattr(zone, 'mid', getattr(zone, 'price_level', None))
                if zone_mid and self._is_confluent(price, zone_mid, current_price):
                    conflations.append(Confluence(
                        type=ConfluenceType.SUPPLY_DEMAND,
                        matched_price=zone_mid,
                        distance_pct=abs(price - zone_mid) / current_price * 100,
                        bonus_weight=0.25,
                        description="منطقة عرض",
                    ))

        if demand_zones:
            for zone in demand_zones:
                zone_mid = getattr(zone, 'mid', getattr(zone, 'price_level', None))
                if zone_mid and self._is_confluent(price, zone_mid, current_price):
                    conflations.append(Confluence(
                        type=ConfluenceType.SUPPLY_DEMAND,
                        matched_price=zone_mid,
                        distance_pct=abs(price - zone_mid) / current_price * 100,
                        bonus_weight=0.25,
                        description="منطقة طلب",
                    ))

        # ٢. توافق مع المتوسطات المتحركة
        if moving_averages:
            for ma_name, ma_value in moving_averages.items():
                if self._is_confluent(price, ma_value, current_price):
                    weight = 0.3 if "200" in ma_name else 0.15
                    conflations.append(Confluence(
                        type=ConfluenceType.MOVING_AVERAGE,
                        matched_price=ma_value,
                        distance_pct=abs(price - ma_value) / current_price * 100,
                        bonus_weight=weight,
                        description=f"متوسط {ma_name}",
                    ))

        # ٣. توافق مع القمم والقيعان السابقة
        swings = self._find_swing_levels(candles)
        for swing in swings:
            if self._is_confluent(price, swing["level"], current_price):
                conflations.append(Confluence(
                    type=ConfluenceType.SWING_LEVEL,
                    matched_price=swing["level"],
                    distance_pct=abs(price - swing["level"]) / current_price * 100,
                    bonus_weight=0.2,
                    description=f"{swing['type']} سابق",
                ))

        # ٤. توافق مع الأرقام الدائرية
        if price > 100:
            round_price = round(price / 100) * 100
            if self._is_confluent(price, round_price, current_price, tolerance=0.01):
                conflations.append(Confluence(
                    type=ConfluenceType.ROUND_NUMBER,
                    matched_price=round_price,
                    distance_pct=abs(price - round_price) / current_price * 100,
                    bonus_weight=0.1,
                    description=f"رقم دائري {round_price}",
                ))

        # ٥. توافق مع خط اتجاه
        if trendlines:
            for tl in trendlines:
                tl_price = tl.get("price", 0)
                if tl_price and self._is_confluent(price, tl_price, current_price):
                    conflations.append(Confluence(
                        type=ConfluenceType.TRENDLINE,
                        matched_price=tl_price,
                        distance_pct=abs(price - tl_price) / current_price * 100,
                        bonus_weight=0.2,
                        description=f"خط اتجاه {tl.get('type', '')}",
                    ))

        # ٦. توافق مع شمعة انعكاسية
        if self._has_reversal_candle_at(candles, price, current_price):
            conflations.append(Confluence(
                type=ConfluenceType.REVERSAL_CANDLE,
                matched_price=price,
                distance_pct=0,
                bonus_weight=0.25,
                description="شمعة انعكاسية",
            ))

        return conflations

    def _is_confluent(
        self,
        fib_price: float,
        other_price: float,
        current_price: float,
        tolerance: float = None,
    ) -> bool:
        """هل السعران متقاربان بما فيه الكفاية؟"""
        if tolerance is None:
            tolerance = self.CONFLUENCE_TOLERANCE

        if current_price == 0 or other_price == 0:
            return False

        return abs(fib_price - other_price) / current_price <= tolerance

    # ═══════════════════════════════════════════════════
    # أدوات مساعدة
    # ═══════════════════════════════════════════════════

    def _find_swing_levels(self, candles: list[dict], lookback: int = 20) -> list[dict]:
        """كشف القمم والقيعان القريبة"""
        if len(candles) < 3:
            return []

        levels = []
        recent = candles[-lookback:]

        for i in range(1, len(recent) - 1):
            c = recent[i]
            # قمة
            if c["high"] > recent[i - 1]["high"] and c["high"] > recent[i + 1]["high"]:
                levels.append({"level": c["high"], "type": "قمة"})
            # قاع
            if c["low"] < recent[i - 1]["low"] and c["low"] < recent[i + 1]["low"]:
                levels.append({"level": c["low"], "type": "قاع"})

        return levels

    def _has_reversal_candle_at(
        self,
        candles: list[dict],
        price: float,
        current_price: float,
    ) -> bool:
        """هل توجد شمعة انعكاسية قرب مستوى فيبوناتشي؟"""
        if not candles or current_price == 0:
            return False

        for c in candles[-3:]:
            # شمعة هامر (مطرقة) = ارتداد صعودي
            body = abs(c["close"] - c["open"])
            lower_wick = min(c["open"], c["close"]) - c["low"]
            upper_wick = c["high"] - max(c["open"], c["close"])

            if body > 0 and lower_wick > body * 2:  # هامر
                if abs(c["low"] - price) / current_price <= self.CONFLUENCE_TOLERANCE:
                    return True

            # شمعة shooting star = ارتداد هبوطي
            if body > 0 and upper_wick > body * 2:
                if abs(c["high"] - price) / current_price <= self.CONFLUENCE_TOLERANCE:
                    return True

        return False

    @staticmethod
    def auto_detect_swing(candles: list[dict]) -> tuple[float, float]:
        """
        كشف تلقائي للقمة والقاع لرسم فيبوناتشي

        يستخدم آخر 50 شمعة
        """
        if len(candles) < 10:
            return 0, 0

        window = candles[-50:]
        return (
            max(c["high"] for c in window),
            min(c["low"] for c in window),
        )

    @staticmethod
    def summary(report: FibConfluenceReport) -> str:
        """ملخص عربي لتقرير توافق فيبوناتشي"""
        lines = [
            f"📐 توافق فيبوناتشي",
            f"القمة: {report.swing_high:.1f} | القاع: {report.swing_low:.1f}",
            f"السعر الحالي: {report.current_price:.1f}",
            "",
        ]

        # المستوى الذهبي
        golden = report.golden_level
        if golden:
            icon = "🟡" if golden.is_strong else "⚪"
            conflations_str = ", ".join(c.type.value for c in golden.conflations) if golden.conflations else "لا توافقات"
            lines.append(f"{icon} {golden.label}: {golden.price:.1f} (وزن: {golden.total_weight:.2f}) → {conflations_str}")

        # أقوى مستوى
        strongest = report.strongest_level
        if strongest and strongest != golden:
            icon = "🔴" if strongest.is_strong else "⚪"
            conflations_str = ", ".join(c.type.value for c in strongest.conflations) if strongest.conflations else "لا توافقات"
            lines.append(f"{icon} {strongest.label}: {strongest.price:.1f} (وزن: {strongest.total_weight:.2f}) → {conflations_str}")

        # أفضل دعم ومقاومة
        if report.best_support:
            lines.append(f"🟢 أفضل دعم: {report.best_support.label} @ {report.best_support.price:.1f} (وزن: {report.best_support.total_weight:.2f})")

        if report.best_resistance:
            lines.append(f"🔴 أفضل مقاومة: {report.best_resistance.label} @ {report.best_resistance.price:.1f} (وزن: {report.best_resistance.total_weight:.2f})")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════
# واجهة مبسطة
# ═══════════════════════════════════════════════════

def quick_fib_entry(
    candles: list[dict],
    current_price: float,
    supply_zones: list = None,
    demand_zones: list = None,
    bias: str = "call",
) -> Optional[dict]:
    """
    واجهة سريعة: إيجاد نقطة دخول من توافق فيبوناتشي

    الاستدعاء:
        entry = quick_fib_entry(candles, price, demand_zones=demand, bias='call')
        if entry:
            print(f"دخول @ {entry['entry']}, وقف @ {entry['stop']}")
    """
    fib = FibConfluence()
    swing_high, swing_low = fib.auto_detect_swing(candles)
    if swing_high == 0 or swing_low == 0:
        return None

    report = fib.analyze(
        candles=candles,
        swing_high=swing_high,
        swing_low=swing_low,
        current_price=current_price,
        demand_zones=demand_zones if bias == "call" else None,
        supply_zones=supply_zones if bias == "put" else None,
    )

    return fib.find_entry_from_confluence(report, bias=bias)
