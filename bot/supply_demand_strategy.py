"""
إستراتيجية العرض والطلب — منهجية أبو ليلى (Abo Mazen Trade) 📊
═══════════════════════════════════════════════════════════
مستخلصة من ٦ محاضرات: دورة العرض والطلب مع ابوليلى
القناة: Abo Mazen Trade (@abo_mazen) — 59K مشترك

المحاضرات:
  ١. اساسيات المضاربة بمناطق العرض والطلب
  ٢. احتراف رسم ترندات العرض والطلب
  ٣. احتراف اثبات مناطق العرض والطلب
  ٤. كيفية تحديد اوامر الدخول ووقف الخساره
  ٥. الواو تريد (W Trade)
  ٦. الية اتخاذ القرار

المصدر: YouTube Playlist — PLnMGGUNsnv8hXcFRFlxacW9Lt7-s31112
التاريخ: مايو 2026
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import math


# ═══════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════

class ZoneState(str, Enum):
    """حالات المنطقة (المحاضرة ١)"""
    FRESH = "fresh"         # 🟢 لم يرجع لها السعر — الأقوى
    TOUCHED = "touched"     # 🟡 لمسها السعر وخرج — مقبولة
    CONSUMED = "consumed"   # 🟠 لمست مرتين — ضعيفة
    BROKEN = "broken"       # 🔴 انكسرت — تحولت لمنطقة فليب


class ZoneType(str, Enum):
    DEMAND = "demand"   # 🟢 طلب — منطقة شراء
    SUPPLY = "supply"   # 🔴 عرض — منطقة بيع


class TrendType(str, Enum):
    """أنواع الترند (المحاضرة ٢)"""
    UPTREND = "uptrend"             # صاعد
    DOWNTREND = "downtrend"         # هابط
    BROKEN_UP = "broken_uptrend"    # صاعد مكسور
    BROKEN_DOWN = "broken_downtrend"  # هابط مكسور


class CandlePattern(str, Enum):
    """أنماط الشموع التي ترسم عليها المناطق (المحاضرة ١)"""
    BASE = "base"               # شمعة صغيرة — حجم جسمها < حجم ذيلها
    MARUBOZU = "marubozu"       # شمعة ممتلئة صغيرة
    ENGULFING = "engulfing"     # شمعة بالعة — تبتلع اللي قبلها
    INSIDE_BAR = "inside_bar"   # شمعة داخلية / انعكاسية
    NONE = "none"


class EntryDecision(str, Enum):
    BUY = "buy"       # شراء من منطقة طلب
    SELL = "sell"     # بيع من منطقة عرض
    WAIT = "wait"     # انتظار
    FLIP_BUY = "flip_buy"    # فليب: عرض → شراء
    FLIP_SELL = "flip_sell"  # فليب: طلب → بيع


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class SupplyDemandZone:
    """منطقة عرض أو طلب كاملة"""
    zone_type: ZoneType
    # الحدود: Distal Line (البعيد) + Proximal Line (القريب)
    distal: float          # الطلب: من الأسفل | العرض: من الأعلى
    proximal: float        # الطلب: من الأعلى | العرض: من الأسفل
    state: ZoneState = ZoneState.FRESH
    candle_pattern: CandlePattern = CandlePattern.NONE
    num_candles_inside: int = 0   # عدد الشموع داخل المنطقة
    exit_strength: int = 0        # قوة الخروج (1-5)
    is_clean: bool = True         # شكل مرتب بدون فوضى سعرية
    location_quality: int = 0     # جودة الموقع (0-3)

    @property
    def size(self) -> float:
        """حجم المنطقة = |distal - proximal|"""
        return abs(self.distal - self.proximal)

    @property
    def mid(self) -> float:
        """منتصف المنطقة"""
        return (self.distal + self.proximal) / 2

    def is_price_inside(self, price: float) -> bool:
        """هل السعر داخل المنطقة؟"""
        return self.bottom <= price <= self.top

    @property
    def top(self) -> float:
        return max(self.distal, self.proximal)

    @property
    def bottom(self) -> float:
        return min(self.distal, self.proximal)


@dataclass
class Trend:
    """ترند العرض والطلب (المحاضرة ٢)"""
    trend_type: TrendType
    points: list[float] = field(default_factory=list)  # نقاط القمم/القيعان
    drawn_from: list[int] = field(default_factory=list)  # مؤشرات الشموع

    @property
    def is_broken(self) -> bool:
        return self.trend_type in (TrendType.BROKEN_UP, TrendType.BROKEN_DOWN)

    @property
    def direction(self) -> str:
        if self.trend_type in (TrendType.UPTREND, TrendType.BROKEN_UP):
            return "up"
        return "down"


@dataclass
class FlipZone:
    """منطقة فليب (Flip Zone) — منطقة متحولة (المحاضرة ١)"""
    original_zone: SupplyDemandZone
    new_type: ZoneType        # النوع الجديد بعد الانعكاس
    break_price: float         # سعر الكسر


@dataclass
class WTradePattern:
    """نمط الواو تريد (W Trade) — المحاضرة ٥"""
    zone: SupplyDemandZone     # المنطقة اللي كسرت الترند
    trend_broken: Trend        # الترند المكسور
    return_price: float        # سعر عودة السعر للمنطقة
    is_valid: bool = False     # تحققت الشروط؟


@dataclass
class EntrySignal:
    """إشارة دخول كاملة"""
    decision: EntryDecision
    zone: SupplyDemandZone
    entry_price: float         # سعر الدخول (Proximal Line)
    stop_loss: float           # وقف الخسارة (Distal Line)
    take_profit: float         # هدف الربح (2:1 كحد أدنى)
    risk_reward: float         # نسبة الربح للخسارة
    confidence: float          # 0.0 - 1.0
    reason: str                # سبب الدخول بالعربي
    trend: Optional[Trend] = None
    w_trade: Optional[WTradePattern] = None
    score: int = 0             # تقييم من ٨ (معايير المحاضرة ١)


# ═══════════════════════════════════════════════════════════
# المحرك الرئيسي
# ═══════════════════════════════════════════════════════════

class SupplyDemandStrategy:
    """
    استراتيجية العرض والطلب — منهجية أبو ليلى كاملة

    خطوات العمل:
      ١. رسم مناطق العرض والطلب
      ٢. تقييم المناطق (٨ معايير)
      ٣. تحليل الترند (W/M)
      ٤. كشف الواو تريد
      ٥. اتخاذ قرار الدخول
    """

    def __init__(self, symbol: str = ""):
        self.symbol = symbol
        self.zones: list[SupplyDemandZone] = []
        self.flip_zones: list[FlipZone] = []
        self.trends: list[Trend] = []

    # ═══════════════════════════════════════════════════════
    # ١. رسم المناطق
    # ═══════════════════════════════════════════════════════

    def detect_zones(
        self,
        candles: list[dict],
        swing_strength: int = 3,
    ) -> list[SupplyDemandZone]:
        """
        كشف مناطق العرض والطلب من الشموع

        المنهجية (المحاضرة ١):
        - كل منطقة صعد منها السعر ← منطقة طلب
        - كل منطقة هبط منها السعر ← منطقة عرض
        """
        zones = []
        n = len(candles)
        if n < swing_strength * 2 + 1:
            return zones

        for i in range(swing_strength, n - swing_strength):
            # كشف القيعان (مناطق طلب)
            if self._is_swing_low(candles, i, swing_strength):
                zone = self._build_zone_from_swing(candles, i, ZoneType.DEMAND)
                if zone:
                    zones.append(zone)

            # كشف القمم (مناطق عرض)
            if self._is_swing_high(candles, i, swing_strength):
                zone = self._build_zone_from_swing(candles, i, ZoneType.SUPPLY)
                if zone:
                    zones.append(zone)

        self.zones = zones
        return zones

    def _is_swing_low(self, candles: list[dict], i: int, strength: int) -> bool:
        """هل النقطة i قاع متأرجح؟"""
        low = candles[i].get("low", candles[i].get("close", 0))
        for j in range(i - strength, i + strength + 1):
            if j == i or j < 0 or j >= len(candles):
                continue
            other_low = candles[j].get("low", candles[j].get("close", 0))
            if other_low <= low:
                return False
        return True

    def _is_swing_high(self, candles: list[dict], i: int, strength: int) -> bool:
        """هل النقطة i قمة متأرجحة؟"""
        high = candles[i].get("high", candles[i].get("close", 0))
        for j in range(i - strength, i + strength + 1):
            if j == i or j < 0 or j >= len(candles):
                continue
            other_high = candles[j].get("high", candles[j].get("close", 0))
            if other_high >= high:
                return False
        return True

    def _build_zone_from_swing(
        self,
        candles: list[dict],
        swing_idx: int,
        zone_type: ZoneType,
    ) -> Optional[SupplyDemandZone]:
        """بناء منطقة من نقطة تأرجح"""
        candle = candles[swing_idx]
        o = candle.get("open", 0)
        c = candle.get("close", 0)
        h = candle.get("high", 0)
        l = candle.get("low", 0)

        # تحديد نمط الشمعة
        pattern = self._classify_candle(o, c, h, l)

        if pattern == CandlePattern.NONE:
            return None

        if zone_type == ZoneType.DEMAND:
            # طلب: Distal من الأسفل، Proximal من الأعلى
            distal = l
            proximal = max(o, c)
        else:
            # عرض: Distal من الأعلى، Proximal من الأسفل
            distal = h
            proximal = min(o, c)

        zone = SupplyDemandZone(
            zone_type=zone_type,
            distal=distal,
            proximal=proximal,
            candle_pattern=pattern,
        )

        # حساب عدد الشموع داخل المنطقة
        zone.num_candles_inside = self._count_candles_inside(candles, swing_idx, zone)

        return zone

    def _classify_candle(
        self, o: float, c: float, h: float, l: float
    ) -> CandlePattern:
        """تصنيف نمط الشمعة (المحاضرة ١)"""
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        total_range = h - l

        if total_range == 0:
            return CandlePattern.NONE

        body_pct = body / total_range
        upper_pct = upper_wick / total_range if total_range else 0
        lower_pct = lower_wick / total_range if total_range else 0

        # Base: جسم < ذيل
        if body_pct < 0.3:
            return CandlePattern.BASE
        # Marubozu: جسم ممتلئ ≥ 80%
        if body_pct >= 0.8:
            return CandlePattern.MARUBOZU
        # Inside Bar / انعكاسية: ذيل طويل + جسم صغير
        if upper_pct > 0.6 or lower_pct > 0.6:
            return CandlePattern.INSIDE_BAR
        # افتراضي
        return CandlePattern.BASE

    def _count_candles_inside(
        self, candles: list[dict], from_idx: int, zone: SupplyDemandZone
    ) -> int:
        """عد الشموع داخل المنطقة بعد تشكلها"""
        count = 0
        for i in range(from_idx + 1, len(candles)):
            c = candles[i]
            price_range = (c.get("low", 0), c.get("high", 0))
            # إذا دخلت الشمعة داخل المنطقة
            if not (price_range[1] < zone.bottom or price_range[0] > zone.top):
                count += 1
        return count

    # ═══════════════════════════════════════════════════════
    # ٢. تقييم المناطق (٨ معايير)
    # ═══════════════════════════════════════════════════════

    def evaluate_zone(
        self,
        zone: SupplyDemandZone,
        current_price: float,
        candles_since: list[dict],
    ) -> int:
        """
        تقييم المنطقة حسب ٨ معايير (المحاضرة ١)
        النتيجة: 0-8
        """
        score = 0
        reasons = []

        # ١. منطقة فريش (لم يرجع لها السعر)
        touches = self._count_touches(zone, candles_since)
        # إذا السعر الحالي داخل المنطقة أو قريب منها (< 2%) → فرصة تداول، لا تكسرها
        price_in_zone = zone.bottom <= current_price <= zone.top
        near_zone = abs(current_price - zone.mid) / current_price < 0.02
        if price_in_zone or near_zone:
            touches = min(touches, 2)  # لا تصل لـ BROKEN أبداً

        if touches == 0:
            zone.state = ZoneState.FRESH
            score += 1
            reasons.append("✅ فريش")
        elif touches == 1:
            zone.state = ZoneState.TOUCHED
        elif touches == 2:
            zone.state = ZoneState.CONSUMED
        else:
            zone.state = ZoneState.BROKEN
            return 0  # مكسورة = لا تدخل

        # ٢. عدد الشموع داخل المنطقة 1-6
        if 1 <= zone.num_candles_inside <= 6:
            score += 1
            reasons.append("✅ شموع داخلية 1-6")

        # ٣. الربح المتوقع ≥ 2:1
        rr = self._calculate_rr(zone, current_price)
        if rr >= 2.0:
            score += 1
            reasons.append(f"✅ R:R = {rr:.1f}:1")

        # ٤. مسافة الخروج = ضعف حجم المنطقة
        exit_distance = abs(current_price - zone.proximal)
        if exit_distance >= zone.size * 2:
            score += 1
            reasons.append("✅ خروج قوي (2x حجم)")
        elif exit_distance >= zone.size:
            score += 1
            reasons.append("✅ خروج مقبول (1x حجم)")

        # ٥. خروج شمعة كاملة خارج المنطقة
        if self._has_full_candle_exit(zone, candles_since):
            score += 1
            reasons.append("✅ شمعة كاملة خارج")

        # ٦. قوة الخروج
        zone.exit_strength = self._measure_exit_strength(zone, candles_since)
        if zone.exit_strength >= 3:
            score += 1
            reasons.append(f"✅ خروج قوي ({zone.exit_strength}/5)")

        # ٧. شكل المنطقة (مرتب، بدون فوضى)
        if self._is_clean_zone(zone, candles_since):
            zone.is_clean = True
            score += 1
            reasons.append("✅ شكل مرتب")
        else:
            zone.is_clean = False

        # ٨. الموقع (عند مناطق شراء/بيع معروفة)
        zone.location_quality = self._evaluate_location(zone, current_price)
        if zone.location_quality >= 2:
            score += 1
            reasons.append("✅ موقع قوي")

        return score

    def _count_touches(self, zone: SupplyDemandZone, candles: list[dict]) -> int:
        """حساب عدد مرات لمس السعر للمنطقة"""
        touches = 0
        for c in candles:
            high = c.get("high", 0)
            low = c.get("low", 0)
            # السعر دخل المنطقة
            if low <= zone.top and high >= zone.bottom:
                touches += 1
        return touches

    def _calculate_rr(self, zone: SupplyDemandZone, current_price: float) -> float:
        """نسبة الربح للخسارة"""
        if zone.zone_type == ZoneType.DEMAND:
            stop_distance = abs(zone.proximal - zone.distal)
            target_distance = abs(current_price - zone.proximal)
        else:
            stop_distance = abs(zone.distal - zone.proximal)
            target_distance = abs(zone.proximal - current_price)

        if stop_distance == 0:
            return 0
        return target_distance / stop_distance

    def _has_full_candle_exit(
        self, zone: SupplyDemandZone, candles: list[dict]
    ) -> bool:
        """هل خرجت شمعة كاملة خارج المنطقة؟"""
        if not candles:
            return False
        last = candles[-1]
        if zone.zone_type == ZoneType.DEMAND:
            return last.get("low", 0) > zone.top
        else:
            return last.get("high", 0) < zone.bottom

    def _measure_exit_strength(
        self, zone: SupplyDemandZone, candles: list[dict]
    ) -> int:
        """قياس قوة الخروج من المنطقة (1-5)"""
        if not candles:
            return 0
        # ننظر لآخر 3 شموع
        strength = 0
        recent = candles[-3:] if len(candles) >= 3 else candles
        for c in recent:
            body = abs(c.get("close", 0) - c.get("open", 0))
            total = c.get("high", 0) - c.get("low", 0)
            if total > 0 and body / total > 0.6:
                strength += 1
        return min(strength + 1, 5)  # +1 أساسي

    def _is_clean_zone(self, zone: SupplyDemandZone, candles: list[dict]) -> bool:
        """هل شكل المنطقة مرتب بدون فوضى سعرية؟"""
        if not candles:
            return True
        # منطقة مرتبة = شموعها متجاورة بدون تداخل كبير
        wick_ratio_total = 0
        count = 0
        for c in candles[-5:]:
            body = abs(c.get("close", 0) - c.get("open", 0))
            total = c.get("high", 0) - c.get("low", 0)
            if total > 0:
                wick_ratio_total += body / total
                count += 1
        if count == 0:
            return True
        avg_wick_ratio = wick_ratio_total / count
        return avg_wick_ratio >= 0.4  # أجسام واضحة = فوضى أقل

    def _evaluate_location(
        self, zone: SupplyDemandZone, current_price: float
    ) -> int:
        """تقييم موقع المنطقة (0-3)"""
        quality = 0
        # +١: قريبة من سعر حالي
        if abs(current_price - zone.mid) / current_price < 0.05:
            quality += 1
        # +١: منطقة ذات حجم واضح
        if zone.size / current_price > 0.002:
            quality += 1
        # +١: نمط شمعة معروف
        if zone.candle_pattern != CandlePattern.NONE:
            quality += 1
        return quality

    # ═══════════════════════════════════════════════════════
    # ٣. تحليل الترند (المحاضرة ٢)
    # ═══════════════════════════════════════════════════════

    def detect_trends(self, candles: list[dict]) -> list[Trend]:
        """
        كشف الترندات حسب منهجية العرض والطلب

        شروط رسم الترند (المحاضرة ٢):
        ١. قاعين وصاعد — القاع الثاني أعلى من الأول (W)
        ٢. قمتين وهابط — القمة الثانية أقل من الأولى (M)
        ٣. ٣ مناطق استمرارية (Drop-Base-Drop / Base-Drop)
        """
        trends = []
        swing_lows = self._find_swings(candles, "low")
        swing_highs = self._find_swings(candles, "high")

        # ترند صاعد: W Pattern
        for i in range(len(swing_lows) - 1):
            if swing_lows[i + 1]["value"] > swing_lows[i]["value"]:
                trends.append(Trend(
                    trend_type=TrendType.UPTREND,
                    points=[swing_lows[i]["value"], swing_lows[i + 1]["value"]],
                    drawn_from=[swing_lows[i]["idx"], swing_lows[i + 1]["idx"]],
                ))

        # ترند هابط: M Pattern
        for i in range(len(swing_highs) - 1):
            if swing_highs[i + 1]["value"] < swing_highs[i]["value"]:
                trends.append(Trend(
                    trend_type=TrendType.DOWNTREND,
                    points=[swing_highs[i]["value"], swing_highs[i + 1]["value"]],
                    drawn_from=[swing_highs[i]["idx"], swing_highs[i + 1]["idx"]],
                ))

        self.trends = trends
        return trends

    def _find_swings(self, candles: list[dict], price_key: str) -> list[dict]:
        """إيجاد نقاط التأرجح"""
        swings = []
        n = len(candles)
        if n < 5:
            return swings

        for i in range(2, n - 2):
            price = candles[i].get(price_key, 0)
            is_swing = True
            for offset in [-2, -1, 1, 2]:
                other = candles[i + offset].get(price_key, 0)
                if price_key == "low" and other <= price:
                    is_swing = False
                    break
                if price_key == "high" and other >= price:
                    is_swing = False
                    break

            if is_swing:
                swings.append({"idx": i, "value": price})

        return swings

    def check_trend_break(
        self, trend: Trend, current_price: float, candle: dict
    ) -> bool:
        """
        كسر الترند (المحاضرة ٢):
        - يكسر بشمعة كاملة خارج الترند
        - أو يكسر منطقة طلب في ترند صاعد
        - أو يكسر منطقة عرض في ترند هابط
        """
        close = candle.get("close", 0)

        if trend.trend_type == TrendType.UPTREND:
            # ترند صاعد يُكسر للأسفل
            if close < trend.points[-1]:
                return True
        elif trend.trend_type == TrendType.DOWNTREND:
            # ترند هابط يُكسر للأعلى
            if close > trend.points[-1]:
                return True

        return False

    # ═══════════════════════════════════════════════════════
    # ٤. الواو تريد (W Trade) — المحاضرة ٥
    # ═══════════════════════════════════════════════════════

    def detect_w_trade(
        self,
        zone: SupplyDemandZone,
        trend: Trend,
        candles: list[dict],
    ) -> Optional[WTradePattern]:
        """
        كشف نمط الواو تريد:
        منطقة كسرت الترند وعاد السعر لها ← فرصة
        """
        # الشرط: المنطقة كسرت الترند
        zone_mid = zone.mid

        if trend.trend_type == TrendType.UPTREND:
            # ترند صاعد — المنطقة كسرته للأسفل
            if zone_mid >= trend.points[-1]:
                return None
            new_trend_type = TrendType.BROKEN_UP
        elif trend.trend_type == TrendType.DOWNTREND:
            # ترند هابط — المنطقة كسرته للأعلى
            if zone_mid <= trend.points[-1]:
                return None
            new_trend_type = TrendType.BROKEN_DOWN
        else:
            return None

        # هل عاد السعر للمنطقة؟
        if not candles:
            return None

        last_close = candles[-1].get("close", 0)
        is_returning = (
            zone.bottom <= last_close <= zone.top
        )

        w_trade = WTradePattern(
            zone=zone,
            trend_broken=Trend(
                trend_type=new_trend_type,
                points=trend.points.copy(),
                drawn_from=trend.drawn_from.copy(),
            ),
            return_price=last_close,
            is_valid=is_returning,
        )

        return w_trade

    # ═══════════════════════════════════════════════════════
    # ٥. اتخاذ القرار (المحاضرة ٦)
    # ═══════════════════════════════════════════════════════

    def decide(
        self,
        candles: list[dict],
        current_price: float,
    ) -> EntrySignal:
        """
        آلية اتخاذ القرار — تجميع كل التحليلات

        الأولويات (المحاضرة ٦):
        ١. الدخول مع الترند أولاً
        ٢. فريم أكبر يغلب الأصغر
        ٣. المنطقة الفريش > الملموسة > المستهلكة
        ٤. إذا تعارضت الإشارات ← انتظار
        """
        if not self.zones:
            self.detect_zones(candles)

        if not self.trends:
            self.detect_trends(candles)

        best_signal = EntrySignal(
            decision=EntryDecision.WAIT,
            zone=SupplyDemandZone(
                zone_type=ZoneType.DEMAND,
                distal=0, proximal=0,
                state=ZoneState.BROKEN,
            ),
            entry_price=0,
            stop_loss=0,
            take_profit=0,
            risk_reward=0,
            confidence=0,
            reason="انتظار — لا توجد إشارة واضحة",
        )

        candidates: list[EntrySignal] = []

        for zone in self.zones:
            # تقييم المنطقة بآخر الشموع
            recent_candles = candles[-20:] if len(candles) >= 20 else candles
            score = self.evaluate_zone(zone, current_price, recent_candles)

            # المناطق القريبة من السعر (< 1%) تقبل حتى لو نقاطها أقل — فرصة فورية
            near_price = abs(current_price - zone.mid) / current_price < 0.01
            min_score = 1 if near_price else 3

            if score < min_score:
                continue  # أقل من الحد الأدنى = لا تدخل

            # تحديد الاتجاه
            if zone.zone_type == ZoneType.DEMAND:
                decision = EntryDecision.BUY
                entry = zone.proximal
                stop = zone.distal
                tp = entry + (entry - stop) * 2  # هدف = 2x المسافة فوق الدخول
            else:
                decision = EntryDecision.SELL
                entry = zone.proximal
                stop = zone.distal
                tp = entry - (stop - entry) * 2  # هدف = 2x المسافة تحت الدخول

            # حساب R:R
            rr = abs(tp - entry) / max(abs(entry - stop), 0.0001)

            signal = EntrySignal(
                decision=decision,
                zone=zone,
                entry_price=entry,
                stop_loss=stop,
                take_profit=tp,
                risk_reward=rr,
                confidence=min(score / 8, 1.0),
                reason=self._build_reason(zone, score),
                score=score,
            )

            # فحص الواو تريد
            for trend in self.trends:
                w = self.detect_w_trade(zone, trend, recent_candles)
                if w and w.is_valid:
                    signal.w_trade = w
                    signal.confidence += 0.15
                    signal.reason += " | 🎯 W Trade"
                    break

            candidates.append(signal)

        # فحص مناطق الفليب
        for fz in self.flip_zones:
            if abs(current_price - fz.break_price) / current_price < 0.01:
                signal = EntrySignal(
                    decision=(
                        EntryDecision.FLIP_BUY
                        if fz.new_type == ZoneType.DEMAND
                        else EntryDecision.FLIP_SELL
                    ),
                    zone=fz.original_zone,
                    entry_price=current_price,
                    stop_loss=fz.break_price * 0.98,
                    take_profit=current_price * 1.04,
                    risk_reward=2.0,
                    confidence=0.65,
                    reason="🔄 منطقة فليب",
                )
                candidates.append(signal)

        if candidates:
            # ترتيب: الأقرب للسعر + الثقة (وزن 50/50)
            # الأقرب = أفضل للدخول بنفس اليوم/الأسبوع
            for s in candidates:
                distance_pct = abs(current_price - s.entry_price) / current_price
                # درجة القرب: 1.0 = قريب جداً، 0.0 = بعيد
                s._proximity = 1.0 / (1.0 + distance_pct * 100)
                # وزن أكبر للقرب (70%) لاختيار مناطق قريبة تصلح لنفس اليوم
                s._final_score = (s.confidence * 0.30) + (s._proximity * 0.70)

            candidates.sort(key=lambda s: s._final_score, reverse=True)
            best_signal = candidates[0]

        return best_signal

    def _build_reason(self, zone: SupplyDemandZone, score: int) -> str:
        """بناء سبب الدخول بالعربي"""
        type_name = "طلب 🟢" if zone.zone_type == ZoneType.DEMAND else "عرض 🔴"
        state_name = {
            ZoneState.FRESH: "فريش ⭐",
            ZoneState.TOUCHED: "ملموسة",
            ZoneState.CONSUMED: "مستهلكة ⚠️",
            ZoneState.BROKEN: "مكسورة ❌",
        }.get(zone.state, "?")

        pattern_name = {
            CandlePattern.BASE: "Base",
            CandlePattern.MARUBOZU: "Marubozu",
            CandlePattern.ENGULFING: "ابتلاعية",
            CandlePattern.INSIDE_BAR: "Inside Bar",
            CandlePattern.NONE: "?",
        }.get(zone.candle_pattern, "?")

        return (
            f"منطقة {type_name} | {state_name} | {pattern_name} | "
            f"تقييم {score}/8 | شموع:{zone.num_candles_inside}"
        )

    # ═══════════════════════════════════════════════════════
    # أدوات مساعدة
    # ═══════════════════════════════════════════════════════

    def get_active_zones(
        self, price: float, threshold_pct: float = 0.05
    ) -> list[SupplyDemandZone]:
        """المناطق النشطة القريبة من السعر الحالي"""
        return [
            z for z in self.zones
            if abs(price - z.mid) / price <= threshold_pct
            and z.state != ZoneState.BROKEN
        ]

    def summary(self, signal: EntrySignal) -> str:
        """ملخص عربي للإشارة"""
        if signal.decision == EntryDecision.WAIT:
            return "⏳ انتظار — لا توجد إشارة دخول"

        dir_emoji = "🟢 شراء" if "buy" in signal.decision.value else "🔴 بيع"
        lines = [
            f"📊 إشارة العرض والطلب | {dir_emoji}",
            f"السعر: {signal.entry_price:.2f}",
            f"وقف: {signal.stop_loss:.2f}",
            f"هدف: {signal.take_profit:.2f}",
            f"R:R = {signal.risk_reward:.1f}:1",
            f"ثقة: {signal.confidence:.0%}",
            f"السبب: {signal.reason}",
        ]
        if signal.w_trade:
            lines.append("🎯 نمط الواو تريد")
        return "\n".join(lines)
