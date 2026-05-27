"""
برك السيولة وصيد الأوامر — Liquidity Pools & Stop Hunting
═══════════════════════════════════════════════════════════
منهجية سامي ضيف الله WH SPX — مايو 2026

المفاهيم:
- برك السيولة: تجمع أوامر إيقاف الخسارة عند القمم والقيعان وخطوط الاتجاه الواضحة
- صيد الأوامر (Stop Hunting): السعر يخترق مستوى واضح لتفعيل الأوامر ثم ينعكس بعنف
- فخ الكسر الزائف (Fakeout Trap): الكسر الوهمي + الانعكاس = إشارة دخول قوية

القاعدة الذهبية:
"لا تطارد الكسر — انتظر الانتزاع. ادخل عند الانعكاس عندما يتماشى مع منطقة عرض/طلب"
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class LiquidityPoolType(Enum):
    """نوع بركة السيولة"""
    EQUAL_HIGHS = "equal_highs"       # قمم متساوية — سيولة بيعية
    EQUAL_LOWS = "equal_lows"         # قيعان متساوية — سيولة شرائية
    TRENDLINE = "trendline"           # خط اتجاه واضح
    SWING_HIGH = "swing_high"         # قمة متأرجحة
    SWING_LOW = "swing_low"           # قاع متأرجح
    DOUBLE_TOP = "double_top"         # قمة مزدوجة
    DOUBLE_BOTTOM = "double_bottom"   # قاع مزدوج


class TrapType(Enum):
    """نوع الفخ"""
    BULL_TRAP = "bull_trap"       # كسر وهمي للأعلى ← انعكاس هبوطي
    BEAR_TRAP = "bear_trap"       # كسر وهمي للأسفل ← انعكاس صعودي
    NONE = "none"                 # لا يوجد فخ


@dataclass
class LiquidityPool:
    """بركة سيولة"""
    pool_type: LiquidityPoolType
    price_level: float            # السعر الذي تتجمع عنده الأوامر
    strength: float               # قوة البركة (0-1)
    touches: int                  # عدد مرات اللمس
    description: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.description:
            type_names = {
                LiquidityPoolType.EQUAL_HIGHS: "قمم متساوية — سيولة بيعية",
                LiquidityPoolType.EQUAL_LOWS: "قيعان متساوية — سيولة شرائية",
                LiquidityPoolType.TRENDLINE: "خط اتجاه — سيولة متجمعة",
                LiquidityPoolType.SWING_HIGH: "قمة متأرجحة",
                LiquidityPoolType.SWING_LOW: "قاع متأرجح",
                LiquidityPoolType.DOUBLE_TOP: "قمة مزدوجة",
                LiquidityPoolType.DOUBLE_BOTTOM: "قاع مزدوج",
            }
            self.description = type_names.get(self.pool_type, "")


@dataclass
class FakeoutSignal:
    """إشارة فخ / كسر زائف"""
    trap_type: TrapType
    broken_level: float           # المستوى الذي انكسر
    reversal_price: float         # سعر الانعكاس
    entry_price: float            # سعر الدخول المقترح
    stop_loss: float              # وقف خسارة
    target_price: float           # هدف
    confidence: float             # ثقة (0-1)
    pool: Optional[LiquidityPool] = None  # البركة المرتبطة
    reason: str = ""

    @property
    def direction(self) -> str:
        if self.trap_type == TrapType.BEAR_TRAP:
            return "call"   # فخ هبوطي ← اشترِ كول (صعود)
        elif self.trap_type == TrapType.BULL_TRAP:
            return "put"    # فخ صعودي ← اشترِ بوت (هبوط)
        return "none"


class LiquidityDetector:
    """
    كاشف برك السيولة وصيد الأوامر

    الاستخدام:
        detector = LiquidityDetector()
        pools = detector.detect_pools(candles)
        traps = detector.detect_traps(candles, pools)
    """

    # الثوابت
    SWING_STRENGTH = 3            # عدد الشموع لتأكيد التأرجح
    POOL_TOUCHES_MIN = 2          # أقل عدد لمسات لاعتبارها بركة
    EQUAL_TOLERANCE_PCT = 0.003   # 0.3% تفاوت مسموح لتساوي المستويات
    FAKEOUT_RECOVERY_PCT = 0.002  # 0.2% — نسبة الارتداد لتأكيد الفخ

    def detect_pools(self, candles: list[dict]) -> list[LiquidityPool]:
        """
        كشف برك السيولة من الشموع

        المدخلات: candles = [{open, high, low, close}, ...]
        المخرجات: قائمة برك السيولة
        """
        if len(candles) < self.SWING_STRENGTH * 3:
            return []

        pools: list[LiquidityPool] = []

        # ١. كشف القمم والقيعان المتأرجحة
        swing_highs = self._find_swing_highs(candles)
        swing_lows = self._find_swing_lows(candles)

        # ٢. برك السيولة من القمم المتساوية
        equal_highs = self._find_equal_levels(swing_highs, "high")
        for level_data in equal_highs:
            pools.append(LiquidityPool(
                pool_type=LiquidityPoolType.EQUAL_HIGHS,
                price_level=level_data["level"],
                strength=level_data["strength"],
                touches=level_data["touches"],
            ))

        # ٣. برك السيولة من القيعان المتساوية
        equal_lows = self._find_equal_levels(swing_lows, "low")
        for level_data in equal_lows:
            pools.append(LiquidityPool(
                pool_type=LiquidityPoolType.EQUAL_LOWS,
                price_level=level_data["level"],
                strength=level_data["strength"],
                touches=level_data["touches"],
            ))

        # ٤. القمم المزدوجة
        double_tops = self._find_double_formations(swing_highs, "top")
        for level_data in double_tops:
            pools.append(LiquidityPool(
                pool_type=LiquidityPoolType.DOUBLE_TOP,
                price_level=level_data["level"],
                strength=level_data["strength"],
                touches=2,
            ))

        # ٥. القيعان المزدوجة
        double_bottoms = self._find_double_formations(swing_lows, "bottom")
        for level_data in double_bottoms:
            pools.append(LiquidityPool(
                pool_type=LiquidityPoolType.DOUBLE_BOTTOM,
                price_level=level_data["level"],
                strength=level_data["strength"],
                touches=2,
            ))

        # ٦. خطوط الاتجاه كبرك سيولة
        trendline_pools = self._detect_trendline_pools(candles, swing_highs, swing_lows)
        pools.extend(trendline_pools)

        # ترتيب حسب القوة
        pools.sort(key=lambda p: p.strength * p.touches, reverse=True)

        return pools

    def detect_traps(
        self,
        candles: list[dict],
        pools: Optional[list[LiquidityPool]] = None,
    ) -> list[FakeoutSignal]:
        """
        كشف أفخاخ الكسر الزائف (Stop Hunting traps)

        يبحث عن:
        - السعر يخترق مستوى واضح ← ثم ينعكس بعنف
        - فخ صعودي (Bull Trap): كسر وهمي للأعلى
        - فخ هبوطي (Bear Trap): كسر وهمي للأسفل
        """
        if len(candles) < 5:
            return []

        if pools is None:
            pools = self.detect_pools(candles)

        traps: list[FakeoutSignal] = []

        # نفحص آخر 5 شموع
        recent = candles[-5:]
        current_close = recent[-1]["close"]

        for pool in pools:
            if not pool.is_active:
                continue

            level = pool.price_level
            tolerance = level * self.EQUAL_TOLERANCE_PCT

            # فحص الكسر والانعكاس في الشموع الأخيرة
            for i in range(2, len(recent)):
                c1 = recent[i - 2]
                c2 = recent[i - 1]
                c3 = recent[i]

                # ── فخ هبوطي (Bear Trap) ──
                # السعر يكسر مستوى للأسفل ← شمعة خضراء قوية للأعلى
                is_bear_trap = (
                    c2["low"] < level - tolerance  # كسر للأسفل
                    and c2["close"] < level          # وأغلق تحت المستوى
                    and c3["close"] > level + self.FAKEOUT_RECOVERY_PCT * level  # ارتداد للأعلى
                    and c3["close"] > c3["open"]     # شمعة خضراء
                )

                if is_bear_trap:
                    stop = level * 0.995  # وقف تحت المستوى بـ 0.5%
                    target = level * 1.02  # هدف 2%
                    confidence = min(0.9, 0.5 + pool.strength * 0.4)

                    traps.append(FakeoutSignal(
                        trap_type=TrapType.BEAR_TRAP,
                        broken_level=level,
                        reversal_price=c3["close"],
                        entry_price=c3["close"],
                        stop_loss=stop,
                        target_price=target,
                        confidence=confidence,
                        pool=pool,
                        reason=f"فخ هبوطي — كسر مستوى {pool.description} ({level:.1f}) وارتد للأعلى"
                    ))

                # ── فخ صعودي (Bull Trap) ──
                # السعر يكسر مستوى للأعلى ← شمعة حمراء قوية للأسفل
                is_bull_trap = (
                    c2["high"] > level + tolerance  # كسر للأعلى
                    and c2["close"] > level           # وأغلق فوق المستوى
                    and c3["close"] < level - self.FAKEOUT_RECOVERY_PCT * level  # ارتداد للأسفل
                    and c3["close"] < c3["open"]      # شمعة حمراء
                )

                if is_bull_trap:
                    stop = level * 1.005  # وقف فوق المستوى بـ 0.5%
                    target = level * 0.98  # هدف 2%
                    confidence = min(0.9, 0.5 + pool.strength * 0.4)

                    traps.append(FakeoutSignal(
                        trap_type=TrapType.BULL_TRAP,
                        broken_level=level,
                        reversal_price=c3["close"],
                        entry_price=c3["close"],
                        stop_loss=stop,
                        target_price=target,
                        confidence=confidence,
                        pool=pool,
                        reason=f"فخ صعودي — كسر مستوى {pool.description} ({level:.1f}) وسقط تحته"
                    ))

        # ترتيب حسب الثقة
        traps.sort(key=lambda t: t.confidence, reverse=True)

        return traps

    def is_price_near_pool(
        self,
        price: float,
        pools: list[LiquidityPool],
        threshold_pct: float = 0.005,
    ) -> Optional[LiquidityPool]:
        """هل السعر قريب من بركة سيولة؟"""
        for pool in pools:
            if abs(price - pool.price_level) / price < threshold_pct:
                return pool
        return None

    def get_nearest_pool(
        self,
        price: float,
        pools: list[LiquidityPool],
        above: bool = True,
    ) -> Optional[LiquidityPool]:
        """أقرب بركة سيولة (فوق أو تحت السعر)"""
        candidates = [
            p for p in pools
            if (above and p.price_level > price) or (not above and p.price_level < price)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: abs(p.price_level - price))

    # ═══════════════════════════════════════════════════
    # دوال المساعدة الداخلية
    # ═══════════════════════════════════════════════════

    def _find_swing_highs(self, candles: list[dict]) -> list[dict]:
        """كشف القمم المتأرجحة"""
        swings = []
        n = self.SWING_STRENGTH
        for i in range(n, len(candles) - n):
            c = candles[i]
            is_swing = all(
                c["high"] >= candles[i - j]["high"]
                and c["high"] >= candles[i + j]["high"]
                for j in range(1, n + 1)
            )
            if is_swing:
                swings.append({"index": i, "level": c["high"]})
        return swings

    def _find_swing_lows(self, candles: list[dict]) -> list[dict]:
        """كشف القيعان المتأرجحة"""
        swings = []
        n = self.SWING_STRENGTH
        for i in range(n, len(candles) - n):
            c = candles[i]
            is_swing = all(
                c["low"] <= candles[i - j]["low"]
                and c["low"] <= candles[i + j]["low"]
                for j in range(1, n + 1)
            )
            if is_swing:
                swings.append({"index": i, "level": c["low"]})
        return swings

    def _find_equal_levels(
        self,
        swings: list[dict],
        direction: str,
    ) -> list[dict]:
        """كشف المستويات المتساوية (قمم/قيعان متساوية)"""
        if len(swings) < 2:
            return []

        levels = []
        used = set()

        for i in range(len(swings)):
            if i in used:
                continue

            level = swings[i]["level"]
            cluster = [swings[i]]
            used.add(i)

            for j in range(i + 1, len(swings)):
                if j in used:
                    continue
                other = swings[j]["level"]
                avg = (level + other) / 2
                if avg == 0:
                    continue
                if abs(level - other) / avg <= self.EQUAL_TOLERANCE_PCT:
                    cluster.append(swings[j])
                    used.add(j)

            if len(cluster) >= self.POOL_TOUCHES_MIN:
                avg_level = sum(s["level"] for s in cluster) / len(cluster)
                strength = min(1.0, len(cluster) * 0.25)
                levels.append({
                    "level": round(avg_level, 1),
                    "touches": len(cluster),
                    "strength": strength,
                })

        return levels

    def _find_double_formations(
        self,
        swings: list[dict],
        formation_type: str,
    ) -> list[dict]:
        """كشف القمم/القيعان المزدوجة"""
        if len(swings) < 2:
            return []

        formations = []
        swings_sorted = sorted(swings, key=lambda s: s["index"])

        for i in range(len(swings_sorted) - 1):
            s1 = swings_sorted[i]
            s2 = swings_sorted[i + 1]

            # التأكد من وجود مسافة كافية بينهما
            if s2["index"] - s1["index"] < self.SWING_STRENGTH * 2:
                continue

            avg = (s1["level"] + s2["level"]) / 2
            if avg == 0:
                continue

            if abs(s1["level"] - s2["level"]) / avg <= self.EQUAL_TOLERANCE_PCT:
                # تأكد من وجود قاع/قمة بينهما
                formations.append({
                    "level": round(avg, 1),
                    "strength": 0.6,
                    "gap": s2["index"] - s1["index"],
                })

        return formations

    def _detect_trendline_pools(
        self,
        candles: list[dict],
        swing_highs: list[dict],
        swing_lows: list[dict],
    ) -> list[LiquidityPool]:
        """كشف خطوط الاتجاه التي تعمل كبرك سيولة"""
        pools = []

        # خط اتجاه هابط من قمتين على الأقل
        if len(swing_highs) >= 2:
            h_sorted = sorted(swing_highs[-6:], key=lambda s: s["index"])
            for i in range(len(h_sorted) - 1):
                s1 = h_sorted[i]
                s2 = h_sorted[i + 1]
                if s2["index"] - s1["index"] < self.SWING_STRENGTH:
                    continue
                slope = (s2["level"] - s1["level"]) / (s2["index"] - s1["index"])
                if slope < -0.001:  # هابط بوضوح
                    # إسقاط خط الاتجاه للمستوى الحالي
                    current_level = s2["level"] + slope * (len(candles) - s2["index"])
                    pools.append(LiquidityPool(
                        pool_type=LiquidityPoolType.TRENDLINE,
                        price_level=round(current_level, 1),
                        strength=0.5,
                        touches=2,
                        description="خط اتجاه هابط — مقاومة",
                    ))

        # خط اتجاه صاعد من قاعين على الأقل
        if len(swing_lows) >= 2:
            l_sorted = sorted(swing_lows[-6:], key=lambda s: s["index"])
            for i in range(len(l_sorted) - 1):
                s1 = l_sorted[i]
                s2 = l_sorted[i + 1]
                if s2["index"] - s1["index"] < self.SWING_STRENGTH:
                    continue
                slope = (s2["level"] - s1["level"]) / (s2["index"] - s1["index"])
                if slope > 0.001:  # صاعد بوضوح
                    current_level = s2["level"] + slope * (len(candles) - s2["index"])
                    pools.append(LiquidityPool(
                        pool_type=LiquidityPoolType.TRENDLINE,
                        price_level=round(current_level, 1),
                        strength=0.5,
                        touches=2,
                        description="خط اتجاه صاعد — دعم",
                    ))

        return pools

    # ═══════════════════════════════════════════════════
    # توليد إشارة تداول من الفخ
    # ═══════════════════════════════════════════════════

    def generate_signal(
        self,
        traps: list[FakeoutSignal],
        supply_demand_zones: Optional[list] = None,
    ) -> Optional[FakeoutSignal]:
        """
        توليد أفضل إشارة من الأفخاخ المكتشفة
        مع تفضيل الأفخاخ المتوافقة مع مناطق العرض/الطلب

        القاعدة من سامي ضيف الله:
        "ادخل عند الانعكاس عندما يتماشى مع منطقة عرض/طلب"
        """
        if not traps:
            return None

        best = traps[0]  # الأعلى ثقة (مرتبة مسبقاً)

        # رفع الثقة إذا كان الفخ متوافق مع منطقة عرض/طلب
        if supply_demand_zones:
            for zone in supply_demand_zones:
                # توافق فخ هبوطي (CALL) مع منطقة طلب
                if best.trap_type == TrapType.BEAR_TRAP and hasattr(zone, 'zone_type'):
                    zone_type = getattr(zone, 'zone_type', None)
                    if zone_type and 'demand' in str(zone_type).lower():
                        if abs(best.broken_level - getattr(zone, 'mid', 0)) / best.broken_level < 0.01:
                            best.confidence = min(1.0, best.confidence + 0.15)
                            best.reason += " ✅ متوافق مع منطقة طلب"

                # توافق فخ صعودي (PUT) مع منطقة عرض
                if best.trap_type == TrapType.BULL_TRAP and hasattr(zone, 'zone_type'):
                    zone_type = getattr(zone, 'zone_type', None)
                    if zone_type and 'supply' in str(zone_type).lower():
                        if abs(best.broken_level - getattr(zone, 'mid', 0)) / best.broken_level < 0.01:
                            best.confidence = min(1.0, best.confidence + 0.15)
                            best.reason += " ✅ متوافق مع منطقة عرض"

        return best if best.confidence >= 0.6 else None


# ═══════════════════════════════════════════════════
# واجهة مبسطة
# ═══════════════════════════════════════════════════

def detect_fakeout_signal(
    candles: list[dict],
    supply_demand_zones: Optional[list] = None,
) -> Optional[FakeoutSignal]:
    """
    واجهة سريعة: كشف فخ الكسر الزائف وتوليد إشارة

    الاستدعاء:
        signal = detect_fakeout_signal(candles, sd_strategy.zones)
        if signal:
            print(f"فخ {signal.trap_type.value} → {signal.direction} @ {signal.entry_price}")
    """
    detector = LiquidityDetector()
    pools = detector.detect_pools(candles)
    traps = detector.detect_traps(candles, pools)
    return detector.generate_signal(traps, supply_demand_zones)
