"""
إستراتيجية أبو فهد قاما (GAMMA) 🚎
═══════════════════════════════════════
منهجية تداول كاملة مبنية على:
  ١. أبراج القاما — سيولة الصانع (أحمر > أصفر > أزرق > أبيض)
  ٢. مناطق العرض والطلب متعددة الأطر الزمنية
  ٣. الشموع البالعة والابتلاعية
  ٤. استعارة الباص — محطات النقل 🚎

المصدر: وثيقة شرح استراتيجية أبو فهد قاما — مايو 2026
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import math


# ═══════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════

class TowerStrength(str, Enum):
    RED = "red"       # 🔴 أقوى برج — سيولة الصانع الرئيسية
    YELLOW = "yellow" # 🟡 برج قوي
    BLUE = "blue"     # 🔵 متوسط
    WHITE = "white"   # ⚪ مضاربي لحظي (أضعف)


class ZoneType(str, Enum):
    DEMAND = "demand"   # 🟢 طلب
    SUPPLY = "supply"   # 🔴 عرض


class ZoneTimeframe(str, Enum):
    HOURLY = "hourly"       # 🟢🔴 منطقة ساعة
    DAILY = "daily"         # 🔵 يومية
    WEEKLY = "weekly"       # 🟡 أسبوعية
    MONTHLY = "monthly"     # 🟣 شهرية


class Direction(str, Enum):
    CALL = "call"
    PUT = "put"


class CandleBody(str, Enum):
    BULLISH = "bullish"     # 🟢 شمعة خضراء
    BEARISH = "bearish"     # 🔴 شمعة حمراء


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class GammaTower:
    """برج قاما — نقطة سيولة للصانع"""
    price: float
    strength: TowerStrength
    has_bus: bool = False  # 🚎 عليه علامة باص = محطة نقل ركاب
    description: str = ""


@dataclass
class SupplyDemandZone:
    """منطقة عرض أو طلب"""
    top: float        # الحد العلوي
    bottom: float     # الحد السفلي
    zone_type: ZoneType
    timeframe: ZoneTimeframe
    is_confirmed: bool = False  # تم كسرها/اختراقها → مؤكدة
    is_broken: bool = False     # ملغية = تم حذفها من الشارت


@dataclass
class CandleSignal:
    """إشارة شمعة"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    body: CandleBody
    is_engulfing: bool = False        # شمعة بالعة
    belly_sucked: bool = False        # شفط البطن (body at extreme)
    timeframe: str = "5m"             # 5m / 15m / 1h


@dataclass
class GammaEntry:
    """نقطة دخول وفق استراتيجية القاما"""
    direction: Direction
    entry_price: float
    tower: GammaTower          # البرج اللي دخلنا منه
    stop_loss: float           # الوقف = نفس البرج
    target_pct: float = 30.0   # الهدف 30%
    target_price: float = 0.0
    reason: str = ""           # سبب الدخول
    require_flip: bool = True  # نعكس الصفقة إذا ضرب الوقف؟
    max_candles_sideways: int = 2  # أقصى شمعتين عرضية قبل الخروج


@dataclass
class GammaAnalysis:
    """التحليل الكامل للاستراتيجية"""
    symbol: str
    current_price: float
    towers: list[GammaTower] = field(default_factory=list)
    zones: list[SupplyDemandZone] = field(default_factory=list)
    last_candle_5m: Optional[CandleSignal] = None
    last_candle_15m: Optional[CandleSignal] = None
    nearest_tower_above: Optional[GammaTower] = None
    nearest_tower_below: Optional[GammaTower] = None
    trend_daily: Optional[Direction] = None
    trend_hourly: Optional[Direction] = None
    entry: Optional[GammaEntry] = None
    notes: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Constants — من الوثيقة
# ═══════════════════════════════════════════════════════════

# ألوان المناطق حسب الفريم
TIMEFRAME_COLORS = {
    ZoneTimeframe.HOURLY: ("🟢", "🔴"),   # طلب / عرض
    ZoneTimeframe.DAILY: ("🔵", "🔵"),
    ZoneTimeframe.WEEKLY: ("🟡", "🟡"),
    ZoneTimeframe.MONTHLY: ("🟣", "🟣"),
}

# أفضل شركات للمضاربة حسب أبو فهد
PREFERRED_SYMBOLS = ["QQQ", "LLY", "CRWD", "COST", "ASML", "MDB"]

# أوقات التداول الرئيسية (EST)
GOLDEN_HOUR_START = 15  # 3 PM — الساعة الذهبية
MARKET_CLOSE = 16       # 4 PM
OPENING_HOUR = 9.5      # 9:30 AM
MID_SESSION = 13.5       # 1:30 PM

# الشمعة البالعة — لا تعاكسها إلا بعد تجاوزها
# (من فريم ربع ساعة وفوق)


# ═══════════════════════════════════════════════════════════
# GammaStrategy — المحرك الرئيسي
# ═══════════════════════════════════════════════════════════

class GammaStrategy:
    """
    استراتيجية أبو فهد قاما — المحرك الكامل 🚎

    ### القواعد الصارمة:
    1. صفقة واحدة باليوم — حقق التارقت وأغلق الشاشة
    2. تمش مع الصانع — لا تعاكس السوق
    3. دخول من باص (برج عليه علامة 🚎) فقط
    4. ربح 30% ثم بيع (أو ارفع الوقف)
    5. الوقف = نفس البرج اللي شريت منه
    6. إذا عاكس وكسر البرج → اعكس الصفقة (Flip)
    7. لا تدخل بدون سبب (كسر/اختراق برج أو منطقة)
    8. فريم 15 دقيقة للاتجاه، 5 دقائق للدخول
    """

    def __init__(
        self,
        symbol: str = "QQQ",
        target_profit_pct: float = 30.0,
        max_daily_trades: int = 1,
    ):
        self.symbol = symbol
        self.target_profit_pct = target_profit_pct
        self.max_daily_trades = max_daily_trades

    # ── الخطوة 1: تحليل الأبراج ──

    def extract_towers_from_gamma_curve(
        self,
        gamma_curve: list[dict],
        current_price: float,
    ) -> list[GammaTower]:
        """
        🔥 تحويل قوس القاما (منحنى) → خطوط أفقية (أبراج)
        ═══════════════════════════════════════════════════════
        المنهجية — أبو فهد القاما:

        المدخلات: بيانات GAMMA Exposure حقيقية من هيئة سوق المال
        الأمريكية (SEC/CFTC) — تباع لشركات البيانات.

        القاما الخام عبارة عن **منحنى** (قوس) — العلاقة بين السعر
        وقيمة القاما تشكّل شكل الجرس.

        دوري: أحوّل هذا القوس إلى **خطوط أفقية** (أبراج) عند
        النقاط الحرجة في المنحنى.

        الآلية:
        1. نقطة انقلاب القاما (Zero Gamma / Flip Point)
           ← أقوى برج 🔴 أحمر — هنا الصانع ينقلب من شراء لبيع
        2. أعلى تركيز قاما (Gamma Wall / Peak)
           ← ثاني أقوى 🟡 أصفر — سيولة كثيفة للصانع
        3. ثاني أعلى تركيز
           ← 🔵 أزرق
        4. النقاط المتبقية
           ← ⚪ أبيض (مضاربي لحظي)

        المعطيات:
        - gamma_curve: [{price, gamma, open_interest}, ...]
          كل نقطة تمثل (سعر, قيمة القاما)
        - current_price: السعر الحالي
        """
        towers = []
        if not gamma_curve:
            return towers

        # ── ترتيب النقاط حسب السعر ──
        sorted_curve = sorted(gamma_curve, key=lambda p: p.get("price", 0))

        # ── 1. البحث عن نقطة انقلاب القاما (أقوى برج 🔴) ──
        # نقطة الانقلاب = السعر اللي تتغير عنده إشارة القاما
        # (من موجب → سالب أو العكس)
        # هذا هو "Flip Point" — المستوى اللي الصانع ينقلب عنده
        flip_price = None
        for i in range(len(sorted_curve) - 1):
            g1 = sorted_curve[i].get("gamma", 0)
            g2 = sorted_curve[i + 1].get("gamma", 0)
            if (g1 > 0 > g2) or (g1 < 0 < g2):
                # تقاطع الصفر — استخدم المتوسط
                p1 = sorted_curve[i]["price"]
                p2 = sorted_curve[i + 1]["price"]
                flip_price = (p1 + p2) / 2
                break

        if flip_price:
            towers.append(GammaTower(
                price=round(flip_price, 2),
                strength=TowerStrength.RED,
                has_bus=True,
                description="🔴 نقطة انقلاب القاما — الصانع ينقلب"
            ))

        # ── 2. البحث عن قمم القاما (تركيز عالي للسيولة) ──
        # قمة القاما = أعلى قيمة مطلقة للقاما
        # هذه "جدران القاما" (Gamma Walls)
        peaks = []
        for i in range(1, len(sorted_curve) - 1):
            g_prev = abs(sorted_curve[i - 1].get("gamma", 0))
            g_curr = abs(sorted_curve[i].get("gamma", 0))
            g_next = abs(sorted_curve[i + 1].get("gamma", 0))
            if g_curr > g_prev and g_curr > g_next:
                peaks.append({
                    "price": sorted_curve[i]["price"],
                    "gamma_abs": g_curr,
                    "gamma": sorted_curve[i].get("gamma", 0),
                    "oi": sorted_curve[i].get("open_interest", 0),
                })

        # ترتيب القمم تنازلياً (الأقوى أولاً)
        peaks.sort(key=lambda p: p["gamma_abs"], reverse=True)

        for i, peak in enumerate(peaks[:6]):
            if i == 0:
                strength = TowerStrength.YELLOW
                has_bus = True
                desc = "🟡 أعلى جدار قاما (Gamma Wall)"
            elif i == 1:
                strength = TowerStrength.BLUE
                has_bus = True
                desc = "🔵 ثاني أعلى تركيز قاما"
            else:
                strength = TowerStrength.WHITE
                has_bus = False
                desc = "⚪ نقطة قاما ثانوية"

            # ما نكرر مستوى قريب من الـ flip
            if flip_price and abs(peak["price"] - flip_price) < 0.1:
                continue

            towers.append(GammaTower(
                price=round(peak["price"], 2),
                strength=strength,
                has_bus=has_bus,
                description=desc,
            ))

        # ── 3. إزالة الأبراج المتقاربة جداً ──
        towers.sort(key=lambda t: t.price)
        filtered = []
        for tower in towers:
            too_close = any(
                abs(tower.price - existing.price) < 0.15
                for existing in filtered
            )
            if not too_close:
                filtered.append(tower)

        return filtered

    def detect_towers(
        self,
        price_data: dict,
        volume_profile: Optional[dict] = None,
    ) -> list[GammaTower]:
        """
        اكتشاف أبراج القاما

        المسار الأساسي: تحويل منحنى القاما إلى خطوط
        (extract_towers_from_gamma_curve)

        المسار الاحتياطي: Volume Profile + Swing Points
        (يستخدم فقط في غياب بيانات القاما الحقيقية)
        """
        towers = []

        # ── المسار الأساسي: بيانات القاما الحقيقية ──
        gamma_curve = price_data.get("gamma_curve", [])
        if gamma_curve:
            current_price = price_data.get("close", price_data.get("price", 0))
            return self.extract_towers_from_gamma_curve(gamma_curve, current_price)

        # ── المسار الاحتياطي: Volume Profile ──
        if not price_data:
            return towers

        high = price_data.get("high", 0)
        low = price_data.get("low", 0)

        if high == 0 or low == 0:
            return towers

        swings = price_data.get("swing_points", [])
        volume_nodes = volume_profile.get("nodes", []) if volume_profile else []

        all_levels = []

        if volume_nodes:
            sorted_nodes = sorted(volume_nodes, key=lambda x: x.get("volume", 0), reverse=True)
            for i, node in enumerate(sorted_nodes[:4]):
                strength = (
                    TowerStrength.RED if i == 0
                    else TowerStrength.YELLOW if i == 1
                    else TowerStrength.BLUE if i == 2
                    else TowerStrength.WHITE
                )
                all_levels.append((node["price"], strength))

        for i, swing in enumerate(swings[:8]):
            all_levels.append((swing, TowerStrength.WHITE if i > 2 else TowerStrength.BLUE))

        seen = set()
        for price, strength in sorted(all_levels, key=lambda x: x[0]):
            rounded = round(price, 2)
            if rounded not in seen:
                seen.add(rounded)
                has_bus = strength in (TowerStrength.RED, TowerStrength.YELLOW)
                towers.append(GammaTower(
                    price=rounded,
                    strength=strength,
                    has_bus=has_bus,
                    description=f"برج {strength.value}"
                ))

        return sorted(towers, key=lambda t: t.price)

    # ── الخطوة 2: تحليل المناطق ──

    # وزن المناطق حسب الإطار الزمني (منهجية أبو فهد)
    # الأسبوعية والشهرية = الأهم — تمثل سيولة كبيرة
    # اليومية = متوسطة
    # الساعة = تأكيد ثانوي فقط (ما تدخل منها لحالها)
    ZONE_WEIGHT = {
        ZoneTimeframe.MONTHLY: 3.0,   # 🟣 الأقوى — سيولة مؤسسية
        ZoneTimeframe.WEEKLY: 2.0,    # 🟡 سيولة أسبوعية كبيرة
        ZoneTimeframe.DAILY: 1.5,     # 🔵 متوسطة
        ZoneTimeframe.HOURLY: 0.5,    # 🟢 ضعيفة — تأكيد فقط
    }

    def detect_zones(
        self,
        price_data: dict,
        timeframe: ZoneTimeframe,
    ) -> list[SupplyDemandZone]:
        """
        اكتشاف مناطق العرض والطلب حسب الإطار الزمني
        """
        zones = []
        if not price_data:
            return zones

        # مناطق محددة مسبقاً (من التحليل اليدوي)
        predefined = price_data.get("zones", [])
        for z in predefined:
            z_tf = ZoneTimeframe(z.get("timeframe", timeframe.value))
            zones.append(SupplyDemandZone(
                top=z.get("top", 0),
                bottom=z.get("bottom", 0),
                zone_type=ZoneType(z.get("type", "demand")),
                timeframe=z_tf,
                is_confirmed=z.get("confirmed", False),
                is_broken=z.get("broken", False),
            ))

        return zones

    def _get_zone_bonus(self, zone: SupplyDemandZone) -> float:
        """وزن المنطقة — الأسبوعية/الشهرية أقوى بكثير من الساعة"""
        return self.ZONE_WEIGHT.get(zone.timeframe, 1.0)

    # ── الخطوة 3: تحليل الشموع ──

    def analyze_candle(self, candle: dict, timeframe: str = "5m") -> CandleSignal:
        """
        تحليل شمعة واحدة — هل هي بالعة؟ شفط البطن؟
        """
        o = candle.get("open", 0)
        h = candle.get("high", 0)
        l = candle.get("low", 0)
        c = candle.get("close", 0)

        body = CandleBody.BULLISH if c >= o else CandleBody.BEARISH
        body_size = abs(c - o)
        total_range = h - l if h != l else 0.01

        # شمعة بالعة: جسمها > 60% من المدى الكلي
        is_engulfing = body_size / total_range > 0.6 if total_range > 0 else False

        # شفط البطن: الجسم عند أقصى الشمعة
        if body == CandleBody.BULLISH:
            belly_sucked = (c - l) / total_range > 0.85 if total_range > 0 else False
        else:
            belly_sucked = (h - c) / total_range > 0.85 if total_range > 0 else False

        return CandleSignal(
            timestamp=candle.get("timestamp", 0),
            open=o, high=h, low=l, close=c,
            body=body,
            is_engulfing=is_engulfing,
            belly_sucked=belly_sucked,
            timeframe=timeframe,
        )

    # ── الخطوة 4: تحديد أقرب الأبراج ──

    def find_nearest_towers(
        self,
        price: float,
        towers: list[GammaTower],
    ) -> tuple[Optional[GammaTower], Optional[GammaTower]]:
        """أقرب برج فوق وأقرب برج تحت"""
        above = None
        below = None

        sorted_towers = sorted(towers, key=lambda t: t.price)

        for t in sorted_towers:
            if t.price > price and (above is None or t.price < above.price):
                above = t
            if t.price < price and (below is None or t.price > below.price):
                below = t

        return above, below

    # ── الخطوة 5: شروط الدخول CALL ──

    def check_call_entry(
        self,
        analysis: GammaAnalysis,
        candle_5m: CandleSignal,
    ) -> Optional[GammaEntry]:
        """التحقق من شروط دخول CALL الأربعة"""

        price = analysis.current_price
        reasons = []

        # الشرط 1: فتحت شمعة خضراء فوق برج (غير ملامسة)
        if candle_5m.body == CandleBody.BULLISH:
            tower_below = analysis.nearest_tower_below
            if tower_below and candle_5m.low > tower_below.price:
                reasons.append(f"✅ شمعة خضراء فوق برج {tower_below.strength.value}")

        # الشرط 2: ارتداد من منطقة طلب + شمعة خضراء ثانية
        # المناطق المهمة فقط: يومية، أسبوعية، شهرية (الساعة ما تدخل منها)
        for zone in analysis.zones:
            if (zone.zone_type == ZoneType.DEMAND
                and not zone.is_broken
                and zone.timeframe != ZoneTimeframe.HOURLY):  # ⛔ الساعة = تأكيد فقط
                if zone.bottom <= price <= zone.top:
                    weight = self._get_zone_bonus(zone)
                    reasons.append(f"✅ ارتداد من منطقة طلب {zone.timeframe.value} (وزن: {weight:.1f})")

        # الشرط 3: تجاوز برج بشمعة خضراء كاملة
        if candle_5m.body == CandleBody.BULLISH and candle_5m.is_engulfing:
            tower_above = analysis.nearest_tower_above
            if tower_above and candle_5m.close > tower_above.price:
                reasons.append(f"✅ اختراق برج {tower_above.strength.value} بشمعة بالعة")

        # الشرط 4: اختراق ترند القاما
        if (analysis.trend_hourly == Direction.PUT and
            candle_5m.body == CandleBody.BULLISH and
            candle_5m.is_engulfing):
            reasons.append("✅ اختراق ترند القاما الهابط")

        if not reasons:
            return None

        # تحديد البرج للدخول والوقف
        entry_tower = analysis.nearest_tower_below or analysis.nearest_tower_above
        if not entry_tower:
            return None

        target_price = price * (1 + self.target_profit_pct / 100)

        return GammaEntry(
            direction=Direction.CALL,
            entry_price=price,
            tower=entry_tower,
            stop_loss=entry_tower.price,
            target_pct=self.target_profit_pct,
            target_price=target_price,
            reason=" | ".join(reasons),
        )

    # ── الخطوة 6: شروط الدخول PUT ──

    def check_put_entry(
        self,
        analysis: GammaAnalysis,
        candle_5m: CandleSignal,
    ) -> Optional[GammaEntry]:
        """التحقق من شروط دخول PUT الأربعة"""

        price = analysis.current_price
        reasons = []

        # الشرط 1: فتحت شمعة حمراء تحت برج (غير ملامسة)
        if candle_5m.body == CandleBody.BEARISH:
            tower_above = analysis.nearest_tower_above
            if tower_above and candle_5m.high < tower_above.price:
                reasons.append(f"✅ شمعة حمراء تحت برج {tower_above.strength.value}")

        # الشرط 2: ارتداد من منطقة عرض + شمعة حمراء ثانية
        # المناطق المهمة فقط: يومية، أسبوعية، شهرية (الساعة ما تدخل منها)
        for zone in analysis.zones:
            if (zone.zone_type == ZoneType.SUPPLY
                and not zone.is_broken
                and zone.timeframe != ZoneTimeframe.HOURLY):  # ⛔ الساعة = تأكيد فقط
                if zone.bottom <= price <= zone.top:
                    weight = self._get_zone_bonus(zone)
                    reasons.append(f"✅ ارتداد من منطقة عرض {zone.timeframe.value} (وزن: {weight:.1f})")

        # الشرط 3: كسر برج بشمعة حمراء كاملة
        if candle_5m.body == CandleBody.BEARISH and candle_5m.is_engulfing:
            tower_below = analysis.nearest_tower_below
            if tower_below and candle_5m.close < tower_below.price:
                reasons.append(f"✅ كسر برج {tower_below.strength.value} بشمعة بالعة")

        # الشرط 4: كسر ترند القاما
        if (analysis.trend_hourly == Direction.CALL and
            candle_5m.body == CandleBody.BEARISH and
            candle_5m.is_engulfing):
            reasons.append("✅ كسر ترند القاما الصاعد")

        if not reasons:
            return None

        entry_tower = analysis.nearest_tower_above or analysis.nearest_tower_below
        if not entry_tower:
            return None

        target_price = price * (1 - self.target_profit_pct / 100)

        return GammaEntry(
            direction=Direction.PUT,
            entry_price=price,
            tower=entry_tower,
            stop_loss=entry_tower.price,
            target_pct=self.target_profit_pct,
            target_price=target_price,
            reason=" | ".join(reasons),
        )

    # ── الخطوة 7: فحص Flip (عكس الصفقة) ──

    def should_flip(
        self,
        current_entry: GammaEntry,
        current_price: float,
        candle_5m: CandleSignal,
    ) -> Optional[GammaEntry]:
        """هل نعكس الصفقة؟ (Flip — إذا كسر الوقف)"""

        if current_entry.direction == Direction.CALL:
            # وقف الكول = تحت البرج → إذا فتحت شمعة حمراء تحت البرج → flip to PUT
            if (candle_5m.body == CandleBody.BEARISH and
                candle_5m.close < current_entry.stop_loss):
                return GammaEntry(
                    direction=Direction.PUT,
                    entry_price=current_price,
                    tower=current_entry.tower,
                    stop_loss=current_entry.tower.price,
                    target_pct=self.target_profit_pct,
                    target_price=current_price * (1 - self.target_profit_pct / 100),
                    reason="🔄 Flip: كسر وقف الكول → دخول PUT",
                )

        else:  # PUT
            # وقف البوت = فوق البرج → إذا فتحت شمعة خضراء فوق البرج → flip to CALL
            if (candle_5m.body == CandleBody.BULLISH and
                candle_5m.close > current_entry.stop_loss):
                return GammaEntry(
                    direction=Direction.CALL,
                    entry_price=current_price,
                    tower=current_entry.tower,
                    stop_loss=current_entry.tower.price,
                    target_pct=self.target_profit_pct,
                    target_price=current_price * (1 + self.target_profit_pct / 100),
                    reason="🔄 Flip: كسر وقف البوت → دخول CALL",
                )

        return None

    # ── الخطوة 8: التحليل الكامل ──

    def analyze(
        self,
        price_data: dict,
        candles_5m: list[dict],
        candles_15m: list[dict],
        volume_profile: Optional[dict] = None,
    ) -> GammaAnalysis:
        """
        التحليل الكامل — يحدد:
        - الأبراج والمناطق
        - الاتجاه اليومي والساعي
        - نقطة الدخول (إن وجدت)
        """

        current_price = price_data.get("close", price_data.get("price", 0))

        analysis = GammaAnalysis(
            symbol=self.symbol,
            current_price=current_price,
        )

        # 1. اكتشاف الأبراج
        analysis.towers = self.detect_towers(price_data, volume_profile)

        # 2. أقرب الأبراج
        analysis.nearest_tower_above, analysis.nearest_tower_below = \
            self.find_nearest_towers(current_price, analysis.towers)

        # 3. المناطق — كل فريم
        for tf in ZoneTimeframe:
            zones = self.detect_zones(price_data, tf)
            analysis.zones.extend(zones)

        # 4. تحليل الشموع
        if candles_5m:
            analysis.last_candle_5m = self.analyze_candle(candles_5m[-1], "5m")

        if candles_15m:
            analysis.last_candle_15m = self.analyze_candle(candles_15m[-1], "15m")

        # 5. تحديد الاتجاه من شمعة 15 دقيقة
        if analysis.last_candle_15m:
            if analysis.last_candle_15m.body == CandleBody.BULLISH and analysis.last_candle_15m.belly_sucked:
                analysis.trend_hourly = Direction.CALL
            elif analysis.last_candle_15m.body == CandleBody.BEARISH and analysis.last_candle_15m.belly_sucked:
                analysis.trend_hourly = Direction.PUT

        # 6. الاتجاه اليومي من السعر بالنسبة لـ MA200 (تقريبي)
        ma200 = price_data.get("ma200", 0)
        if ma200 > 0:
            analysis.trend_daily = Direction.CALL if current_price > ma200 else Direction.PUT

        # 7. البحث عن دخول
        if analysis.last_candle_5m:
            call_entry = self.check_call_entry(analysis, analysis.last_candle_5m)
            put_entry = self.check_put_entry(analysis, analysis.last_candle_5m)

            # الأولوية للاتجاه الأقوى
            if call_entry and put_entry:
                if analysis.trend_hourly == Direction.CALL:
                    analysis.entry = call_entry
                elif analysis.trend_hourly == Direction.PUT:
                    analysis.entry = put_entry
                else:
                    # الأقرب للبرج هو الأفضل
                    analysis.entry = call_entry  # تفضيل الكول (رضا الوالدين)
            elif call_entry:
                analysis.entry = call_entry
            elif put_entry:
                analysis.entry = put_entry

        # 8. ملاحظات
        if analysis.entry:
            analysis.notes.append(f"🚎 دخول {analysis.entry.direction.value.upper()} من برج {analysis.entry.tower.strength.value}")
            analysis.notes.append(f"🛑 الوقف: ${analysis.entry.stop_loss:.2f}")
            analysis.notes.append(f"🎯 الهدف: ${analysis.entry.target_price:.2f} (+{analysis.entry.target_pct}%)")
            analysis.notes.append(f"📋 السبب: {analysis.entry.reason}")

        return analysis

    # ── عقد رضا الوالدين (Parents' Blessing Contract) ──

    def parents_blessing_contract(
        self,
        towers: list[GammaTower],
        current_price: float,
        expiry_days: int = 2,
    ) -> dict:
        """
        عقد رضا الوالدين:
        - عقد CALL دائماً
        - عند أعمق برج قاع (تحت)
        - نصف سعر العقد (Limit Order)
        - مدة يومين على الأقل
        """
        # أعمق برج تحت السعر
        deep_tower = None
        for t in sorted(towers, key=lambda t: t.price):
            if t.price < current_price and t.strength in (TowerStrength.RED, TowerStrength.YELLOW):
                deep_tower = t

        if not deep_tower:
            # خذ أعمق برج متاح
            below = [t for t in towers if t.price < current_price]
            deep_tower = below[-1] if below else None

        if not deep_tower:
            return {"error": "لا توجد أبراج تحت السعر"}

        return {
            "type": "CALL",
            "strike": deep_tower.price,
            "limit_price_pct": 50,  # نصف السعر
            "expiry_days": max(expiry_days, 2),
            "tower": deep_tower,
            "note": "عقد رضا الوالدين — CALL من القاع 🕌",
        }

    # ── توليد ملخص ──

    def summary(self, analysis: GammaAnalysis) -> str:
        """توليد ملخص عربي للتحليل"""
        lines = [
            f"## 📊 تحليل قاما — {analysis.symbol}",
            f"السعر الحالي: **${analysis.current_price:.2f}**",
            "",
            "### 🗼 الأبراج القريبة:",
        ]

        if analysis.nearest_tower_above:
            t = analysis.nearest_tower_above
            bus = "🚎" if t.has_bus else ""
            lines.append(f"- فوق: ${t.price:.2f} ({t.strength.value}) {bus}")
        if analysis.nearest_tower_below:
            t = analysis.nearest_tower_below
            bus = "🚎" if t.has_bus else ""
            lines.append(f"- تحت: ${t.price:.2f} ({t.strength.value}) {bus}")

        if analysis.entry:
            lines.append("")
            lines.append(f"### {'🟢' if analysis.entry.direction == Direction.CALL else '🔴'} إشارة دخول:")
            lines.append(f"- **{analysis.entry.direction.value.upper()}** عند ${analysis.entry.entry_price:.2f}")
            lines.append(f"- 🛑 وقف: ${analysis.entry.stop_loss:.2f}")
            lines.append(f"- 🎯 هدف: ${analysis.entry.target_price:.2f} (+{analysis.entry.target_pct}%)")
        else:
            lines.append("")
            lines.append("⏳ لا توجد إشارة دخول حالياً")

        return "\n".join(lines)


# ═══════════════════════════════════════════
# مكتبة أنماط القاما — Gamma Pattern Library
# مستخرجة من ٢٢ صورة تحليلية (FAHAD_GAMMA@TradingView)
# ═══════════════════════════════════════════

GAMMA_PATTERNS = [
    # ═══════ فوق الأبيض ═══════
    {"id": 1, "condition": "above_white", "signal": "CALL", "desc": "فوق البرج الأبيض — كل الأبراج دعم قوي"},
    # ═══════ عند الأبيض ═══════
    {"id": 2, "condition": "at_white_testing", "signal": "WAIT", "desc": "عند البرج الأبيض — اختبار مقاومة، انتظار"},
    {"id": 3, "condition": "at_white_rejected", "signal": "PUT", "desc": "عند الأبيض + رفض/شمعة حمراء — PUT"},
    {"id": 4, "condition": "at_white_breakthrough", "signal": "CALL", "desc": "اختراق البرج الأبيض للأعلى — CALL قوي"},
    # ═══════ بين أزرق وأبيض ═══════
    {"id": 5, "condition": "blue_to_white_ascending", "signal": "CALL", "desc": "بين أزرق وأبيض — صاعد نحو المقاومة — CALL"},
    {"id": 6, "condition": "blue_to_white_descending", "signal": "PUT", "desc": "بين أزرق وأبيض — هابط من الأبيض — PUT"},
    # ═══════ عند الأزرق (Flip Zone) ═══════
    {"id": 7, "condition": "at_flip_zone", "signal": "WAIT", "desc": "عند Flip Zone — منطقة الانعكاس — انتظار"},
    {"id": 8, "condition": "flip_up_break_blue", "signal": "CALL", "desc": "اختراق الأزرق للأعلى — Flip إيجابي — CALL"},
    {"id": 9, "condition": "flip_down_break_blue", "signal": "PUT", "desc": "كسر الأزرق للأسفل — Flip سلبي — PUT"},
    # ═══════ بين أصفر وأزرق ═══════
    {"id": 10, "condition": "yellow_to_blue_ascending", "signal": "CALL", "desc": "بين أصفر وأزرق — صاعد نحو الـ Flip — CALL"},
    {"id": 11, "condition": "yellow_to_blue_descending", "signal": "PUT", "desc": "بين أصفر وأزرق — هابط من الأزرق — PUT"},
    # ═══════ عند الأصفر (Gamma Wall) ═══════
    {"id": 12, "condition": "at_yellow_support", "signal": "CALL", "desc": "عند الأصفر كارتداد — جدار قاما كدعم — CALL"},
    {"id": 13, "condition": "at_yellow_resistance", "signal": "PUT", "desc": "عند الأصفر كمقاومة — فشل في الاختراق — PUT"},
    # ═══════ بين أحمر وأصفر ═══════
    {"id": 14, "condition": "red_to_yellow_ascending", "signal": "CALL", "desc": "بين أحمر وأصفر — صاعد من القاع — CALL"},
    {"id": 15, "condition": "red_to_yellow_descending", "signal": "PUT", "desc": "بين أحمر وأصفر — هابط نحو الأحمر — PUT"},
    # ═══════ عند الأحمر ═══════
    {"id": 16, "condition": "at_red_support", "signal": "CALL", "desc": "عند البرج الأحمر — أقوى دعم — دخول CALL"},
    {"id": 17, "condition": "at_red_breakdown", "signal": "PUT", "desc": "عند الأحمر + ضغط بيعي — خطر كسر — PUT"},
    # ═══════ تحت الأحمر ═══════
    {"id": 18, "condition": "below_red", "signal": "WAIT", "desc": "تحت كل الأبراج — كلها مقاومة — انتظار"},
    {"id": 19, "condition": "below_red_bounce", "signal": "CALL", "desc": "تحت الأحمر + ارتداد للأعلى — FLIP CALL"},
    # ═══════ ضغط / squeeze ═══════
    {"id": 20, "condition": "red_yellow_squeeze", "signal": "WAIT", "desc": "انضغاط بين أحمر وأصفر — انتظار كسر"},
    {"id": 21, "condition": "blue_white_squeeze", "signal": "WAIT", "desc": "انضغاط بين أزرق وأبيض — انتظار اختراق"},
    # ═══════ اختراق متسلسل ═══════
    {"id": 22, "condition": "cascade_breakthrough", "signal": "CALL", "desc": "اختراق متسلسل لكل الأبراج — زخم صاعد قوي"},
]


def _get_tower(towers, strength):
    """استخراج برج حسب القوة (red/yellow/blue/white)"""
    return next((t for t in towers if t.get('strength') == strength or t.get('name') == strength), None)


def _pct_diff(a, b):
    """نسبة الفرق بين قيمتين"""
    return abs(a - b) / b if b != 0 else 0


def _candle_direction(candles):
    """تحديد اتجاه آخر شمعتين: 1=صاعد، -1=هابط، 0=متردد"""
    if not candles or len(candles) < 2:
        return 0
    last, prev = candles[-1], candles[-2]
    if last.get('close', 0) > last.get('open', 0) and last.get('close', 0) > prev.get('close', 0):
        return 1
    if last.get('close', 0) < last.get('open', 0) and last.get('close', 0) < prev.get('close', 0):
        return -1
    return 0


def _is_squeeze(t1, t2, threshold=0.05):
    """هل البرجين متقاربين (انضغاط)؟"""
    if not t1 or not t2:
        return False
    return _pct_diff(t1['price'], t2['price']) < threshold


def match_gamma_pattern(towers, current_price, recent_candles=None):
    """
    مطابقة السعر الحالي مع ٢٢ نمط قاما — تغطية كاملة.
    تطبق على أي سهم — الأنماط عامة وليست خاصة برمز معين.
    
    Args:
        towers: قائمة أبراج [{'price': float, 'strength': str}, ...]
        current_price: السعر الحالي
        recent_candles: آخر شمعتين (اختياري)
    
    Returns:
        dict: {pattern_id, signal, confidence, stop, desc}
    """
    if not towers:
        return {"pattern_id": 0, "signal": "WAIT", "confidence": 0, "desc": "لا توجد أبراج"}

    red = _get_tower(towers, 'red')
    yellow = _get_tower(towers, 'yellow')
    blue = _get_tower(towers, 'blue')
    white = _get_tower(towers, 'white')

    p = current_price
    direction = _candle_direction(recent_candles) if recent_candles else 0

    # ───────────────────────────────────
    # النمط ١: فوق الأبيض — CALL قوي
    # ───────────────────────────────────
    if white and p > white['price']:
        return {"pattern_id": 1, "signal": "CALL", "confidence": 0.90,
                "stop": white['price'], "desc": "فوق البرج الأبيض — كل الأبراج دعم"}

    # ───────────────────────────────────
    # النمط ٢-٤: عند الأبيض
    # ───────────────────────────────────
    if white and _pct_diff(p, white['price']) < 0.015:
        if direction == -1:
            return {"pattern_id": 3, "signal": "PUT", "confidence": 0.70,
                    "stop": white['price'] * 1.02, "desc": "عند الأبيض + رفض — PUT"}
        if direction == 1:
            return {"pattern_id": 4, "signal": "CALL", "confidence": 0.75,
                    "stop": white['price'] * 0.98, "desc": "اختراق الأبيض — CALL"}
        return {"pattern_id": 2, "signal": "WAIT", "confidence": 0.40,
                "desc": "عند البرج الأبيض — انتظار التأكيد"}

    # ───────────────────────────────────
    # النمط ٥-٦: بين أزرق وأبيض
    # ───────────────────────────────────
    if blue and white and blue['price'] < p < white['price']:
        if direction == -1:
            return {"pattern_id": 6, "signal": "PUT", "confidence": 0.60,
                    "stop": white['price'], "desc": "بين أزرق وأبيض — هابط — PUT"}
        return {"pattern_id": 5, "signal": "CALL", "confidence": 0.65,
                "stop": blue['price'], "desc": "بين أزرق وأبيض — صاعد — CALL"}

    # ───────────────────────────────────
    # النمط ٧-٩: عند الأزرق (Flip Zone)
    # ───────────────────────────────────
    if blue and _pct_diff(p, blue['price']) < 0.015:
        if direction == 1:
            return {"pattern_id": 8, "signal": "CALL", "confidence": 0.75,
                    "stop": blue['price'] * 0.98, "desc": "Flip إيجابي — اختراق الأزرق — CALL"}
        if direction == -1:
            return {"pattern_id": 9, "signal": "PUT", "confidence": 0.70,
                    "stop": blue['price'] * 1.02, "desc": "Flip سلبي — كسر الأزرق — PUT"}
        return {"pattern_id": 7, "signal": "WAIT", "confidence": 0.35,
                "desc": "عند Flip Zone — انتظار تحديد الاتجاه"}

    # ───────────────────────────────────
    # النمط ١٠-١١: بين أصفر وأزرق
    # ───────────────────────────────────
    if yellow and blue and yellow['price'] < p < blue['price']:
        if direction == -1:
            return {"pattern_id": 11, "signal": "PUT", "confidence": 0.55,
                    "stop": blue['price'], "desc": "بين أصفر وأزرق — هابط — PUT"}
        return {"pattern_id": 10, "signal": "CALL", "confidence": 0.55,
                "stop": yellow['price'], "desc": "بين أصفر وأزرق — صاعد — CALL"}

    # ───────────────────────────────────
    # النمط ١٢-١٣: عند الأصفر (Gamma Wall)
    # ───────────────────────────────────
    if yellow and _pct_diff(p, yellow['price']) < 0.015:
        if direction == 1:
            return {"pattern_id": 12, "signal": "CALL", "confidence": 0.65,
                    "stop": yellow['price'] * 0.98, "desc": "ارتداد من جدار القاما — CALL"}
        if direction == -1:
            return {"pattern_id": 13, "signal": "PUT", "confidence": 0.60,
                    "stop": yellow['price'] * 1.02, "desc": "فشل عند جدار القاما — PUT"}
        return {"pattern_id": 12, "signal": "CALL", "confidence": 0.55,
                "stop": red['price'] if red else yellow['price'] * 0.97, "desc": "عند الأصفر — ارتداد متوقع"}

    # ───────────────────────────────────
    # النمط ١٤-١٥: بين أحمر وأصفر
    # ───────────────────────────────────
    if red and yellow and red['price'] < p < yellow['price']:
        if _is_squeeze(red, yellow):
            return {"pattern_id": 20, "signal": "WAIT", "confidence": 0.30,
                    "desc": "انضغاط بين أحمر وأصفر — انتظار كسر"}
        if direction == -1:
            return {"pattern_id": 15, "signal": "PUT", "confidence": 0.55,
                    "stop": yellow['price'], "desc": "بين أحمر وأصفر — هابط — PUT"}
        return {"pattern_id": 14, "signal": "CALL", "confidence": 0.55,
                "stop": red['price'] * 0.98, "desc": "بين أحمر وأصفر — صاعد — CALL"}

    # ───────────────────────────────────
    # النمط ١٦-١٧: عند الأحمر
    # ───────────────────────────────────
    if red and _pct_diff(p, red['price']) < 0.015:
        if direction == -1:
            return {"pattern_id": 17, "signal": "PUT", "confidence": 0.60,
                    "stop": red['price'] * 0.97, "desc": "عند الأحمر + ضغط بيعي — خطر كسر"}
        if direction == 1:
            return {"pattern_id": 16, "signal": "CALL", "confidence": 0.75,
                    "stop": red['price'] * 0.98, "desc": "ارتداد من البرج الأحمر — CALL"}
        return {"pattern_id": 16, "signal": "CALL", "confidence": 0.70,
                "stop": red['price'] * 0.98, "desc": "عند البرج الأحمر — دخول CALL"}

    # ───────────────────────────────────
    # النمط ١٨-١٩: تحت الأحمر
    # ───────────────────────────────────
    if red and p < red['price']:
        if direction == 1:
            return {"pattern_id": 19, "signal": "CALL", "confidence": 0.50,
                    "stop": red['price'] * 0.95, "desc": "ارتداد من تحت الأحمر — FLIP CALL"}
        return {"pattern_id": 18, "signal": "WAIT", "confidence": 0.30,
                "desc": "تحت كل الأبراج — انتظار ارتداد"}

    # ───────────────────────────────────
    # النمط ٢١: انضغاط بين أزرق وأبيض
    # ───────────────────────────────────
    if blue and white and _is_squeeze(blue, white, 0.03) and blue['price'] < p < white['price']:
        return {"pattern_id": 21, "signal": "WAIT", "confidence": 0.30,
                "desc": "انضغاط بين أزرق وأبيض — انتظار اختراق"}

    # ───────────────────────────────────
    # النمط ٢٢: اختراق متسلسل (زخم)
    # ───────────────────────────────────
    if direction == 1 and red and p > red['price']:
        towers_above = [t for t in [red, yellow, blue, white] if t and t['price'] > red['price']]
        if len(towers_above) >= 2 and p > towers_above[1]['price']:
            return {"pattern_id": 22, "signal": "CALL", "confidence": 0.80,
                    "stop": towers_above[0]['price'], "desc": "اختراق متسلسل — زخم صاعد قوي"}

    # ───────────────────────────────────
    # افتراضي
    # ───────────────────────────────────
    if blue and p < blue['price']:
        return {"pattern_id": 9, "signal": "PUT", "confidence": 0.50,
                "stop": blue['price'] * 1.02, "desc": "تحت الأزرق — PUT"}

    return {"pattern_id": 0, "signal": "WAIT", "confidence": 0, "desc": "نمط غير معروف"}
